/* Frontend REST Client for Web-Based ML Model Evaluator */

// Use the same server that serves the frontend.
const API_BASE = "/api";

// Initialize frontend when the page loads.
document.addEventListener("DOMContentLoaded", initializeFrontend);

function initializeFrontend() {
    checkBackendHealth();
    setupEventListeners();
    setupLoginForm();
    setupRegistrationForm();
    restoreSession();
}

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
            "Unable to reach the server. Check your connection and try again."
        );
    }

    const contentType = response.headers.get("content-type") || "";
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
            (typeof data.error === "string" && data.error) ||
            (typeof data.message === "string" && data.message) ||
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

    console.log(
        "Frontend architecture initialized. Ready for US implementation."
    );
}

function setupLoginForm() {
    document.getElementById("login-form")
        ?.addEventListener("submit", handleLoginSubmit);
}

async function handleLoginSubmit(event) {
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
}

async function restoreSession() {
    const currentUser = document.getElementById("current-user");
    if (!currentUser) return;

    try {
        const result = await apiRequest("/auth/session");
        if (!result.authenticated) {
            window.location.replace("/login");
            return;
        }
        currentUser.textContent = result.user.username;
    } catch {
        window.location.replace("/login");
    }
}

// Registration form (US-04).
function setupRegistrationForm() {
    document.getElementById("registration-form")
        ?.addEventListener("submit", handleRegistrationSubmit);
}

async function handleRegistrationSubmit(event) {
    event.preventDefault();

    const data = {
        username: document.getElementById("reg-username").value.trim(),
        email: document.getElementById("reg-email").value.trim(),
        password: document.getElementById("reg-password").value
    };

    try {
        const result = await apiRequest("/auth/register", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(data)
        });

        setRegistrationFeedback(
            result.message || "Registration successful.",
            true
        );
        event.currentTarget.reset();
    } catch (error) {
        setRegistrationFeedback(error.message || "Registration failed.", false);
        console.error("Registration failed:", error.message);
    }
}

function setRegistrationFeedback(message, success) {
    const feedback = document.getElementById("registration-feedback");
    if (!feedback) return;

    feedback.textContent = message;
    feedback.className = success
        ? "mt-3 alert alert-success"
        : "mt-3 alert alert-danger";
}
