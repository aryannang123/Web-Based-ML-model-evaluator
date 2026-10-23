# US-06 and US-07 Test Execution Record

**Project:** Web-Based ML Model Evaluator
**Execution date:** 2026-10-23
**Scope:** US-06 logout and session management; US-07 user data isolation

## Result summary

| Verification | Result | Evidence |
| --- | --- | --- |
| Backend automated suite | PASS | 45 tests passed with `python -m unittest discover -s tests -v` from `backend/` |
| Frontend JavaScript syntax | PASS | `node --check frontend/js/app.js` |
| Python source compilation | PASS | `python -m compileall -q backend` |
| Diff whitespace check | PASS | `git diff --check` |

## Test Plan traceability

| Test Plan ID | Coverage in this execution | Automated test |
| --- | --- | --- |
| SEC-SES-2-ST-1 | Idle-expired session is denied and requires reauthentication | `test_session_expiration_requires_reauthentication` |
| SEC-SES-3-ST-1 | Replaying a cookie captured before logout is rejected | `test_sec_ses_3_st_1_replayed_cookie_is_rejected_after_logout` |
| FR-2.5-ST-2 | Dataset metadata listing is restricted to the authenticated owner | `test_fr_2_5_st_2_each_user_lists_only_their_dataset_metadata` |
| FR-6.1-ST-2 | Model and evaluation history is restricted to the authenticated owner | `test_fr_6_1_st_2_run_and_evaluation_history_is_private` |
| SEC-AZ-2-ST-1 | Direct foreign dataset, model, and evaluation IDs are denied; mismatched ownership links are denied | `test_sec_az_2_st_1_foreign_dataset_model_and_evaluation_ids_are_denied`; `test_mismatched_model_or_evaluation_ownership_is_never_visible` |
| NFR-4-ST-1 | Anonymous direct API requests are rejected by server authorization | `test_nfr_4_st_1_anonymous_direct_requests_are_rejected` |
| NFR-5-ST-1 / SEC-DAT-1-ST-1 | Collection responses do not disclose foreign resources | `test_nfr_5_st_1_and_sec_dat_1_lists_do_not_disclose_foreign_resources` |

The full 45-test suite also covers registration/login, protected dashboard/API access, schema relationships, and frontend-to-backend route availability. The run completed with **45 passed, 0 failed**.

## Scope and verification limits

US-07 ownership is enforced on the implemented dataset, model, and evaluation list/detail reads. Automated isolation tests seed records for two users and exercise both collection and direct-ID access. The tests do not claim to verify file upload or model-training workflows: those write flows belong to later stories (US-08 and US-18/US-19) and are still unimplemented. When those stories are implemented, they must derive `user_id` from the authenticated server-side session and use the owner-scoped lookup helpers before reading or changing resources. A deployment-level check of HTTPS, secure cookie behavior behind the deployment proxy, backup restoration, and performance under load was not performed in this local run.
