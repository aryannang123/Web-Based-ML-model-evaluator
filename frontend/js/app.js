
/* Frontend REST Client for Web-Based ML Model Evaluator */

const API_BASE = "/api";

// US-11: Restore the active dataset ID for this browser session.
let activeDatasetId = sessionStorage.getItem("activeDatasetId");

// Initialize frontend when the page loads.
document.addEventListener("DOMContentLoaded", () => {
    checkBackendHealth();
    setupEventListeners();
    setupLoginForm();
    setupRegistrationForm();
    restoreSession();
});

// Reusable function for communicating with the backend API.
async function apiRequest(endpoint, options = {}) {
    let response;

    try {
        response = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            credentials: "same-origin",
            headers: {
                ...options.headers
            }
        });
    } catch {
        throw new Error(
            "Unable to connect to the server. Please check your connection."
        );
    }

    const contentType = response.headers.get("content-type") || "";
    let data = {};

    if (contentType.includes("application/json")) {
        try {
            data = await response.json();
        } catch {
            throw new Error("The backend returned invalid JSON.");
        }
    } else {
        if (!response.ok) {
            throw new Error(
                `The server returned an unexpected response (HTTP ${response.status}).`
            );
        }

        throw new Error("The backend returned a non-JSON response.");
    }

    if (!response.ok) {
        throw new Error(
            data.message ||
            data.error ||
            `API request failed with status ${response.status}`
        );
    }

    return data;
}

// Check whether the backend server is available.
async function checkBackendHealth() {
    const badge = document.getElementById("api-status");
    if (!badge) return;

    try {
        const data = await apiRequest("/health");

        if (data.status === "healthy") {
            badge.className = "badge bg-success me-3";
            badge.innerHTML =
                '<i class="bi bi-circle-fill me-1 small"></i>API Connected';
        } else {
            throw new Error("Backend is not healthy");
        }
    } catch (error) {
        badge.className = "badge bg-warning text-dark me-3";
        badge.innerHTML =
            '<i class="bi bi-exclamation-triangle-fill me-1 small"></i>API Offline';

        console.error("Backend connection failed:", error.message);
    }
}

// Set up frontend event listeners.
function setupEventListeners() {
    // US-03: Frontend-backend communication.
    // US-08 and US-11: Upload or replace a CSV dataset.
    document.getElementById("upload-form")
        ?.addEventListener("submit", uploadDataset);

    // TODO: US-15 - Target column dropdown listener (Abhishek).
    // TODO: US-16 - Split ratio range slider listener (Nidhi).
    // TODO: US-18 - Train button listener (Aryan).
    // TODO: US-19 - Render evaluation metrics and confusion matrix (Abhishek).

    const logoutBtn = document.getElementById("logout-btn");

    if (logoutBtn) {
        logoutBtn.addEventListener("click", handleLogout);
    }

    console.log("Frontend architecture initialized.");
}

// Update the upload button based on active dataset state.
function updateUploadButton() {
    const button = document.getElementById("upload-btn");
    if (!button) return;

    if (activeDatasetId) {
        button.innerHTML =
            '<i class="bi bi-arrow-repeat me-1"></i>Replace Dataset';
    } else {
        button.innerHTML =
            '<i class="bi bi-upload me-1"></i>Upload & Inspect';
    }
}

// Update target-column options using the replacement dataset's columns.
function updateTargetColumnOptions(columns) {
    const select = document.getElementById("target-column-select");
    if (!select) return;

    select.replaceChildren();

    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = columns.length
        ? "Select target column..."
        : "Upload dataset first...";
    select.appendChild(placeholder);

    columns.forEach((column) => {
        const option = document.createElement("option");
        option.value = column;
        option.textContent = column;
        select.appendChild(option);
    });

    select.disabled = columns.length === 0;
}

