/* Browser client for the Web-Based ML Model Evaluator. */

const API_BASE = "/api";
let activeDatasetId = null;

document.addEventListener("DOMContentLoaded", () => {
    checkBackendHealth();
    setupLoginForm();
    setupRegistrationForm();
    setupStudentDashboard();
    setupAdminDashboard();
    setupInstructorDashboard();
    restoreSession();
});

async function apiRequest(endpoint, options = {}) {
    let response;
    try {
        response = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            credentials: "same-origin",
            headers: {...options.headers}
        });
    } catch {
        throw new Error("Unable to connect to the server. Check your connection.");
    }

    const contentType = response.headers.get("content-type") || "";
    let data = {};
    if (contentType.includes("application/json")) {
        try {
            data = await response.json();
        } catch {
            throw new Error("The backend returned invalid JSON.");
        }
    } else if (!response.ok) {
        throw new Error(`The server returned HTTP ${response.status}.`);
    } else {
        throw new Error("The backend returned a non-JSON response.");
    }

    if (!response.ok) {
        throw new Error(data.error || data.message || `Request failed (${response.status}).`);
    }
    return data;
}

async function checkBackendHealth() {
    const badge = document.getElementById("api-status");
    if (!badge) return;
    try {
        const result = await apiRequest("/health");
        if (result.status !== "healthy") throw new Error("Backend is not healthy");
        badge.className = "badge bg-success me-3";
        badge.textContent = "API Connected";
    } catch (error) {
        badge.className = "badge bg-warning text-dark me-3";
        badge.textContent = "API Offline";
        console.error("Backend health check failed:", error.message);
    }
}

async function restoreSession() {
    const userElement = document.getElementById("current-user");
    if (!userElement) return;
    try {
        const result = await apiRequest("/auth/session");
        if (!result.authenticated) {
            window.location.replace("/login");
            return;
        }
        userElement.textContent = `${result.user.username} (${result.user.role})`;
    } catch {
        window.location.replace("/login");
    }
}

function setupLoginForm() {
    document.getElementById("login-form")?.addEventListener("submit", async event => {
        event.preventDefault();
        const feedback = document.getElementById("login-feedback");
        const button = event.currentTarget.querySelector('button[type="submit"]');
        button.disabled = true;
        feedback.textContent = "Signing in...";
        feedback.className = "mt-3 text-muted";
        try {
            const result = await apiRequest("/auth/login", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    username: document.getElementById("login-username").value.trim(),
                    password: document.getElementById("login-password").value
                })
            });
            window.location.assign(result.redirect_url || "/");
        } catch (error) {
            feedback.textContent = error.message;
            feedback.className = "mt-3 alert alert-danger";
        } finally {
            button.disabled = false;
        }
    });
}

function setupRegistrationForm() {
    document.getElementById("registration-form")?.addEventListener("submit", async event => {
        event.preventDefault();
        const feedback = document.getElementById("registration-feedback");
        try {
            const result = await apiRequest("/auth/register", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    username: document.getElementById("reg-username").value.trim(),
                    email: document.getElementById("reg-email").value.trim(),
                    password: document.getElementById("reg-password").value
                })
            });
            feedback.textContent = `${result.message} You can now sign in.`;
            feedback.className = "mt-3 alert alert-success";
            event.target.reset();
        } catch (error) {
            feedback.textContent = error.message;
            feedback.className = "mt-3 alert alert-danger";
        }
    });
}

function setupLogout() {
    document.getElementById("logout-btn")?.addEventListener("click", async () => {
        const button = document.getElementById("logout-btn");
        button.disabled = true;
        try {
            await apiRequest("/auth/logout", {method: "POST"});
            window.location.replace("/login");
        } catch (error) {
            button.disabled = false;
            window.alert(error.message);
        }
    });
}

