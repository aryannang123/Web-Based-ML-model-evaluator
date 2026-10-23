/* Frontend REST Client for Web-Based ML Model Evaluator */

// Use the same server that serves the frontend.
const API_BASE = "/api";

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
    // TODO: US-08 - Connect file upload form (Nidhi).
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
