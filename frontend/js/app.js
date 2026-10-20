
// Frontend REST Client for Web-Based ML Model Evaluator

const API_BASE = "/api";

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
    document.getElementById("upload-form")
        ?.addEventListener("submit", uploadDataset);
    // TODO: US-15 - Target column dropdown listener (Abhishek)
    // TODO: US-16 - Split ratio range slider listener (Nidhi)
    // TODO: US-18 - Train button listener (Aryan)
    // TODO: US-19 - Render evaluation metrics and confusion matrix (Abhishek)

    console.log("Frontend architecture initialized. Ready for US implementation.");
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
        // FormData supplies the multipart boundary; do not set Content-Type here.
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
        form.reset();
    } catch (error) {
        showUploadFeedback(error.message || "Upload failed. Please try another CSV file.", false);
    } finally {
        button.disabled = false;
        button.innerHTML = '<i class="bi bi-upload me-1"></i>Upload & Inspect';
    }
}

function showUploadFeedback(message, success) {
    const feedback = document.getElementById("upload-feedback");
    feedback.classList.remove("d-none", "alert-info", "alert-success", "alert-danger");
    feedback.classList.add(success ? "alert-success" : "alert-danger");
    feedback.textContent = message;
}

/* Issue #4: Registration form */
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
      const response = await fetch("/api/auth/register", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(data)
      });

      const result = await response.json();

      feedback.textContent = response.ok
        ? result.message
        : (result.error || "Registration failed");

      feedback.className = response.ok
        ? "mt-3 alert alert-success"
        : "mt-3 alert alert-danger";

      if (response.ok) event.target.reset();

    } catch (error) {
      feedback.textContent = "Unable to connect to server";
      feedback.className = "mt-3 alert alert-danger";
    }
  });
/* End Issue #4 */