function setupStudentDashboard() {
    if (!document.getElementById("upload-form")) return;
    setupLogout();
    document.getElementById("split-range")?.addEventListener("input", event => {
        const testPercent = Math.round(Number(event.target.value) * 100);
        document.getElementById("split-display").textContent =
            `${100 - testPercent}% Train / ${testPercent}% Test`;
    });
    document.getElementById("upload-mode")?.addEventListener("change", event => {
        document.getElementById("dataset-select-label").textContent =
            event.target.value === "replace" ? "Dataset to replace" : "Current dataset";
    });
    document.getElementById("upload-form").addEventListener("submit", uploadDataset);
    document.getElementById("preprocessing-form").addEventListener("submit", savePreprocessing);
    document.getElementById("save-target-btn").addEventListener("click", saveTarget);
    document.getElementById("train-form").addEventListener("submit", submitTraining);
    document.getElementById("refresh-history").addEventListener("click", refreshHistory);
    document.getElementById("compare-runs").addEventListener("click", compareSelectedRuns);
    document.getElementById("dataset-select").addEventListener("change", event => {
        if (event.target.value) loadDataset(Number(event.target.value));
    });
    refreshDatasets().catch(showPageError);
    refreshHistory().catch(showPageError);
}

async function uploadDataset(event) {
    event.preventDefault();
    const file = document.getElementById("csv-file").files[0];
    const feedback = document.getElementById("upload-feedback");
    if (!file) return setFeedback(feedback, "Choose a CSV file.", "danger");
    const mode = document.getElementById("upload-mode").value;
    const datasetId = Number(document.getElementById("dataset-select").value);
    if (mode === "replace" && !datasetId) {
        return setFeedback(feedback, "Choose a dataset to replace.", "danger");
    }
    const form = new FormData();
    form.append("file", file);
    try {
        setFeedback(feedback, "Validating and uploading CSV...", "info");
        const path = mode === "replace"
            ? `/dataset/${datasetId}/replace`
            : "/dataset/upload";
        const result = await apiRequest(path, {
            method: mode === "replace" ? "PUT" : "POST", body: form
        });
        activeDatasetId = result.dataset.id;
        await refreshDatasets();
        document.getElementById("dataset-select").value = String(activeDatasetId);
        await loadDataset(activeDatasetId);
        setFeedback(feedback,
            `Dataset ready: ${result.dataset.row_count} rows, ${result.dataset.column_count} columns.`,
            "success");
        event.target.reset();
    } catch (error) {
        setFeedback(feedback, error.message, "danger");
    }
}

async function refreshDatasets() {
    const result = await apiRequest("/dataset");
    const select = document.getElementById("dataset-select");
    const prior = activeDatasetId;
    select.replaceChildren();
    if (!result.datasets.length) {
        select.add(new Option("No datasets uploaded", ""));
        select.disabled = true;
    } else {
        select.disabled = false;
    }
    for (const dataset of result.datasets) {
        const option = document.createElement("option");
        option.value = dataset.id;
        option.textContent = `${dataset.filename} (${dataset.row_count} × ${dataset.column_count})`;
        select.append(option);
    }
    const uploadButton = document.getElementById("upload-btn");
    const replaceOption = document.querySelector('#upload-mode option[value="replace"]');
    replaceOption.disabled = result.datasets.length === 0;
    if (result.datasets.length) {
        const selection = result.datasets.some(item => item.id === prior)
            ? prior : result.datasets[0].id;
        activeDatasetId = selection;
        select.value = String(selection);
        await loadDataset(selection);
    } else {
        activeDatasetId = null;
        uploadButton.disabled = false;
        document.getElementById("target-column-select").disabled = true;
        document.getElementById("save-target-btn").disabled = true;
        document.getElementById("save-preprocessing").disabled = true;
    }
}

