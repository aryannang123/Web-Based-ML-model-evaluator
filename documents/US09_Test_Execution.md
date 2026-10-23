# US-09 Validation Test Execution Record

**Project:** Web-Based ML Model Evaluator
**Execution date:** 2026-10-23
**Scope:** US-09 uploaded dataset validation

## Result summary

| Verification | Result | Evidence |
| --- | --- | --- |
| US-09 upload tests | PASS | 11 tests passed with `python -m unittest discover -s tests -p 'test_dataset_upload.py' -v` from `backend/`. |
| Backend automated suite | PASS | 66 tests passed with `python -m unittest discover -s tests -v` from `backend/`. Windows temporary files were redirected to `backend/.test-tmp` because the sandbox temp directory is not writable. |
| Python source compilation | PASS | `python -m compileall -q backend` |
| Frontend JavaScript syntax | PASS | `node --check frontend/js/app.js` |
| Diff whitespace check | PASS | `git diff --check` |

## US-09 validation coverage

| Requirement / acceptance area | Coverage | Automated test evidence |
| --- | --- | --- |
| CSV-only and readable UTF-8 input | Unsupported extension, invalid UTF-8, empty file, malformed quoting, NUL bytes | `test_non_csv_extension_is_rejected`, `test_empty_file_is_rejected`, `test_invalid_csvs_are_rejected_with_clear_errors` |
| Required structure and minimum size | Non-empty unique headers; consistent row widths; at least 2 non-empty rows and at least 2 columns (feature and target); reject empty rows and columns with no data | `test_invalid_csvs_are_rejected_with_clear_errors`, `test_csv_meeting_the_two_row_two_column_minimum_is_accepted` |
| Upload size limit | HTTP 413 with JSON and an accurate configured limit in the message | `test_over_limit_upload_returns_json_413` |
| Ownership and persistence safety | Server derives owner from the authenticated session; failed database save rolls back and removes the stored file | `test_request_user_id_cannot_override_authenticated_owner`, `test_database_failure_rolls_back_and_removes_uploaded_file` |

## Policy decision

US-09 requires a minimum row count but does not specify its numeric value. This implementation sets the configurable minimum to **2 non-empty data rows** and **2 columns** (at least one feature and one target) in `backend/config.py`. Training-specific sample-count or class-count requirements remain the responsibility of model training validation. The 16 MiB Flask request limit includes multipart form overhead.

## Verification limits

Automated API tests validate upload and error behavior. A manual browser upload, cross-browser run, hosted deployment/proxy limit check, and performance test were not performed. The full suite emits existing `ResourceWarning` messages for open test response/database resources; they did not fail the test run.