// Update dashboard metadata after an upload or replacement.
function updateDatasetDisplay(dataset) {
    const datasetMeta = document.getElementById("dataset-meta");

    if (datasetMeta) {
        datasetMeta.textContent =
            `${dataset.filename} · ${dataset.row_count} rows · ${dataset.column_count} columns`;
    }

    if (Array.isArray(dataset.columns)) {
        updateTargetColumnOptions(dataset.columns);
    }
}

// US-08 / US-11: Upload a new dataset or replace the active dataset.
async function uploadDataset(event) {
    event.preventDefault();

    const form = event.currentTarget;
    const fileInput = document.getElementById("csv-file");
    const button = document.getElementById("upload-btn");

    if (!fileInput || !fileInput.files.length) {
        showUploadFeedback("Choose a CSV file to upload.", false);
        return;
    }

    const isReplacement = Boolean(activeDatasetId);

    if (button) {
        button.disabled = true;
        button.textContent = isReplacement
            ? "Replacing…"
            : "Uploading…";
    }

    const feedback = document.getElementById("upload-feedback");

    if (feedback) {
        feedback.classList.remove(
            "d-none",
            "alert-success",
            "alert-danger"
        );
        feedback.classList.add("alert-info");
        feedback.textContent = isReplacement
            ? "Validating and replacing the active dataset…"
            : "Validating and uploading your CSV…";
    }

    try {
        const endpoint = isReplacement
            ? `/dataset/${encodeURIComponent(activeDatasetId)}/replace`
            : "/dataset/upload";

        const result = await apiRequest(endpoint, {
            method: "POST",
            body: new FormData(form)
        });

        // Save the active dataset ID for this browser session.
        activeDatasetId = String(result.dataset_id);
        sessionStorage.setItem("activeDatasetId", activeDatasetId);

        updateDatasetDisplay(result);

        showUploadFeedback(
            isReplacement
                ? `${result.filename} replaced the active dataset successfully: ${result.row_count} rows and ${result.column_count} columns.`
                : `${result.filename} uploaded successfully: ${result.row_count} rows and ${result.column_count} columns.`,
            true
        );

        form.reset();

    } catch (error) {
        showUploadFeedback(
            error.message ||
            "Dataset upload or replacement failed. Please try again.",
            false
        );
    } finally {
        if (button) {
            button.disabled = false;
            updateUploadButton();
        }
    }
}

// Display upload or replacement feedback.
function showUploadFeedback(message, success) {
    const feedback = document.getElementById("upload-feedback");
    if (!feedback) return;

    feedback.classList.remove(
        "d-none",
        "alert-info",
        "alert-success",
        "alert-danger"
    );

    feedback.classList.add(
        success ? "alert-success" : "alert-danger"
    );

    feedback.textContent = message;
}

// Restore active dataset metadata after a dashboard refresh.
async function restoreActiveDataset() {
    if (!activeDatasetId) {
        updateUploadButton();
        return;
    }

    try {
        const result = await apiRequest(
            `/dataset/${encodeURIComponent(activeDatasetId)}`
        );

        const dataset = result.dataset;

        updateDatasetDisplay({
            dataset_id: dataset.id,
            filename: dataset.filename,
            row_count: dataset.row_count,
            column_count: dataset.column_count,
            columns: dataset.metadata?.columns || []
        });

    } catch (error) {
        // Clear stale IDs, including IDs belonging to another account.
        console.warn("Unable to restore active dataset:", error.message);

        activeDatasetId = null;
        sessionStorage.removeItem("activeDatasetId");

        const datasetMeta = document.getElementById("dataset-meta");
        if (datasetMeta) {
            datasetMeta.textContent = "No dataset selected";
        }

        updateTargetColumnOptions([]);
    }

    updateUploadButton();
}

