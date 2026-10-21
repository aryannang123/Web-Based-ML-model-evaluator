// Frontend REST Client for Web-Based ML Model Evaluator
// Architecture Scaffolding for US-01

const API_BASE = "http://127.0.0.1:5000/api";

document.addEventListener("DOMContentLoaded", () => {
    checkBackendHealth();
    setupEventListeners();
});

// Health check to verify communication with Flask server
async function checkBackendHealth() {
    const badge = document.getElementById("api-status");
    try {
        const res = await fetch(`${API_BASE}/health`);
        if (res.ok) {
            badge.className = "badge bg-success me-3";
            badge.innerHTML = '<i class="bi bi-circle-fill me-1 small"></i>API Connected';
        } else {
            throw new Error();
        }
    } catch {
        badge.className = "badge bg-warning text-dark me-3";
        badge.innerHTML = '<i class="bi bi-exclamation-triangle-fill me-1 small"></i>API Offline';
    }
}

function setupEventListeners() {
    // TODO: US-03 - Set up frontend-backend communication (Assigned to: @abhishekdeene-eng)
    // TODO: US-08 - Connect file upload form (Assigned to: @nidhipoojamrutha20)
    // TODO: US-15 - Target column dropdown listener (Assigned to: @abhishekdeene-eng)
    // TODO: US-16 - Split ratio range slider listener (Assigned to: @nidhipoojamrutha20)
    // TODO: US-18 - Train button listener and loading indicator (Assigned to: @aryannang123)
    // TODO: US-19 - Render evaluation metrics and confusion matrix (Assigned to: @abhishekdeene-eng)
    console.log("Frontend architecture initialized. Ready for US implementation.");
}

/* Issue #4: Registration form */
document.getElementById("registration-form")
  ?.addEventListener("submit", handleRegistrationSubmit);

async function handleRegistrationSubmit(event) {
    event.preventDefault();

    const data = {
      username: document.getElementById("reg-username").value.trim(),
      email: document.getElementById("reg-email").value.trim(),
      password: document.getElementById("reg-password").value
    };

    let response;
    try {
      response = await fetch("/api/auth/register", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(data)
      });
    } catch {
      setRegistrationFeedback(
        "Unable to reach the server. Check your connection and try again.",
        false
      );
      return;
    }

    const contentType = response.headers.get("content-type") || "";
    if (!contentType.toLowerCase().includes("json")) {
      setRegistrationFeedback(
        `The server returned a non-JSON response (HTTP ${response.status}).`,
        false
      );
      return;
    }

    let result;
    try {
      result = await response.json();
    } catch {
      setRegistrationFeedback(
        `The server returned invalid JSON (HTTP ${response.status}).`,
        false
      );
      return;
    }

    if (!result || typeof result !== "object" || Array.isArray(result)) {
      setRegistrationFeedback(
        `The server returned an unexpected response (HTTP ${response.status}).`,
        false
      );
      return;
    }

    if (!response.ok) {
      const validationError = typeof result.error === "string"
        ? result.error
        : typeof result.message === "string"
          ? result.message
          : `Registration failed (HTTP ${response.status}).`;
      setRegistrationFeedback(validationError, false);
      return;
    }

    setRegistrationFeedback(
      typeof result.message === "string" ? result.message : "Registration successful.",
      true
    );
    event.currentTarget.reset();
}

function setRegistrationFeedback(message, success) {
    const feedback = document.getElementById("registration-feedback");
    feedback.textContent = message;
    feedback.className = success
      ? "mt-3 alert alert-success"
      : "mt-3 alert alert-danger";
}
/* End Issue #4 */
