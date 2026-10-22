# Web-Based ML Model Evaluator

A browser-based application for uploading CSV datasets, preparing supervised-learning experiments, training and evaluating classification or regression models, comparing runs, and exporting results. The complete documented scope includes Student, Instructor, and Admin roles.

## Project documentation

The project documents are the repository PDFs listed in [`documents/README.md`](documents/README.md). The Use Case Flows includes three additional use cases; the other PDFs contain their original repository pages. The existing UML diagram is unchanged. In particular, training-run recording maps to FR-4.3, metrics to FR-5.1, and comparison to FR-5.3.

## Roles

- **Student:** owns datasets and runs; can upload/replace/version datasets, configure preprocessing and target/split, train/evaluate/compare/export, and optionally share a completed result with Instructors.
- **Instructor:** read-only access to completed results explicitly shared by Students.
- **Admin:** manage account roles/status, archive or restore dataset records, and read audit events.

Public registration always creates a Student account. Use the trusted local Flask CLI command to grant the first Admin role.

## Requirements

- Python 3.9 or newer (3.13 supported by the project environment).
- A desktop Chrome, Firefox, or Edge browser.

## Accepted implementation policies

- **Accounts:** usernames are limited to 80 characters. Passwords must be 8–128 characters and are stored with Werkzeug's password hashing. Public registration creates Student accounts only.
- **Sessions:** browser cookies are HttpOnly and SameSite=Lax. Server-side sessions expire after 30 minutes without activity and 12 hours after login, and logout revokes the session. Deployed HTTPS environments must set `SESSION_COOKIE_SECURE=true` and provide a stable `SECRET_KEY`.
- **Login abuse:** after 10 failed attempts from one hashed remote-address key in 15 minutes, login is blocked for 15 minutes. Configure trusted proxy handling before relying on client IP behind a reverse proxy.
- **Uploads:** CSV only, UTF-8 or UTF-8 BOM, 16 MiB maximum full HTTP request including multipart overhead, unique non-empty column names, at least two columns and two data rows. Previews return at most 10 rows.
- **Training:** default split is 80/20 with deterministic random seed 42. Classification supports Logistic Regression, Decision Tree, Random Forest, and K-Nearest Neighbors. Regression supports Linear Regression, Decision Tree, Random Forest, and K-Nearest Neighbors.
- **Performance target:** health, login, dataset preview, and statistics target a P95 response time of 5 seconds on the documented local test environment. This target still needs a measured run before release.

The Flask development server binds to `127.0.0.1` with debug mode disabled by default. Set `HOST` only when access from other machines is intended, `FLASK_DEBUG=true` only for local development, and `CORS_ALLOWED_ORIGINS` to a comma-separated allowlist when a separately hosted frontend is required.

## Setup and run (PowerShell)

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:SECRET_KEY = 'replace-with-a-stable-random-secret-for-this-environment'
python app.py
```

Open `http://127.0.0.1:5000`. Local loopback HTTP is for development only. For deployment, terminate TLS, set `SESSION_COOKIE_SECURE=true`, use a stable secret, disable debug mode, and set the real allowed frontend origin.

### Grant the first Admin

After registering an account, stop the server or open another terminal in `backend/`, activate the environment, then run:

```powershell
$env:FLASK_APP = 'app.py'
flask promote-admin YOUR_USERNAME
```

Restart the app and sign in with that account. Only trusted local operators should run this command.

## Verification

Run backend tests from `backend/`:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q .
node --check ..\frontend\js\app.js
```

The repository Test Plan PDF lists the acceptance cases. A local automated pass does not verify browser compatibility, performance targets, deployment HTTPS, hosted dependency audit, or backup restoration.

Latest local verification on 2026-10-22: **45 Python tests passed**, Python compilation passed, and the frontend JavaScript syntax check passed. The PDF Test Plan remains the planned acceptance inventory; the 45 automated tests cover its automatable requirements but do not mark browser, performance, deployment, or recovery checks complete. Those checks still require a target browser/deployment environment and recorded evidence.

## Storage and operations

By default, SQLite data is stored in `backend/ml_evaluator.db`; CSV files are under `backend/uploads/`; trained pipelines are under `backend/saved_models/`. Existing SQLite schemas are upgraded on application startup. For a consistent backup, stop the app, copy the database and both storage directories together to a restricted location, then restore all three from the same snapshot while the app is stopped. Restart and verify a sample dataset, run, and artifact. Do not store backups in the repository.

Dependency updates are monitored through Dependabot, and `.github/workflows/dependency-audit.yml` runs `pip-audit` on relevant changes, weekly, or manually.

## Supported ML algorithms

| Task | Algorithms |
| --- | --- |
| Classification | Logistic Regression, Decision Tree, Random Forest, K-Nearest Neighbors |
| Regression | Linear Regression, Decision Tree, Random Forest, K-Nearest Neighbors |

Models are stored as scikit-learn pipelines so preprocessing is fitted on training data and reused with the saved model.
