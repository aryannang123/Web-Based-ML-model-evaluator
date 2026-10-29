# US-14 Data Preprocessing – Test Execution Record

**Date:** 2026-10-28
**Tester:** @aryannang123
**Sprint:** Sprint 2
**Issue:** #14 – US-14: Implement data preprocessing
**Traceability:** SRS `FR-3.1`, Test Plan sections `3.3 Data Preparation`, `SEC-INP-1`

---

## Test Plan Coverage

| Test Plan ID | Section | Description | Result |
|---|---|---|---|
| **FR-3.1-UT-1** | 3.3 Data Preparation | Apply a supported preprocessing option to valid data | **PASS** |
| **FR-3.1-UT-2** | 3.3 Data Preparation | Reject incompatible preprocessing configuration | **PASS** |
| **SEC-INP-1-UT-1** | Security | Backend validates all user-controlled configuration identifiers | **PASS** |
| **SEC-AZ-2** | Security | User data isolation on preprocessing endpoint | **PASS** |

---

## Overall Suite Result

| Scope | Result | Details |
|---|---|---|
| **US-14 Dedicated Test Suite** | **PASS** | 40 tests passed in `test_us14_preprocessing.py` |
| **Full Backend Regression** | **PASS** | 129 tests passed across all test modules |

---

## US-14 Test Suite Details (`test_us14_preprocessing.py`)

### Class: `TestDataPreprocessorMissingValues` — FR-3.1-UT-1

| Test Case | Description | Result |
|---|---|---|
| `test_none_strategy_leaves_frame_unchanged` | Strategy 'none' returns identical copy of DataFrame | PASS |
| `test_drop_strategy_removes_rows_with_nulls` | Strategy 'drop' removes every row containing NaN | PASS |
| `test_mean_strategy_fills_numeric_nulls` | Strategy 'mean' fills numeric nulls with column mean | PASS |
| `test_median_strategy_fills_numeric_nulls` | Strategy 'median' fills numeric nulls with column median | PASS |
| `test_mode_strategy_fills_nulls_with_most_frequent` | Strategy 'mode' fills with most frequent value | PASS |
| `test_constant_strategy_fills_numeric_with_zero` | Strategy 'constant' fills numeric nulls with 0 by default | PASS |
| `test_mean_strategy_categorical_column_uses_mode` | Strategy 'mean' on categorical columns falls back to mode | PASS |
| `test_drop_raises_if_result_is_too_small` | Dropping all rows raises ValueError with useful message | PASS |

### Class: `TestDataPreprocessorEncoding` — FR-3.1-UT-1

| Test Case | Description | Result |
|---|---|---|
| `test_label_encoding_converts_strings_to_integers` | Label encoding produces integer-dtype columns for all categoricals | PASS |
| `test_onehot_encoding_expands_categorical_columns` | One-hot encoding expands each categorical feature into indicator columns | PASS |
| `test_none_encoding_leaves_frame_unchanged` | Strategy 'none' returns identical copy | PASS |
| `test_encoding_fills_null_cats_before_encoding` | Encoding handles categorical NaN values gracefully | PASS |

### Class: `TestDataPreprocessorScaling` — FR-3.1-UT-1

| Test Case | Description | Result |
|---|---|---|
| `test_minmax_scales_to_0_1` | MinMax normalization produces values in [0.0, 1.0] | PASS |
| `test_standard_scaling_produces_near_zero_mean` | Standardization produces mean ≈ 0 and std ≈ 1 | PASS |
| `test_scaling_excludes_target_column` | Scaling does not alter the target column values | PASS |
| `test_none_scaling_leaves_frame_unchanged` | Strategy 'none' returns values identical to input | PASS |

### Class: `TestDataPreprocessorPipeline` — FR-3.1-UT-1

| Test Case | Description | Result |
|---|---|---|
| `test_pipeline_applies_all_steps_in_order` | Pipeline (missing + encoding + scaling) completes without errors | PASS |
| `test_pipeline_returns_row_and_column_counts` | Summary dict contains rows_before, rows_after, columns_after | PASS |
| `test_pipeline_raises_on_invalid_target_column` | Pipeline raises ValueError for nonexistent target column | PASS |

