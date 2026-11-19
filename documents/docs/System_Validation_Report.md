# System Validation Report

For the related backend regression and coverage reports, see the [Testing Reports index](README.md).

- **Project:** Web-Based ML Model Evaluator
- **Execution date:** 10 November 2026
- **Branch / commit:** `feature/sprint2-demo-video` / `cf3328a`
- **Result:** **PASS — all recorded checks completed successfully**
- **Environment:** Windows, Python 3.13.5, Node.js 24.8.0, Playwright 1.56.0; isolated SQLite database, uploads, and model storage

## Validation summary

| Validation area | Checks | Result |
|---|---:|---|
| Backend regression suite | 215 | **215 passed, 0 failed** |
| Python source compilation (`app.py`, `config.py`, `database`, `models`, `routes`, `ml`) | 1 | PASS |
| Frontend JavaScript syntax (`node --check frontend/js/app.js`) | 1 | PASS |
| Backend health endpoint (`GET /api/health`) | 1 | PASS — HTTP 200, `status: healthy` |
| Primary browser journey: Chromium 141.0.7390.37 | 1 | PASS |
| Primary browser journey: Firefox 142.0.1 | 1 | PASS |
| Primary browser journey: WebKit 26.0 | 1 | PASS |
| **Recorded checks total** | **221** | **All passed** |

The 221 total combines the 215-test backend regression suite with six additional validation checks. It is a count of recorded checks, not a separate test-run summary produced by one command.

## Validation notes

- The browser journey covered registration, login, dashboard load, CSV upload, target and algorithm selection, model training/evaluation, and rendering the resulting SVG chart.
- The browser journeys completed without page-level JavaScript errors. The local server logged an HTTP 404 for the optional `/favicon.ico` request; it did not block the tested workflow.
- Tests used fresh accounts and isolated temporary storage. They did not write test records into the application's normal database.
- The detailed backend test breakdown is in [Unit Test Report](Unit_Test_Report.md). The captured system output is in [System_Validation_Run_Log.txt](System_Validation_Run_Log.txt).

## Test execution

The backend suite was run from `backend/` with:

```powershell
python -m unittest discover -s tests -p 'test_*.py' -v
```

The recorded system checks also included Python compilation, JavaScript syntax validation, the health endpoint, and the cross-browser smoke journeys. Their summarized output is preserved in [`System_Validation_Run_Log.txt`](System_Validation_Run_Log.txt).

## Scope limits

This is local validation evidence from the working tree at `cf3328a`, which contained uncommitted changes. It does not certify the latest `main`, a pull-request head, or a production deployment. Browser automation covered the primary Student journey; it was not a manual visual/accessibility audit and did not validate the Admin or Instructor UI journeys. Production HTTPS, public certificate trust, load testing, and live backup/restore were not part of this validation run. Performance and local TLS measurements, where applicable, are documented separately in the test execution record.