async function loadDataset(datasetId) {
    activeDatasetId = datasetId;
    const [details, preview, statistics] = await Promise.all([
        apiRequest(`/dataset/${datasetId}`),
        apiRequest(`/dataset/${datasetId}/preview`),
        apiRequest(`/dataset/${datasetId}/statistics`)
    ]);
    const dataset = details.dataset;
    document.getElementById("dataset-meta").textContent =
        `${dataset.row_count} rows · ${dataset.column_count} columns · ${formatBytes(dataset.file_size)}`;
    const missingTotal = Object.values(statistics.missing_values)
        .reduce((sum, count) => sum + count, 0);
    document.getElementById("dataset-statistics").textContent =
        `${missingTotal} missing cells`;
    renderPreview(preview);
    const targetSelect = document.getElementById("target-column-select");
    targetSelect.replaceChildren(new Option("Choose a target column...", ""));
    for (const column of preview.columns) {
        targetSelect.add(new Option(column, column));
    }
    targetSelect.disabled = false;
    document.getElementById("save-target-btn").disabled = false;
    document.getElementById("save-preprocessing").disabled = false;
    const options = dataset.preprocessing || {};
    document.getElementById("missing-strategy").value = options.missing_strategy || "impute";
    document.getElementById("numeric-imputer").value = options.numeric_imputer || "median";
    document.getElementById("encode-categorical").checked = options.encode_categorical !== false;
    document.getElementById("scale-numeric").checked = options.scale_numeric !== false;
    if (dataset.target_column) {
        targetSelect.value = dataset.target_column;
        document.getElementById("task-type-display").textContent =
            `Detected: ${dataset.task_type}`;
        await loadAlgorithms(dataset.task_type);
    }
}

function renderPreview(preview) {
    const table = document.getElementById("preview-table");
    const head = table.querySelector("thead");
    const body = table.querySelector("tbody");
    head.replaceChildren();
    body.replaceChildren();
    const headerRow = document.createElement("tr");
    for (const column of preview.columns) {
        const th = document.createElement("th");
        th.textContent = column;
        headerRow.append(th);
    }
    head.append(headerRow);
    for (const row of preview.rows) {
        const tr = document.createElement("tr");
        for (const column of preview.columns) {
            const td = document.createElement("td");
            td.textContent = row[column] === null ? "" : String(row[column]);
            tr.append(td);
        }
        body.append(tr);
    }
}

async function savePreprocessing(event) {
    event.preventDefault();
    if (!activeDatasetId) return;
    const options = {
        missing_strategy: document.getElementById("missing-strategy").value,
        numeric_imputer: document.getElementById("numeric-imputer").value,
        encode_categorical: document.getElementById("encode-categorical").checked,
        scale_numeric: document.getElementById("scale-numeric").checked
    };
    try {
        const result = await apiRequest(`/dataset/${activeDatasetId}/preprocess`, {
            method: "POST", headers: {"Content-Type": "application/json"},
            body: JSON.stringify(options)
        });
        setFeedback(document.getElementById("preprocessing-feedback"), result.message, "success");
    } catch (error) {
        setFeedback(document.getElementById("preprocessing-feedback"), error.message, "danger");
    }
}

async function saveTarget() {
    if (!activeDatasetId) return;
    const targetColumn = document.getElementById("target-column-select").value;
    try {
        const result = await apiRequest(`/dataset/${activeDatasetId}/target`, {
            method: "POST", headers: {"Content-Type": "application/json"},
            body: JSON.stringify({target_column: targetColumn})
        });
        document.getElementById("task-type-display").textContent = `Detected: ${result.task_type}`;
        await loadAlgorithms(result.task_type);
    } catch (error) {
        showPageError(error);
    }
}

async function loadAlgorithms(taskType) {
    const data = await apiRequest("/ml/algorithms");
    const select = document.getElementById("algorithm-select");
    select.replaceChildren(new Option("Choose an algorithm...", ""));
    for (const algorithm of data[taskType] || []) {
        const label = {
            logistic_regression: "Logistic Regression",
            linear_regression: "Linear Regression",
            decision_tree: "Decision Tree",
            random_forest: "Random Forest",
            knn: "K-Nearest Neighbors"
        }[algorithm] || algorithm;
        select.add(new Option(label, algorithm));
    }
    select.disabled = false;
    document.getElementById("train-btn").disabled = false;
}

