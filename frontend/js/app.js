// Frontend REST Client for Web-Based ML Model Evaluator
const API_BASE = "http://127.0.0.1:5000/api";

let currentDataset = null;

document.addEventListener("DOMContentLoaded", () => {
    checkBackendHealth();
    setupEventListeners();
});

// Check if Flask backend is live
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
    // Split range listener
    const splitRange = document.getElementById("split-range");
    const splitDisplay = document.getElementById("split-display");
    splitRange.addEventListener("input", (e) => {
        const testPercent = Math.round(e.target.value * 100);
        const trainPercent = 100 - testPercent;
        splitDisplay.textContent = `${trainPercent}% Train / ${testPercent}% Test`;
    });

    // Upload form
    const uploadForm = document.getElementById("upload-form");
    uploadForm.addEventListener("submit", handleUpload);

    // Train form
    const trainForm = document.getElementById("train-form");
    trainForm.addEventListener("submit", handleTrain);
}

// Upload CSV Dataset
async function handleUpload(e) {
    e.preventDefault();
    const fileInput = document.getElementById("csv-file");
    const feedback = document.getElementById("upload-feedback");
    const uploadBtn = document.getElementById("upload-btn");

    if (!fileInput.files.length) return;

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);
    formData.append("user_id", 1);

    uploadBtn.disabled = true;
    uploadBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Uploading...';
    feedback.className = "mt-3 alert alert-info py-2 small";
    feedback.textContent = "Processing and inspecting dataset...";
    feedback.classList.remove("d-none");

    try {
        const res = await fetch(`${API_BASE}/dataset/upload`, {
            method: "POST",
            body: formData
        });
        const data = await res.json();

        if (!res.ok) {
            throw new Error(data.error || "Upload failed");
        }

        currentDataset = data.dataset;
        feedback.className = "mt-3 alert alert-success py-2 small";
        feedback.textContent = `Uploaded ${currentDataset.filename} (${currentDataset.row_count} rows, ${currentDataset.column_count} columns)`;

        // Render preview table
        renderPreviewTable(data.preview, currentDataset.columns);

        // Populate Target Column Select
        populateTargetColumns(currentDataset.columns);

        // Enable train controls
        document.getElementById("target-column-select").disabled = false;
        document.getElementById("algorithm-select").disabled = false;
        document.getElementById("train-btn").disabled = false;

    } catch (err) {
        feedback.className = "mt-3 alert alert-danger py-2 small";
        feedback.textContent = err.message;
    } finally {
        uploadBtn.disabled = false;
        uploadBtn.innerHTML = '<i class="bi bi-upload me-1"></i>Upload & Inspect';
    }
}

function renderPreviewTable(previewRows, columns) {
    const table = document.getElementById("preview-table");
    const meta = document.getElementById("dataset-meta");

    meta.textContent = `${currentDataset.filename} • ${currentDataset.row_count} rows`;

    if (!previewRows || !previewRows.length) return;

    // Header
    const colNames = Object.keys(previewRows[0]);
    let theadHtml = "<tr>" + colNames.map(col => `<th>${col}</th>`).join("") + "</tr>";
    table.querySelector("thead").innerHTML = theadHtml;

    // Body
    let tbodyHtml = "";
    previewRows.forEach(row => {
        tbodyHtml += "<tr>" + colNames.map(c => `<td>${row[c] !== null ? row[c] : "<em>null</em>"}</td>`).join("") + "</tr>";
    });
    table.querySelector("tbody").innerHTML = tbodyHtml;
}

function populateTargetColumns(columns) {
    const select = document.getElementById("target-column-select");
    select.innerHTML = '<option value="">Select target variable...</option>' +
        columns.map(c => `<option value="${c.name}">${c.name} (${c.dtype})</option>`).join("");
}

