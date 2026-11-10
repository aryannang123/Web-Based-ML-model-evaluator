# Unit Test Report

**Project:** Web-Based ML Model Evaluator  
**Execution date:** 2026-11-10  
**Branch / HEAD:** `feature/sprint2-demo-video` / `cf3328a`  
**Environment:** Windows, Python 3.13.5, Flask test client, isolated temporary SQLite databases  
**Command:** `python -m unittest discover -s tests -p 'test_*.py' -v` from `backend/`

## Final result

| Total | Passed | Failed | Errors | Outcome |
|---:|---:|---:|---:|---|
| 215 | 215 | 0 | 0 | PASS |

## Resolution of the first run

The first run had 214 passing tests and one failure in `test_release_gaps.TestReleaseGapImplementations.test_database_schema_document_matches_current_model_inventory`. The schema document described the evaluation/model ownership trigger but did not use the exact phrase `owners match`, which the documentation consistency test expects. I revised the schema sentence to state that evaluation and model owners match, preserving the same implemented constraint, then reran the entire backend suite. All 215 tests passed on the rerun.

The original failed-run output is retained in [`unit_test_run_initial_failure.txt`](unit_test_run_initial_failure.txt); the final passing run is [`unit_test_run.txt`](unit_test_run.txt).

## Scope and limitations

This was a full backend unit/integration regression discovery run. It ran against the local working tree at the revision above; the working tree had uncommitted changes, so it does not certify the branch commit alone, latest `main`, or the open PR head. The change that resolved the failure was documentation wording only; no application behavior or test assertion was changed.
