# Sprint 2 (US-11–US-20) Test Execution Record

**Project:** Web-Based ML Model Evaluator
**Execution date:** 2026-10-29
**Branch:** `US-17`
**Base revision:** `e1fe96e` (latest fetched `origin/main`)
**Scope:** Sprint 2 dataset, model pipeline, evaluation, comparison/export, run-history, and instructor-review tests.
**Traceability:** `Corrected_Test_Plan.md`, sections 3.2–3.6; requirements FR-2.3, FR-2.4, FR-3.1–FR-3.3, FR-4.1–FR-4.4, FR-5.4, FR-6.1, FR-7.4 and FR-7.5.

---

## 1. Overall Results

| Verification | Result | Evidence |
|---|---|---|
| Full backend regression suite | **PASS** | 156 tests passed using `python -m unittest discover -s tests -q` from `backend/`. |
| Browser JavaScript syntax | **PASS** | `node --check frontend/js/app.js` completed without syntax errors. |
| Git whitespace validation | **PASS** | `git diff --check` reported no whitespace errors. |
| Manual browser workflow | **NOT RUN** | Requires a human browser review of registration/login, student workflow, downloads, and instructor review. |
| Performance/deployment checks | **NOT RUN** | No hosted environment or performance run was part of this local automated test run. |

`PASS` above means the listed automated check was run and passed. `NOT RUN` is not a pass or a failure. The detailed master test plan's blank Actual Result/Test Result cells remain unchanged; this document records only this execution.

## 2. Sprint 2 Traceability

| Story / plan area | Verification performed | Result |
|---|---|---|
| US-11 dataset replacement | `test_us11_replacement_updates_owned_dataset_without_changing_its_id`; `test_us11_replacement_of_another_users_dataset_is_hidden` | **PASS** |
| US-12 preview | Existing authenticated preview, missing-value serialization, authorization, missing/malformed file tests in `test_dataset_upload.py` | **PASS** |
| US-13 statistics | `test_statistics_returns_numeric_summary_and_missing_counts` in `test_dataset_upload.py` | **PASS** |
| US-14 preprocessing | Existing preprocessing endpoint and data-transform tests in `test_us14_preprocessing.py` | **PASS** |
| US-15 target selection (FR-3.2) | `test_us15_target_column_is_validated_and_bad_requests_do_not_save_runs` | **PASS** |
| US-16 split (FR-3.3) | Split defaults, custom ratios, invalid bounds, endpoint behavior, and split-size tests in `test_train_test_split.py` | **PASS** |
| US-17 algorithm selection (FR-4.1) | Catalog contents, classification/regression compatibility, and fitting every supported estimator in `test_train_test_split.py` | **PASS** |
| US-18 training (FR-4.2) | Successful train endpoint and `test_us18_failed_training_does_not_remove_prior_successful_run` | **PASS** |
| US-19 evaluation (FR-4.3) | Deterministic classification and regression metric checks in `test_evaluation_metrics.py`; frontend confusion-matrix wiring check | **PASS** |
| US-20 compare/export/history (FR-4.4, FR-5.4, FR-6.1) | Owner comparison, invalid/missing and mixed-task rejection, model download, PDF report, and history checks in `test_train_test_split.py` | **PASS** |
| US-19a instructor review (FR-7.4, FR-7.5) | Shared-only visibility, private-run denial, instructor write denial, and frontend read-only mode wiring | **PASS** |

## 3. New/Expanded Automated Cases

| Test case | Purpose | Result |
|---|---|---|
| `test_us11_replacement_updates_owned_dataset_without_changing_its_id` | Replacing an owned dataset updates its metadata/file while retaining its record ID. | PASS |
| `test_us11_replacement_of_another_users_dataset_is_hidden` | A different account cannot replace the dataset. | PASS |
| `test_us15_target_column_is_validated_and_bad_requests_do_not_save_runs` | Missing target columns fail before creating an evaluation. | PASS |
| `test_us17_catalog_and_every_algorithm_task_pair_are_supported` | API catalog matches the supported classification/regression algorithms and mismatched tasks are rejected. | PASS |
| `test_us17_all_supported_estimators_fit_for_their_task_type` | Every advertised estimator can fit and predict on a deterministic mixed-feature dataset. | PASS |
| `test_us18_failed_training_does_not_remove_prior_successful_run` | A rejected run leaves a previously completed result in history. | PASS |
| `test_fr43_classification_metrics_and_confusion_matrix` | Classification metrics and confusion-matrix counts match known values. | PASS |
| `test_fr43_regression_metrics_match_known_values` | MSE, RMSE, and R² match known values. | PASS |
| `test_us20_compare_and_download_artifacts_for_owner` | Owner can compare compatible runs and download model/PDF artifacts. | PASS |
| `test_us20_comparison_rejects_invalid_and_missing_run_requests` | Invalid selection sizes and inaccessible run IDs are rejected. | PASS |
| `test_us20_comparison_rejects_mixed_classification_and_regression` | Cross-task comparisons are rejected with a client error. | PASS |
| `test_us19a_instructor_sees_only_shared_runs_and_cannot_write` | Instructor sees explicitly shared results only and receives 403 on write actions. | PASS |
| `test_us17_to_us20_frontend_catalog_history_comparison_and_review_are_wired` | Dashboard wiring exists for catalog, history, comparison, confusion matrix, and instructor mode. | PASS |

## 4. Remaining Manual Verification

- Sign in as a student, upload and replace a CSV, inspect preview/statistics, configure preprocessing, choose a target/algorithm/split, and run both a classification and a regression evaluation.
- Inspect the confusion matrix and metric output in a browser; select two compatible runs and compare them.
- Download a model and PDF report and verify the files open and match the selected run.
- Share a run, sign in as an instructor, verify only that shared run is visible, then try upload/preprocess/train controls and direct API writes.
- Record supported-browser and deployment/performance outcomes separately when those environments are available.

No commit or push was performed for this execution.
