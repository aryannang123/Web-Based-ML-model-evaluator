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
