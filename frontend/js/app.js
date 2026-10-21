
/* Frontend REST Client for Web-Based ML Model Evaluator */

const API_BASE = "/api";

// Initialize once when the DOM is ready.
document.addEventListener("DOMContentLoaded", initializeFrontend);

function initializeFrontend() {
    checkBackendHealth();
    setupEventListeners();
    setupLoginForm();
    setupRegistrationForm();
    restoreSession();
}

// Shared API helper for all frontend requests.
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
            "Unable to reach the server. Check your connection and try again."
        );
    }

    const contentType =
        response.headers.get("content-type") || "";

    if (!contentType.toLowerCase().includes("json")) {
        throw new Error(
            `The server returned a non-JSON response (HTTP ${response.status}).`
        );
    }

    let data;

    try {
        data = await response.json();
    } catch {
        throw new Error(
            `The server returned invalid JSON (HTTP ${response.status}).`
        );
    }

    if (!data || typeof data !== "object" || Array.isArray(data)) {
        throw new Error(
            `The server returned an unexpected response (HTTP ${response.status}).`
        );
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

// Verify backend connectivity.
async function checkBackendHealth() {
    const badge = document.getElementById("api-status");

    if (!badge) return;

    try {
        const data = await apiRequest("/health");

        if (data.status !== "healthy") {
            throw new Error("Backend is not healthy");
        }

        badge.className = "badge bg-success me-3";
        badge.innerHTML =
            '<i class="bi bi-circle-fill me-1 small"></i>API Connected';

    } catch (error) {
        badge.className =
            "badge bg-warning text-dark me-3";

        badge.innerHTML =
            '<i class="bi bi-exclamation-triangle-fill me-1 small"></i>API Offline';

        console.error(
            "Backend connection failed:",
            error.message
        );
    }
}

// Existing frontend architecture.
function setupEventListeners() {
    // US-03: Frontend-backend communication.
    // US-08: CSV upload integration.
    // US-15: Target column selection.
    // US-16: Train-test split configuration.
    // US-18: Model training integration.
    // US-19: Evaluation result rendering.

    console.log(
        "Frontend architecture initialized. Ready for US implementation."
    );
}

// Existing login functionality.
function setupLoginForm() {
    const form = document.getElementById("login-form");

    if (!form) return;

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const feedback =
            document.getElementById("login-feedback");

        const submitButton =
            form.querySelector('button[type="submit"]');

        const credentials = {
            username:
                document.getElementById("login-username").value.trim(),
            password:
                document.getElementById("login-password").value
        };

        if (submitButton) submitButton.disabled = true;

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

            window.location.assign(
                result.redirect_url || "/"
            );

        } catch (error) {
            if (feedback) {
                feedback.textContent = error.message;
                feedback.className =
                    "mt-3 alert alert-danger";
            }

        } finally {
            if (submitButton) submitButton.disabled = false;
        }
    });
}

// Restore authenticated user session.
async function restoreSession() {
    const currentUser =
        document.getElementById("current-user");

    if (!currentUser) return;

    try {
        const result = await apiRequest("/auth/session");

        if (!result.authenticated) {
            window.location.replace("/login");
            return;
        }

        currentUser.textContent =
            result.user.username;

    } catch {
        window.location.replace("/login");
    }
}

// US-04: User Registration.
function setupRegistrationForm() {
    const form =
        document.getElementById("registration-form");

    if (!form) return;

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const feedback =
            document.getElementById("registration-feedback");

        const submitButton =
            form.querySelector('button[type="submit"]');

        const registrationData = {
            username:
                document.getElementById("reg-username").value.trim(),
            email:
                document.getElementById("reg-email").value.trim(),
            password:
                document.getElementById("reg-password").value
        };

        if (submitButton) submitButton.disabled = true;

        if (feedback) {
            feedback.textContent = "Creating account...";
            feedback.className = "mt-3 text-muted";
        }

        try {
            const result = await apiRequest("/auth/register", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(registrationData)
            });

            if (feedback) {
                feedback.textContent =
                    result.message || "Registration successful.";

                feedback.className =
                    "mt-3 alert alert-success";
            }

            form.reset();

        } catch (error) {
            if (feedback) {
                feedback.textContent =
                    error.message || "Registration failed.";

                feedback.className =
                    "mt-3 alert alert-danger";
            }

            console.error(
                "Registration failed:",
                error.message
            );

        } finally {
            if (submitButton) submitButton.disabled = false;
        }
    });
}