async function submitTraining(event) {
    event.preventDefault();
    if (!activeDatasetId) return showPageError(new Error("Upload a dataset first."));
    const button = document.getElementById("train-btn");
    const originalLabel = button.textContent;
    button.disabled = true;
    button.textContent = "Training in progress...";
    try {
        const result = await apiRequest("/ml/train", {
            method: "POST", headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                dataset_id: activeDatasetId,
                target_column: document.getElementById("target-column-select").value,
                algorithm: document.getElementById("algorithm-select").value,
                test_size: Number(document.getElementById("split-range").value),
                share_with_instructors: document.getElementById("share-instructor").checked
            })
        });
        renderRunResult(result.run);
        await refreshHistory();
    } catch (error) {
        showPageError(error);
    } finally {
        button.disabled = false;
        button.textContent = originalLabel;
    }
}

function renderRunResult(run) {
    const container = document.getElementById("evaluation-container");
    container.replaceChildren();
    const title = document.createElement("h5");
    title.textContent = `${run.model_name} · ${run.task_type}`;
    container.append(title);
    const meta = document.createElement("p");
    meta.className = "text-muted small";
    meta.textContent = `${run.algorithm} · target ${run.target_column} · ${run.configuration.train_rows} train / ${run.configuration.test_rows} test rows`;
    container.append(meta);
    appendMetrics(container, run.metrics);
    if (run.confusion_matrix) appendConfusionMatrix(container, run.confusion_matrix, run.report?.classes || []);
    if (run.visualization?.kind === "regression_residuals") {
        appendResidualPlot(container, run.visualization.points || []);
    }
}

async function refreshHistory() {
    const body = document.getElementById("run-history-body");
    if (!body) return;
    const data = await apiRequest("/ml/runs");
    body.replaceChildren();
    if (!data.runs.length) {
        const row = body.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 8;
        cell.className = "text-muted p-3";
        cell.textContent = "No runs yet.";
        return;
    }
    for (const run of data.runs) {
        const row = body.insertRow();
        const compareCell = row.insertCell();
        if (run.status === "completed") {
            const checkbox = document.createElement("input");
            checkbox.type = "checkbox";
            checkbox.className = "form-check-input compare-run";
            checkbox.value = run.id;
            compareCell.append(checkbox);
        }
        row.insertCell().textContent = `#${run.id} ${run.model_name}`;
        row.insertCell().textContent = run.dataset_name || "(dataset removed)";
        row.insertCell().textContent = run.algorithm;
        row.insertCell().textContent = `${run.task_type} · ${run.target_column}`;
        row.insertCell().textContent = run.status === "completed"
            ? metricSummary(run.metrics) : run.status;
        const shareCell = row.insertCell();
        if (run.status === "completed") {
            const checkbox = document.createElement("input");
            checkbox.type = "checkbox";
            checkbox.className = "form-check-input";
            checkbox.checked = run.is_shared_with_instructors;
            checkbox.setAttribute("aria-label", `Share run ${run.id} with instructors`);
            checkbox.addEventListener("change", () => toggleSharing(run.id, checkbox));
            shareCell.append(checkbox);
        }
        const downloadCell = row.insertCell();
        if (run.status === "completed") {
            downloadCell.append(
                makeActionButton("Model", () => downloadFile(`/ml/runs/${run.id}/download/model`)),
                document.createTextNode(" "),
                makeActionButton("Report", () => downloadFile(`/ml/runs/${run.id}/download/report`))
            );
        }
    }
}

async function toggleSharing(runId, checkbox) {
    checkbox.disabled = true;
    try {
        await apiRequest(`/ml/runs/${runId}/share`, {
            method: "PATCH", headers: {"Content-Type": "application/json"},
            body: JSON.stringify({shared: checkbox.checked})
        });
    } catch (error) {
        checkbox.checked = !checkbox.checked;
        showPageError(error);
    } finally {
        checkbox.disabled = false;
    }
}

async function compareSelectedRuns() {
    const ids = [...document.querySelectorAll(".compare-run:checked")]
        .map(input => Number(input.value));
    const output = document.getElementById("comparison-output");
    output.replaceChildren();
    try {
        const result = await apiRequest("/ml/compare", {
            method: "POST", headers: {"Content-Type": "application/json"},
            body: JSON.stringify({run_ids: ids})
        });
        const table = document.createElement("table");
        table.className = "table table-sm table-bordered";
        const header = table.insertRow();
        ["Run", "Algorithm", "Task", "Metrics"].forEach(value => {
            header.insertCell().textContent = value;
        });
        for (const run of result.runs) {
            const row = table.insertRow();
            [run.model_name, run.algorithm, run.task_type, metricSummary(run.metrics)]
                .forEach(value => row.insertCell().textContent = value || "");
        }
        output.append(table);
        appendComparisonChart(output, result.runs);
    } catch (error) {
        setFeedback(output, error.message, "danger");
    }
}

