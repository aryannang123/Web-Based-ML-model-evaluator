/* Frontend REST Client for Web-Based ML Model Evaluator */

// Use the same server that serves the frontend.
const API_BASE = "/api";
let currentDatasetId = null;

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

    // Read the response according to its content type.
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
    // US-08: CSV upload form.
    document.getElementById("upload-form")
        ?.addEventListener("submit", uploadDataset);
    document.getElementById("train-form")
        ?.addEventListener("submit", evaluateDataset);
    document.getElementById("split-range")
        ?.addEventListener("input", updateSplitDisplay);
    updateSplitDisplay();
    // TODO: US-15 - Target column dropdown listener (Abhishek).
    // TODO: US-16 - Split ratio range slider listener (Nidhi).
    // TODO: US-18 - Train button listener (Aryan).
    // TODO: US-19 - Render evaluation metrics and confusion matrix (Abhishek).

    // US-06: Logout button listener
    const logoutBtn = document.getElementById("logout-btn");
    if (logoutBtn) {
        logoutBtn.addEventListener("click", handleLogout);
    }

    console.log(
        "Frontend architecture initialized. Ready for US implementation."
    );
}

async function uploadDataset(event) {
    event.preventDefault();

    const form = event.currentTarget;
    const fileInput = document.getElementById("csv-file");
    const feedback = document.getElementById("upload-feedback");
    const button = document.getElementById("upload-btn");

    if (!fileInput.files.length) {
        showUploadFeedback("Choose a CSV file to upload.", false);
        return;
    }

    button.disabled = true;
    button.textContent = "Uploading…";
    feedback.classList.remove("d-none", "alert-success", "alert-danger");
    feedback.classList.add("alert-info");
    feedback.textContent = "Validating and uploading your CSV…";

    try {
        const result = await apiRequest("/dataset/upload", {
            method: "POST",
            body: new FormData(form)
        });
        showUploadFeedback(
            `${result.filename} uploaded successfully: ${result.row_count} rows and ${result.column_count} columns.`,
            true
        );
        document.getElementById("dataset-meta").textContent =
            `${result.row_count} rows · ${result.column_count} columns`;
        currentDatasetId = result.dataset_id;
        populateTrainingOptions(result.columns || []);
        form.reset();
    } catch (error) {
        showUploadFeedback(
            error.message || "Upload failed. Please try another CSV file.",
            false
        );
    } finally {
        button.disabled = false;
        button.innerHTML = '<i class="bi bi-upload me-1"></i>Upload & Inspect';
    }
}

function updateSplitDisplay() {
    const slider = document.getElementById("split-range");
    const display = document.getElementById("split-display");
    if (!slider || !display) return;
    const testPercent = Math.round(Number(slider.value) * 100);
    display.textContent = `${100 - testPercent}% Train / ${testPercent}% Test`;
}

function populateTrainingOptions(columns) {
    const targetSelect = document.getElementById("target-column-select");
    const algorithmSelect = document.getElementById("algorithm-select");
    const trainButton = document.getElementById("train-btn");
    if (!targetSelect || !algorithmSelect || !trainButton) return;

    targetSelect.replaceChildren();
    const prompt = document.createElement("option");
    prompt.value = "";
    prompt.textContent = "Choose a target column...";
    targetSelect.appendChild(prompt);
    for (const column of columns) {
        const option = document.createElement("option");
        option.value = column;
        option.textContent = column;
        targetSelect.appendChild(option);
    }
    targetSelect.disabled = columns.length === 0;
    algorithmSelect.disabled = columns.length === 0;
    trainButton.disabled = columns.length === 0;
}

async function evaluateDataset(event) {
    event.preventDefault();
    const targetColumn = document.getElementById("target-column-select").value;
    const algorithmSelect = document.getElementById("algorithm-select");
    const algorithm = algorithmSelect.value;
    const selectedOption = algorithmSelect.selectedOptions[0];
    const taskType = selectedOption?.parentElement?.label?.toLowerCase() === "regression"
        ? "regression"
        : "classification";
    const feedback = document.getElementById("evaluation-container");
    const trainButton = document.getElementById("train-btn");

    if (!currentDatasetId) {
        renderEvaluationMessage("Upload a dataset before training a model.", true);
        return;
    }
    if (!targetColumn || !algorithm) {
        renderEvaluationMessage("Choose a target column and algorithm.", true);
        return;
    }

    trainButton.disabled = true;
    feedback.textContent = "Training and evaluating the model…";
    feedback.className = "card-body text-muted";
    try {
        const result = await apiRequest("/ml/evaluate", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                dataset_id: currentDatasetId,
                target_column: targetColumn,
                algorithm,
                task_type: taskType,
                test_size: Number(document.getElementById("split-range").value)
            })
        });
        renderEvaluationResult(result);
    } catch (error) {
        renderEvaluationMessage(error.message || "The model could not be evaluated.", true);
    } finally {
        trainButton.disabled = false;
    }
}

