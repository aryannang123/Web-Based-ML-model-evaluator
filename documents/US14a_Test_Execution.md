# US-14a Role-Based Access Control and Admin Management Test Execution Record

**Project:** Web-Based ML Model Evaluator  
**Execution date:** 2026-10-28  
**Scope:** US-14a Foundational Role-Based Access Control (Student, Instructor, Admin roles), Admin User Management (UC-09 / FR-7.1), Admin Dataset Oversight (UC-13 / FR-7.2), Admin Activity Logs (UC-14 / FR-7.3), and Server-Side Authorization (FR-7.5 / NFR-4).

---

## 1. Result summary

| Verification | Result | Evidence |
| --- | --- | --- |
| **US-14a Dedicated Test Suite** | **PASS** | 11 tests passed in `test_us14a_rbac_admin.py` executed with `python -m unittest discover -s tests -p 'test_us14a_rbac_admin.py' -v` from `backend/`. |
| **Frontend/Backend Contract Integration** | **PASS** | 8 tests passed in `test_frontend_backend_integration.py` verifying API endpoints, static assets, and admin panel elements. |
| **Full Backend Regression Suite** | **PASS** | 88 tests passed in `python -m unittest discover -s tests -q` from `backend/`. Zero regressions across authentication, dataset upload, data isolation, and statistics. |
| **Frontend JavaScript Syntax** | **PASS** | `node --check frontend/js/app.js` executed without errors. |
| **Git Diff Whitespace Check** | **PASS** | `git diff --check` executed with zero whitespace warnings. |

---

## 2. Test Plan Section 13 Traceability (FR-7.1, FR-7.2, FR-7.3, FR-7.5)

| Test Case ID | Linked SRS / SEC IDs | Description & Coverage | Automated Test Name | Result |
| --- | --- | --- | --- | --- |
| **FR-7.1-ST-1** | FR-7.1; SEC-AZ-3 | Admin can view the registered users list populated with accounts across all roles. | `test_fr7_1_st_1_admin_can_view_registered_users_list` | **PASS** |
| **FR-7.1-ST-2** | FR-7.1; SEC-AZ-3 | Admin can perform supported account management actions (inspect details and toggle `is_active` status to deactivate/reactivate accounts). Deactivated accounts are blocked from logging in. | `test_fr7_1_st_2_admin_can_perform_supported_account_management_action` | **PASS** |
| **FR-7.1-ST-3** | FR-7.1; SEC-AZ-3 | Non-Admin accounts (Students and Instructors) calling user management endpoints directly via API or UI are denied with `HTTP 403 Forbidden`. | `test_fr7_1_st_3_non_admin_cannot_access_or_call_user_management` | **PASS** |
| **FR-7.2-ST-1** | FR-7.2; SEC-AZ-4 | Admin can view stored dataset records and metadata across all user accounts in the platform. | `test_fr7_2_st_1_admin_can_view_stored_dataset_records_and_metadata` | **PASS** |
| **FR-7.2-ST-2** | FR-7.2; SEC-AZ-4 | Dataset oversight preserves ownership associations (`user_id` mapped to original account) and supports administrative cleanup. | `test_fr7_2_st_2_dataset_management_preserves_ownership_associations` | **PASS** |
| **FR-7.2-ST-3** | FR-7.2; SEC-AZ-4 | Non-Admin accounts (Students and Instructors) calling administrative dataset management endpoints are rejected with `HTTP 403 Forbidden`. | `test_fr7_2_st_3_non_admin_cannot_access_administrative_dataset_management` | **PASS** |
| **FR-7.3-ST-1** | FR-7.3; SEC-AUD-1 | Admin can view application activity and audit logs recorded across system operations. | `test_fr7_3_st_1_admin_can_view_application_activity_logs` | **PASS** |
| **FR-7.3-ST-2** | FR-7.3; SEC-AUD-1 | Activity logs are strictly read-only (mutations on `/logs` return 405 Method Not Allowed) and mask credentials, passwords, and session secrets. | `test_fr7_3_st_2_activity_logs_are_read_only_and_mask_secrets` | **PASS** |
| **FR-7.3-ST-3** | FR-7.3; SEC-AZ-6 | Non-Admin and Instructor accounts cannot access the system activity log endpoint or interface (`HTTP 403 Forbidden`). | `test_fr7_3_st_3_non_admin_cannot_access_system_log_interface` | **PASS** |
| **FR-7.5-ST-1** | FR-7.5; NFR-4 | Server-side role-based access control is enforced on all endpoints regardless of client request headers or UI state. | `test_fr7_5_st_1_cross_role_access_control_enforced_server_side` | **PASS** |
| **FR-7.5-IT-1** | FR-7.5; FR-1.1 | Newly registered users are assigned the Student role by default; client tampering attempting to register with elevated roles (`admin`, `instructor`) is overridden. | `test_fr7_5_it_1_newly_registered_users_assigned_student_role_by_default` | **PASS** |

---

## 3. GitHub Acceptance Criteria Traceability

| Acceptance Criterion | Result | Implementation Evidence |
| --- | --- | --- |
| **Role column in `users` table** | PASS | `User.role` added with default `'student'`, backed by SQLite automatic column migration. |
| **Registration hardening** | PASS | `/api/auth/register` forces `role="student"` and `is_active=True`, preventing client-side privilege escalation. |
| **RBAC authorization decorator** | PASS | `@role_required(*allowed_roles)` and `@admin_required` decorators implemented in `auth_utils.py` enforcing 403 status codes. |
| **Admin User Management (UC-09 / FR-7.1)** | PASS | `GET /api/admin/users`, `GET /api/admin/users/<id>`, and `PATCH /api/admin/users/<id>` implemented and wired to the UI. |
| **Admin Dataset Oversight (UC-13 / FR-7.2)** | PASS | `GET /api/admin/datasets`, `GET /api/admin/datasets/<id>`, and `DELETE /api/admin/datasets/<id>` implemented with user association preserved. |
| **System Activity Logs (UC-14 / FR-7.3)** | PASS | `ActivityLog` model and `GET /api/admin/logs` endpoint implemented with credential masking and read-only constraints. |
| **Frontend Administrative Control Center** | PASS | Admin modal with User Accounts, Dataset Oversight, and Activity Logs tabs added to `index.html` and rendered dynamically in `app.js`. |

---

## 4. Verification Limits

All 88 unit, integration, and security test cases passed locally in the test environment (`python -m unittest discover -s tests`). Browser UI integration was verified through contract tests and syntax linting; formal automated end-to-end browser execution (Selenium/Cypress) in a headless multi-browser matrix was not run as part of this sprint ticket.