async function downloadFile(path) {
    try {
        const response = await fetch(`${API_BASE}${path}`, {credentials: "same-origin"});
        if (!response.ok) {
            const result = await response.json().catch(() => ({}));
            throw new Error(result.error || `Download failed (${response.status}).`);
        }
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = response.headers.get("content-disposition")?.match(/filename="?([^";]+)"?/)?.[1] || "download";
        document.body.append(anchor);
        anchor.click();
        anchor.remove();
        URL.revokeObjectURL(url);
    } catch (error) {
        showPageError(error);
    }
}

function setupAdminDashboard() {
    if (!document.getElementById("admin-users-body")) return;
    setupLogout();
    document.getElementById("refresh-users").addEventListener("click", refreshAdminUsers);
    document.getElementById("refresh-datasets").addEventListener("click", refreshAdminDatasets);
    document.getElementById("refresh-logs").addEventListener("click", refreshAdminLogs);
    refreshAdminUsers().catch(showPageError);
    refreshAdminDatasets().catch(showPageError);
    refreshAdminLogs().catch(showPageError);
}

async function refreshAdminUsers() {
    const body = document.getElementById("admin-users-body");
    if (!body) return;
    const result = await apiRequest("/admin/users");
    body.replaceChildren();
    for (const user of result.users) {
        const row = body.insertRow();
        row.insertCell().textContent = user.id;
        row.insertCell().textContent = user.username;
        row.insertCell().textContent = user.email;
        const roleCell = row.insertCell();
        const role = document.createElement("select");
        role.className = "form-select form-select-sm";
        ["student", "instructor", "admin"].forEach(value => role.add(new Option(value, value)));
        role.value = user.role;
        roleCell.append(role);
        const activeCell = row.insertCell();
        const active = document.createElement("input");
        active.type = "checkbox";
        active.className = "form-check-input";
        active.checked = user.is_active;
        activeCell.append(active);
        row.insertCell().textContent = user.created_at || "";
        const actionCell = row.insertCell();
        actionCell.append(makeActionButton("Save", async () => {
            try {
                await apiRequest(`/admin/users/${user.id}`, {
                    method: "PATCH", headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({role: role.value, is_active: active.checked})
                });
                showAdminFeedback("User updated.", "success");
                await refreshAdminUsers();
            } catch (error) {
                showAdminFeedback(error.message, "danger");
            }
        }));
    }
}

async function refreshAdminDatasets() {
    const body = document.getElementById("admin-datasets-body");
    if (!body) return;
    const result = await apiRequest("/admin/datasets?include_archived=true");
    body.replaceChildren();
    for (const dataset of result.datasets) {
        const row = body.insertRow();
        row.insertCell().textContent = dataset.id;
        row.insertCell().textContent = dataset.owner_username;
        row.insertCell().textContent = dataset.filename;
        row.insertCell().textContent = `${dataset.row_count} × ${dataset.column_count}`;
        row.insertCell().textContent = dataset.is_archived ? "Archived" : "Active";
        const actionCell = row.insertCell();
        actionCell.append(makeActionButton(dataset.is_archived ? "Restore" : "Archive", async () => {
            try {
                await apiRequest(`/admin/datasets/${dataset.id}`, {
                    method: "PATCH", headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({is_archived: !dataset.is_archived})
                });
                await refreshAdminDatasets();
            } catch (error) {
                showAdminFeedback(error.message, "danger");
            }
        }));
    }
}

