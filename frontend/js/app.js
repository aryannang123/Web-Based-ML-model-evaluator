
// Frontend REST Client for Web-Based ML Model Evaluator

const API_BASE = "http://127.0.0.1:5000/api";

// Initialize frontend when the page loads
document.addEventListener("DOMContentLoaded", () => {
    checkBackendHealth();
    setupEventListeners();
});

// Reusable function for communicating with the backend API
async function apiRequest(endpoint, options = {}) {
    const response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers: {
            ...options.headers
        }
    });

    // Read the response according to its content type
    const contentType = response.headers.get("content-type") || "";
    let data = {};

    if (contentType.includes("application/json")) {
        try {
            data = await response.json();
        } catch {
            throw new Error("The backend returned invalid JSON");
        }
    }

    // Handle unsuccessful HTTP responses
    if (!response.ok) {
        throw new Error(
            data.message ||
            data.error ||
            `API request failed with status ${response.status}`
        );
    }

    return data;
}

// Check whether the backend server is available
async function checkBackendHealth() {
    const badge = document.getElementById("api-status");

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

// Set up frontend event listeners
function setupEventListeners() {
    // US-03: Frontend-backend communication implemented
    // TODO: US-08 - Connect file upload form (Nidhi)
    // TODO: US-15 - Target column dropdown listener (Abhishek)
    // TODO: US-16 - Split ratio range slider listener (Nidhi)
    // TODO: US-18 - Train button listener (Aryan)
    // TODO: US-19 - Render evaluation metrics and confusion matrix (Abhishek)

    console.log("Frontend architecture initialized. Ready for US implementation.");
}