function renderEvaluationMessage(message, isError = false) {
    const container = document.getElementById("evaluation-container");
    container.replaceChildren();
    const paragraph = document.createElement("p");
    paragraph.className = isError ? "mb-0 text-danger" : "mb-0 text-muted";
    paragraph.textContent = message;
    container.appendChild(paragraph);
}

function renderEvaluationResult(result) {
    const container = document.getElementById("evaluation-container");
    container.replaceChildren();
    const split = document.createElement("p");
    split.className = "small text-muted";
    split.textContent = `Training used ${result.split.train_rows} rows and testing used ${result.split.test_rows} rows.`;
    container.appendChild(split);

    const list = document.createElement("dl");
    list.className = "row mb-0";
    for (const [name, value] of Object.entries(result.metrics || {})) {
        const term = document.createElement("dt");
        term.className = "col-sm-6";
        term.textContent = name.replaceAll("_", " ");
        const detail = document.createElement("dd");
        detail.className = "col-sm-6";
        detail.textContent = typeof value === "number" ? value.toFixed(4) : String(value);
        list.append(term, detail);
    }
    container.appendChild(list);
}

function showUploadFeedback(message, success) {
    const feedback = document.getElementById("upload-feedback");
    feedback.classList.remove("d-none", "alert-info", "alert-success", "alert-danger");
    feedback.classList.add(success ? "alert-success" : "alert-danger");
    feedback.textContent = message;
}

// US-06: Handle logout
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
        const result = await apiRequest("/auth/logout", {method: "POST"});
        sessionStorage.setItem(
            "logoutMessage",
            result.message || "You have been logged out successfully"
        );
        sessionStorage.setItem("logoutStatus", "success");
        window.location.assign(result.redirect_url || "/login");
    } catch (error) {
        console.error("Logout failed:", error.message);
        if (feedback) {
            feedback.textContent = error.message || "Logout failed. Please try again.";
            feedback.className = "alert alert-danger";
        }
        if (logoutBtn) {
            logoutBtn.disabled = false;
            logoutBtn.textContent = "Logout";
        }
    }
}

function setupLoginForm() {
    // Display logout feedback message if present
    const logoutMessage = sessionStorage.getItem("logoutMessage");
    const logoutStatus = sessionStorage.getItem("logoutStatus");
    
    if (logoutMessage) {
        const loginFeedback = document.getElementById("login-feedback");
        if (loginFeedback) {
            loginFeedback.textContent = logoutMessage;
            // Show success in green, error in red
            loginFeedback.className = logoutStatus === "error" 
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

            submitButton.disabled = true;
            feedback.textContent = "Signing in...";
            feedback.className = "mt-3 text-muted";

            try {
                const result = await apiRequest("/auth/login", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify(credentials)
                });
                window.location.assign(result.redirect_url || "/");
            } catch (error) {
                feedback.textContent = error.message;
                feedback.className = "mt-3 alert alert-danger";
            } finally {
                submitButton.disabled = false;
            }
        });
}

async function restoreSession() {
    const currentUser = document.getElementById("current-user");
    const logoutBtn = document.getElementById("logout-btn");
    
    if (!currentUser) return;

    try {
        const result = await apiRequest("/auth/session");
        if (!result.authenticated) {
            window.location.replace("/login");
            return;
        }
        
        // Display username and show logout button
        currentUser.textContent = result.user.username;
        if (logoutBtn) {
            logoutBtn.classList.remove("d-none");
        }
    } catch {
        window.location.replace("/login");
    }
}

// Registration form (US-04).
function setupRegistrationForm() {
    document.getElementById("registration-form")
        ?.addEventListener("submit", async (event) => {
            event.preventDefault();

            const feedback = document.getElementById("registration-feedback");
            const data = {
                username: document.getElementById("reg-username").value.trim(),
                email: document.getElementById("reg-email").value.trim(),
                password: document.getElementById("reg-password").value
            };

            try {
                const response = await apiRequest("/auth/register", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
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
                    feedback.textContent = error.message || "Registration failed";
                    feedback.className = "mt-3 alert alert-danger";
                }

                console.error("Registration failed:", error.message);
            }
        });
}