async function refreshAdminLogs() {
    const body = document.getElementById("admin-logs-body");
    if (!body) return;
    const result = await apiRequest("/admin/logs?limit=100");
    body.replaceChildren();
    for (const event of result.events) {
        const row = body.insertRow();
        row.insertCell().textContent = event.created_at || "";
        row.insertCell().textContent = event.actor_username || "System/anonymous";
        row.insertCell().textContent = event.event_type;
        row.insertCell().textContent = [event.target_type, event.target_id].filter(Boolean).join(" #");
        row.insertCell().textContent = JSON.stringify(event.details);
    }
}

function setupInstructorDashboard() {
    if (!document.getElementById("instructor-results-body")) return;
    setupLogout();
    document.getElementById("refresh-results").addEventListener("click", refreshInstructorResults);
    refreshInstructorResults().catch(showPageError);
}

async function refreshInstructorResults() {
    const body = document.getElementById("instructor-results-body");
    if (!body) return;
    const result = await apiRequest("/instructor/results");
    body.replaceChildren();
    if (!result.results.length) {
        const row = body.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 7;
        cell.className = "text-muted p-3";
        cell.textContent = "No results have been shared for review.";
        return;
    }
    for (const item of result.results) {
        const row = body.insertRow();
        row.insertCell().textContent = `#${item.id} ${item.model_name}`;
        row.insertCell().textContent = item.owner_username;
        row.insertCell().textContent = item.dataset?.filename || "";
        row.insertCell().textContent = item.algorithm;
        row.insertCell().textContent = `${item.task_type} · ${item.target_column}`;
        row.insertCell().textContent = metricSummary(item.metrics);
        const action = row.insertCell();
        action.append(makeActionButton("View", () => renderInstructorDetail(item)));
    }
}

function appendMetrics(container, metrics) {
    if (!metrics) return;
    const table = document.createElement("table");
    table.className = "table table-sm table-bordered w-auto";
    for (const [name, value] of Object.entries(metrics)) {
        const row = table.insertRow();
        row.insertCell().textContent = name.replaceAll("_", " ");
        const valueCell = row.insertCell();
        valueCell.textContent = Number(value).toFixed(4);
        const meter = document.createElement("div");
        meter.className = "progress mt-1";
        meter.setAttribute("aria-label", `${name} metric chart`);
        const bar = document.createElement("div");
        bar.className = "progress-bar";
        bar.style.width = `${Math.max(0, Math.min(100, Number(value) * 100))}%`;
        meter.append(bar);
        valueCell.append(meter);
    }
    container.append(table);
}

function appendResidualPlot(container, points) {
    if (!points.length) return;
    const title = document.createElement("h6");
    title.textContent = "Residual plot (prediction vs. residual)";
    container.append(title);
    const svgNs = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(svgNs, "svg");
    svg.setAttribute("viewBox", "0 0 600 260");
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", "Scatter plot of model predictions and residuals");
    svg.classList.add("w-100", "border", "rounded", "bg-white");
    const xs = points.map(point => point.predicted);
    const ys = points.map(point => point.residual);
    let xMin = Math.min(...xs), xMax = Math.max(...xs);
    let yMin = Math.min(...ys), yMax = Math.max(...ys);
    if (xMin === xMax) { xMin -= 1; xMax += 1; }
    if (yMin === yMax) { yMin -= 1; yMax += 1; }
    const left = 42, right = 585, top = 15, bottom = 225;
    const zeroY = bottom - ((0 - yMin) / (yMax - yMin)) * (bottom - top);
    const axis = document.createElementNS(svgNs, "path");
    axis.setAttribute("d", `M${left},${top} V${bottom} H${right} M${left},${zeroY} H${right}`);
    axis.setAttribute("stroke", "#6c757d");
    axis.setAttribute("stroke-dasharray", `1 1`);
    axis.setAttribute("fill", "none");
    svg.append(axis);
    for (const point of points) {
        const circle = document.createElementNS(svgNs, "circle");
        const cx = left + ((point.predicted - xMin) / (xMax - xMin)) * (right - left);
        const cy = bottom - ((point.residual - yMin) / (yMax - yMin)) * (bottom - top);
        circle.setAttribute("cx", String(cx));
        circle.setAttribute("cy", String(cy));
        circle.setAttribute("r", "3");
        circle.setAttribute("fill", "#0d6efd");
        svg.append(circle);
    }
    container.append(svg);
}