### Class: `TestDataPreprocessorInvalidConfigs` — FR-3.1-UT-2 / SEC-INP-1

| Test Case | Description | Result |
|---|---|---|
| `test_invalid_missing_strategy_raises` | Unsupported missing-value strategy name raises ValueError | PASS |
| `test_invalid_encoding_strategy_raises` | Unsupported encoding strategy name raises ValueError | PASS |
| `test_invalid_scaling_strategy_raises` | Unsupported scaling strategy name raises ValueError | PASS |
| `test_scaling_on_non_numeric_column_raises` | Scaling applied to non-numeric columns raises ValueError | PASS |
| `test_scaling_with_missing_values_raises` | Scaling with remaining NaN values raises ValueError | PASS |
| `test_empty_dataframe_raises_in_pipeline` | Pipeline rejects DataFrame with fewer than 2 rows | PASS |

### Class: `TestPreprocessEndpoint` — API Integration (FR-3.1-UT-1, FR-3.1-UT-2, SEC-INP-1, SEC-AZ-2)

| Test Case | Description | Result |
|---|---|---|
| `test_mean_imputation_fills_missing_values` | FR-3.1-UT-1: Mean imputation on dataset with NaN values → HTTP 200 | PASS |
| `test_label_encoding_applied_to_dataset` | FR-3.1-UT-1: Label encoding on categorical columns → HTTP 200 | PASS |
| `test_onehot_encoding_expands_column_count` | FR-3.1-UT-1: One-hot encoding expands categorical columns | PASS |
| `test_minmax_scaling_applied_after_encoding` | FR-3.1-UT-1: MinMax scaling after label encoding → HTTP 200 | PASS |
| `test_standard_scaling_applied_after_encoding` | FR-3.1-UT-1: Standardization scaling after label encoding → HTTP 200 | PASS |
| `test_no_op_preprocessing_succeeds` | FR-3.1-UT-1: All-'none' config is valid → HTTP 200 | PASS |
| `test_response_contains_preview_rows` | API response includes sample preview rows | PASS |
| `test_invalid_missing_strategy_returns_400` | FR-3.1-UT-2 / SEC-INP-1: Invalid missing_values → HTTP 400 | PASS |
| `test_invalid_encoding_strategy_returns_400` | FR-3.1-UT-2 / SEC-INP-1: Invalid encoding → HTTP 400 | PASS |
| `test_invalid_scaling_strategy_returns_400` | FR-3.1-UT-2 / SEC-INP-1: Invalid scaling → HTTP 400 | PASS |
| `test_nonexistent_target_column_returns_400` | FR-3.1-UT-2: Nonexistent target_column → HTTP 400 | PASS |
| `test_scaling_without_encoding_on_mixed_data_returns_400` | FR-3.1-UT-2: Scaling before encoding on mixed data → HTTP 400 | PASS |
| `test_preprocess_unauthenticated_returns_401` | SEC-AZ-2: Unauthenticated request → HTTP 401 | PASS |
| `test_preprocess_another_users_dataset_returns_404` | SEC-AZ-2: User B cannot access User A's dataset → HTTP 404 | PASS |
| `test_preprocess_nonexistent_dataset_returns_404` | SEC-AZ-2: Non-existent dataset ID → HTTP 404 | PASS |

---

## Regression Results

Full suite executed with:
```
cd backend && python -m unittest discover -s tests -q
Ran 129 tests in 48.160s
OK
```

Previous suite baseline: 89 tests (US-14a merged). US-14 adds 40 new test cases.

---

## Acceptance Criteria Verification

| Acceptance Criterion | Status |
|---|---|
| Handle missing values by dropping or filling (mean, median, mode, constant) | ✅ DONE |
| Support label encoding and one-hot encoding for categorical features | ✅ DONE |
| Support MinMax normalization [0,1] and Z-score standardization | ✅ DONE |
| Apply selected preprocessing operations and update dataset preview & metadata | ✅ DONE |
| Display clear errors for invalid configurations | ✅ DONE |