// Train & Evaluate Model
async function handleTrain(e) {
    e.preventDefault();
    if (!currentDataset) return;

    const targetCol = document.getElementById("target-column-select").value;
    const algorithm = document.getElementById("algorithm-select").value;
    const splitRatio = document.getElementById("split-range").value;
    const trainBtn = document.getElementById("train-btn");
    const container = document.getElementById("evaluation-container");

    if (!targetCol || !algorithm) return;

    trainBtn.disabled = true;
    trainBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Training in progress...';
    container.innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary mb-3"></div>
            <p class="text-muted fw-semibold">Training ${algorithm.replace("_", " ").toUpperCase()} model on backend...</p>
        </div>
    `;

    try {
        const res = await fetch(`${API_BASE}/ml/train`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: jsonPayload = JSON.stringify({
                dataset_id: currentDataset.id,
                target_column: targetCol,
                algorithm: algorithm,
                split_ratio: splitRatio,
                user_id: 1
            })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Training failed");

        renderEvaluationResults(data.evaluation);

    } catch (err) {
        container.innerHTML = `<div class="alert alert-danger py-3">${err.message}</div>`;
    } finally {
        trainBtn.disabled = false;
        trainBtn.innerHTML = '<i class="bi bi-play-circle me-1"></i>Train & Evaluate Model';
    }
}

function renderEvaluationResults(evaluation) {
    const container = document.getElementById("evaluation-container");
    const metrics = evaluation.metrics;

    if (metrics.task_type === "classification") {
        container.innerHTML = `
            <div class="alert alert-success py-2 d-flex justify-content-between align-items-center mb-3">
                <span class="fw-semibold"><i class="bi bi-check-circle-fill me-1"></i>${evaluation.model_name.toUpperCase()} (Classification)</span>
                <span class="badge bg-success">Test Split: ${Math.round(evaluation.split_ratio * 100)}%</span>
            </div>
            <div class="row g-3 mb-4">
                <div class="col-6 col-md-3">
                    <div class="metric-card">
                        <div class="text-muted small">Accuracy</div>
                        <div class="metric-value">${(metrics.accuracy * 100).toFixed(1)}%</div>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="metric-card">
                        <div class="text-muted small">Precision</div>
                        <div class="metric-value">${(metrics.precision * 100).toFixed(1)}%</div>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="metric-card">
                        <div class="text-muted small">Recall</div>
                        <div class="metric-value">${(metrics.recall * 100).toFixed(1)}%</div>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="metric-card">
                        <div class="text-muted small">F1-Score</div>
                        <div class="metric-value">${(metrics.f1_score * 100).toFixed(1)}%</div>
                    </div>
                </div>
            </div>
            ${metrics.confusion_matrix ? `
                <div class="card bg-light border-0 p-3">
                    <h6 class="fw-bold mb-2">Confusion Matrix</h6>
                    <pre class="bg-white p-2 rounded border small mb-0">${JSON.stringify(metrics.confusion_matrix, null, 2)}</pre>
                </div>
            ` : ""}
        `;
    } else {
        container.innerHTML = `
            <div class="alert alert-success py-2 d-flex justify-content-between align-items-center mb-3">
                <span class="fw-semibold"><i class="bi bi-check-circle-fill me-1"></i>${evaluation.model_name.toUpperCase()} (Regression)</span>
                <span class="badge bg-success">Test Split: ${Math.round(evaluation.split_ratio * 100)}%</span>
            </div>
            <div class="row g-3">
                <div class="col-6 col-md-3">
                    <div class="metric-card">
                        <div class="text-muted small">R² Score</div>
                        <div class="metric-value">${metrics.r2_score}</div>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="metric-card">
                        <div class="text-muted small">RMSE</div>
                        <div class="metric-value">${metrics.rmse}</div>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="metric-card">
                        <div class="text-muted small">MAE</div>
                        <div class="metric-value">${metrics.mae}</div>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="metric-card">
                        <div class="text-muted small">MSE</div>
                        <div class="metric-value">${metrics.mse}</div>
                    </div>
                </div>
            </div>
        `;
    }
}