function appendComparisonChart(container, runs) {
    if (runs.length < 2) return;
    const task = runs[0].task_type;
    const metricName = task === "classification" ? "accuracy" : "rmse";
    const values = runs.map(run => Number(run.metrics?.[metricName])).filter(Number.isFinite);
    if (values.length !== runs.length) return;
    const title = document.createElement("h6");
    title.textContent = `Comparison chart: ${metricName} (lower is better for RMSE)`;
    container.append(title);
    const chart = document.createElement("div");
    chart.className = "vstack gap-2";
    const max = Math.max(...values, task === "classification" ? 1 : 0.0001);
    runs.forEach((run, index) => {
        const line = document.createElement("div");
        line.className = "d-flex align-items-center gap-2";
        const label = document.createElement("span");
        label.className = "small text-truncate";
        label.style.width = "160px";
        label.textContent = run.model_name;
        const track = document.createElement("div");
        track.className = "progress flex-grow-1";
        const bar = document.createElement("div");
        bar.className = "progress-bar";
        bar.style.width = `${Math.max(1, Math.min(100, values[index] / max * 100))}%`;
        bar.setAttribute("aria-label", `${run.model_name}: ${values[index]}`);
        track.append(bar);
        const score = document.createElement("span");
        score.className = "small";
        score.textContent = values[index].toFixed(4);
        line.append(label, track, score);
        chart.append(line);
    });
    container.append(chart);
}

function renderInstructorDetail(item) {
    const container = document.getElementById("instructor-detail");
    if (!container) return;
    container.replaceChildren();
    const heading = document.createElement("h2");
    heading.className = "h5";
    heading.textContent = `Run #${item.id}: ${item.model_name}`;
    container.append(heading);
    appendMetrics(container, item.metrics);
    if (item.confusion_matrix) {
        appendConfusionMatrix(container, item.confusion_matrix, item.report?.classes || []);
    }
    if (item.visualization?.kind === "regression_residuals") {
        appendResidualPlot(container, item.visualization.points || []);
    }
    container.scrollIntoView({behavior: "smooth", block: "nearest"});
}

function appendConfusionMatrix(container, matrix, classes) {
    if (!matrix) return;
    const heading = document.createElement("h6");
    heading.textContent = "Confusion matrix";
    container.append(heading);
    const table = document.createElement("table");
    table.className = "table table-sm table-bordered w-auto";
    const header = table.insertRow();
    header.insertCell().textContent = "Actual / Predicted";
    (classes || []).forEach(label => header.insertCell().textContent = String(label));
    matrix.forEach((values, index) => {
        const row = table.insertRow();
        row.insertCell().textContent = String(classes?.[index] ?? index);
        values.forEach(value => row.insertCell().textContent = String(value));
    });
    container.append(table);
}

function metricSummary(metrics) {
    return Object.entries(metrics || {})
        .map(([name, value]) => `${name} ${Number(value).toFixed(3)}`)
        .join(" · ");
}

function makeActionButton(label, action) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "btn btn-sm btn-outline-primary me-1";
    button.textContent = label;
    button.addEventListener("click", action);
    return button;
}

function setFeedback(element, message, variant) {
    if (!element) return;
    element.textContent = message;
    element.className = `mt-2 alert alert-${variant}`;
}

function showPageError(error) {
    const feedback = document.getElementById("admin-feedback")
        || document.getElementById("instructor-feedback");
    if (feedback) {
        setFeedback(feedback, error.message, "danger");
        feedback.classList.remove("d-none");
        return;
    }
    const uploadFeedback = document.getElementById("upload-feedback");
    if (uploadFeedback) setFeedback(uploadFeedback, error.message, "danger");
    else window.alert(error.message);
}

function showAdminFeedback(message, variant) {
    const feedback = document.getElementById("admin-feedback");
    setFeedback(feedback, message, variant);
    feedback.classList.remove("d-none");
}

function formatBytes(value) {
    if (!Number.isFinite(Number(value))) return "size unknown";
    return `${(Number(value) / (1024 * 1024)).toFixed(2)} MiB`;
}
