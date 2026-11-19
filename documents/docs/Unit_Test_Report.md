# Unit Test Report

For the related system-validation and coverage reports, see the [Testing Reports index](README.md).

- **Project:** Web-Based ML Model Evaluator
- **Execution date:** 10 November 2026
- **Branch / commit:** `feature/sprint2-demo-video` / `cf3328a`
- **Result:** **PASS — 215 of 215 tests passed**
- **Runtime:** Windows, Python 3.13.5, `unittest`, Flask test client, temporary SQLite databases

## Test results

| Test module | Tests | Passed | Failed / errors |
|---|---:|---:|---:|
| `test_auth_dataset_integration.py` | 5 | 5 | 0 |
| `test_auth_login.py` | 7 | 7 | 0 |
| `test_auth_logout.py` | 9 | 9 | 0 |
| `test_auth_registration.py` | 6 | 6 | 0 |
| `test_backup_restore_procedure.py` | 1 | 1 | 0 |
| `test_dataset_upload.py` | 22 | 22 | 0 |
| `test_evaluation_metrics.py` | 3 | 3 | 0 |
| `test_evaluation_ownership.py` | 5 | 5 | 0 |
| `test_frontend_backend_integration.py` | 11 | 11 | 0 |
| `test_release_gaps.py` | 9 | 9 | 0 |
| `test_train_test_split.py` | 19 | 19 | 0 |
| `test_us01_us05_acceptance.py` | 12 | 12 | 0 |
| `test_us07_data_isolation.py` | 6 | 6 | 0 |
| `test_us14_preprocessing.py` | 40 | 40 | 0 |
| `test_us14a_rbac_admin.py` | 11 | 11 | 0 |
| `test_us18_model_training.py` | 42 | 42 | 0 |
| `test_us20_model_comparison.py` | 7 | 7 | 0 |
| **Total** | **215** | **215** | **0** |

## Scope

The suite exercises authentication and sessions, CSV upload and validation, data isolation, preprocessing, train/test splitting, model training, metrics, model comparison and download, role-based access, and backup/restore helper behavior. Several tests make Flask HTTP requests and use temporary SQLite databases, so this is a backend unit/integration regression suite rather than a set of isolated function-only unit tests.

## Execution and resolution

Run from `backend/`:

```powershell
python -m unittest discover -s tests -p 'test_*.py' -v
```

The recorded final run completed in **63.881 seconds**. The first run had 214 passing tests and one failure in `test_release_gaps.TestReleaseGapImplementations.test_database_schema_document_matches_current_model_inventory`: the schema described the model/evaluation ownership constraint but omitted the exact phrase `owners match` asserted by the documentation-consistency test. The schema wording was clarified and the suite was rerun; all 215 tests then passed. No application behavior or test assertion was changed to obtain the passing result.

The final raw run is [`unit_test_run.txt`](unit_test_run.txt). The earlier failure is preserved in [`unit_test_run_initial_failure.txt`](unit_test_run_initial_failure.txt).

## Scope limits

This run was executed on a local working tree at `cf3328a` that contained uncommitted changes. It does not certify the commit alone, the latest `main`, or a pull-request head. Some non-failing SQLAlchemy deprecation and Python resource warnings appeared in the output; the test process ended with `Ran 215 tests` and `OK`.