// US-06: Handle logout.
async function handleLogout() {
    const logoutBtn = document.getElementById("logout-btn");
    const feedback = document.getElementById("logout-feedback");

    if (logoutBtn) {
        logoutBtn.disabled = true;
        logoutBtn.textContent = "Logging out...";
    }

    if (feedback) {
        feedback.classList.add("d-none");
        feedback.textContent = "";
    }

    try {
        const result = await apiRequest("/auth/logout", {
            method: "POST"
        });

        // Do not reuse one user's active dataset in another session.
        activeDatasetId = null;
        sessionStorage.removeItem("activeDatasetId");

        sessionStorage.setItem(
            "logoutMessage",
            result.message || "You have been logged out successfully"
        );

        sessionStorage.setItem("logoutStatus", "success");

        window.location.assign(result.redirect_url || "/login");

    } catch (error) {
        console.error("Logout failed:", error.message);

        if (feedback) {
            feedback.textContent =
                error.message || "Logout failed. Please try again.";
            feedback.className = "alert alert-danger";
        }

        if (logoutBtn) {
            logoutBtn.disabled = false;
            logoutBtn.textContent = "Logout";
        }
    }
}

// Login form.
function setupLoginForm() {
    const logoutMessage = sessionStorage.getItem("logoutMessage");
    const logoutStatus = sessionStorage.getItem("logoutStatus");

    if (logoutMessage) {
        const loginFeedback = document.getElementById("login-feedback");

        if (loginFeedback) {
            loginFeedback.textContent = logoutMessage;
            loginFeedback.className =
                logoutStatus === "error"
                    ? "mt-3 alert alert-danger"
                    : "mt-3 alert alert-success";
        }

        sessionStorage.removeItem("logoutMessage");
        sessionStorage.removeItem("logoutStatus");
    }

    document.getElementById("login-form")
        ?.addEventListener("submit", async (event) => {
            event.preventDefault();

            const feedback = document.getElementById("login-feedback");
            const submitButton = event.currentTarget.querySelector(
                'button[type="submit"]'
            );

            const credentials = {
                username: document.getElementById("login-username").value.trim(),
                password: document.getElementById("login-password").value
            };

            if (submitButton) {
                submitButton.disabled = true;
            }

            if (feedback) {
                feedback.textContent = "Signing in...";
                feedback.className = "mt-3 text-muted";
            }

            try {
                const result = await apiRequest("/auth/login", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify(credentials)
                });

                window.location.assign(result.redirect_url || "/");

            } catch (error) {
                if (feedback) {
                    feedback.textContent = error.message;
                    feedback.className = "mt-3 alert alert-danger";
                }
            } finally {
                if (submitButton) {
                    submitButton.disabled = false;
                }
            }
        });
}

// Restore authenticated session and active dataset.
async function restoreSession() {
    const currentUser = document.getElementById("current-user");
    const logoutBtn = document.getElementById("logout-btn");

    if (!currentUser) return;

    try {
        const result = await apiRequest("/auth/session");

        if (!result.authenticated) {
            activeDatasetId = null;
            sessionStorage.removeItem("activeDatasetId");
            window.location.replace("/login");
            return;
        }

        currentUser.textContent = result.user.username;

        if (logoutBtn) {
            logoutBtn.classList.remove("d-none");
        }

        await restoreActiveDataset();

    } catch {
        activeDatasetId = null;
        sessionStorage.removeItem("activeDatasetId");
        window.location.replace("/login");
    }
}

// Registration form (US-04).
function setupRegistrationForm() {
    document.getElementById("registration-form")
        ?.addEventListener("submit", async (event) => {
            event.preventDefault();

            const feedback = document.getElementById(
                "registration-feedback"
            );

            const data = {
                username: document.getElementById("reg-username").value.trim(),
                email: document.getElementById("reg-email").value.trim(),
                password: document.getElementById("reg-password").value
            };

            try {
                const response = await apiRequest("/auth/register", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify(data)
                });

                if (feedback) {
                    feedback.textContent =
                        response.message || "Registration successful";
                    feedback.className = "mt-3 alert alert-success";
                }

                event.target.reset();

            } catch (error) {
                if (feedback) {
                    feedback.textContent =
                        error.message || "Registration failed";
                    feedback.className = "mt-3 alert alert-danger";
                }

                console.error("Registration failed:", error.message);
            }
        });
}
