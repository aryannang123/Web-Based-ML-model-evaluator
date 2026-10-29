Test Plan Document
Web-Based ML Model Evaluator

1. Purpose and Scope
This test plan defines the verification approach for the Web-Based ML Model Evaluator. It maps test cases directly to the FR
and NFR identifiers in the companion SRS. The plan covers account access, dataset management, preparation, model
training, evaluation, comparison, exports, run history, API behaviour, security, usability, and reliability.
Test execution has not been represented as completed in this document. The Actual Result and Test Result columns are
intentionally left blank for the team to fill in during execution.

2. Test Objectives
• Verify each functional requirement through positive, negative, integration, or end-to-end tests.
• Verify important quality requirements, especially authorization, user data isolation, data integrity, and error handling.
• Confirm that invalid data and configuration are rejected safely and consistently.
• Maintain traceability from SRS requirement IDs to test case IDs and outcomes.

3. Test Scope

3.1 In Scope
• Registration, login, logout, and protected-resource access.
• CSV upload, validation, preview, statistics, metadata, and dataset replacement.
• Preprocessing, target selection, train-test split, algorithm selection, and training.
• Metrics, evaluation visualizations, model comparison, downloads, and run history.
• API response behaviour, user isolation, reproducibility metadata, browser UI, and failure handling.
• Role-based access control: Admin user management, Admin dataset management, Admin log access, and Instructor read-only evaluation access.

3.2 Out of Scope
• Testing algorithms or ML libraries independently of their integration with this application.
• Production-scale penetration testing or formal certification.
• Formats, algorithms, or export types not implemented in the delivered version.

4. Test Approach

Test type                     | Purpose
------------------------------|--------------------------------------------------------------
Unit Testing (UT)             | Test individual validation functions, service methods, metrics calculations, and configuration checks.
Integration Testing (IT)      | Test interactions among UI/API, backend, database, file storage, and ML components.
System Testing (ST)           | Test complete user workflows and cross-cutting requirements from the user's perspective.
Non-functional Testing (NFT)  | Test performance, security, compatibility, reliability, and usability where applicable.

5. Test Case ID Convention
Test Case ID format: <Requirement-ID>-<Test-Type>-<Sequence>, for example FR-2.1-UT-1 or NFR-4-ST-1.
• Requirement-ID: exact FR or NFR identifier defined in the SRS.
• Test-Type: UT = Unit Test, IT = Integration Test, ST = System Test, NFT = Non-Functional Test.
• Sequence: running number for the selected requirement and test type.

6. Test Environment and Test Data
• Run the application in the project's configured development/test environment with backend, database, storage, and ML dependencies available.
• Use dedicated test accounts (User A and User B) to verify user isolation.
• Create dedicated role-specific test accounts: one Admin account and one Instructor account for role-based access control testing.
• Prepare valid CSV data, an empty CSV, a malformed CSV, a file with missing values, a dataset with numeric and categorical columns, and a dataset with a usable target column.
• Use small deterministic datasets for metric and reproducibility checks; use a larger within-limit dataset for performance tests.
• Do not use real personal or confidential data in test fixtures.

7. Test Execution Summary
The summary below is a planned test inventory, not a claim that tests have already passed.

Requirement ID | Test cases planned | Coverage area
---------------|-------------------|------------------------------------------------------
FR-1.1         | 2                 | Register with valid required account fields
FR-1.2         | 2                 | Authenticate with valid credentials
FR-1.3         | 1                 | Logout terminates the active session
FR-1.4         | 2                 | Unauthenticated user cannot access protected pages or APIs
FR-2.1         | 2                 | Upload a valid CSV dataset
FR-2.2         | 2                 | Reject an empty or malformed CSV
FR-2.3         | 1                 | Preview displays correct headers and sample rows
FR-2.4         | 1                 | Dataset statistics match a known dataset
FR-2.5         | 2                 | Replacing a dataset updates the current user's selected dataset
FR-3.1         | 2                 | Apply a supported preprocessing option to valid data
FR-3.2         | 2                 | Select a valid target column
FR-3.3         | 2                 | Accept a valid train-test split
FR-4.1         | 2                 | Display supported algorithms and accept a compatible selection
FR-4.2         | 2                 | Complete training for a valid configuration
FR-4.3         | 3                 | Calculate applicable metrics for classification
FR-4.4         | 2                 | Compare two completed runs
FR-5.4         | 2                 | Download a supported model artifact or report
FR-6.1         | 2                 | Show a user's prior runs and configuration
FR-6.2         | 2                 | API returns a successful structured response for a valid request
FR-6.3         | 1                 | Show actionable errors for a failed operation
FR-7.1         | 3                 | Admin can view and manage user accounts; non-Admin is denied
FR-7.2         | 3                 | Admin can view and manage dataset records; non-Admin is denied
FR-7.3         | 3                 | Admin can view activity logs; non-Admin and Instructor are denied
FR-7.4         | 3                 | Instructor can view authorized evaluation results in read-only mode
FR-7.5         | 2                 | Role-based access control is enforced server-side for all roles
NFR-1          | 1                 | Measure response time for common preview/list actions
NFR-2          | 1                 | Show progress/status for a long-running training job
NFR-3          | 1                 | Verify passwords are not stored in plaintext
NFR-4          | 1                 | Enforce authorization on direct backend requests
NFR-5          | 1                 | Verify isolation across datasets, runs, and artifacts
NFR-6          | 1                 | Preserve completed results after a later operation fails
NFR-7          | 1                 | Retain run configuration needed to explain a result
NFR-8          | 1                 | Verify the primary workflow is understandable in the desktop UI
NFR-9          | 1                 | Check core workflows in supported browsers
NFR-10         | 1                 | Verify separation of major application components
NFR-11         | 1                 | Verify upload/resource limits are enforced
NFR-12         | 1                 | Verify run metadata and artifacts map to the correct run
NFR-13         | 1                 | Ensure errors do not reveal sensitive internals
NFR-14         | 1                 | Deploy from documented setup instructions
TOTAL          | 61                | Planned test cases; execute and record actual outcomes

8. Detailed Test Cases
For each case, record Actual Result and Test Result after execution. Use Pass, Fail, Blocked, or Not Run as appropriate.

FR-1.1
Test Case ID  | Module          | Test Case Description                          | Pre-conditions              | Test Steps                                              | Test Data                                   | Expected Results                                                       | Actual Result | Test Result
--------------|-----------------|------------------------------------------------|-----------------------------|---------------------------------------------------------|---------------------------------------------|------------------------------------------------------------------------|---------------|------------
FR-1.1-UT-1   | 3.1 User Access | Register with valid required fields            | Registration page is available. | 1. Open registration. 2. Enter valid unique credentials. 3. Submit. | Valid unique username/email; valid password | Account is created and success feedback is shown.                      |               |
FR-1.1-UT-2   | 3.1 User Access | Reject registration with missing or invalid fields | Registration page is available. | 1. Leave a required field blank or enter invalid data. 2. Submit. | Blank required field / invalid email / out-of-bounds password | Validation is shown, no account is created.                            |               |

FR-1.2
Test Case ID  | Module          | Test Case Description             | Pre-conditions                     | Test Steps                                   | Test Data                     | Expected Results                                          | Actual Result | Test Result
--------------|-----------------|-----------------------------------|------------------------------------|----------------------------------------------|-------------------------------|-----------------------------------------------------------|---------------|------------
FR-1.2-UT-1   | 3.1 User Access | Authenticate with valid credentials | Registered test account exists.   | 1. Open login. 2. Enter valid credentials. 3. Submit. | Valid username and password | User is authenticated and redirected to the application.  |               |
FR-1.2-UT-2   | 3.1 User Access | Reject invalid credentials        | Registered test account exists.   | 1. Enter incorrect password. 2. Submit.      | Wrong password                | Login is rejected without exposing account details.       |               |

FR-1.3
Test Case ID  | Module          | Test Case Description                       | Pre-conditions        | Test Steps                                        | Test Data                 | Expected Results                                      | Actual Result | Test Result
--------------|-----------------|---------------------------------------------|-----------------------|---------------------------------------------------|---------------------------|-------------------------------------------------------|---------------|------------
FR-1.3-IT-1   | 3.1 User Access | Logout terminates the active session        | User is logged in.    | 1. Select Logout. 2. Navigate back to a protected page. | Authenticated test account | Session ends and protected content is not accessible. |               |

FR-1.4
Test Case ID  | Module          | Test Case Description                                   | Pre-conditions                              | Test Steps                                                         | Test Data          | Expected Results                                                       | Actual Result | Test Result
--------------|-----------------|---------------------------------------------------------|---------------------------------------------|--------------------------------------------------------------------|--------------------|------------------------------------------------------------------------|---------------|------------
FR-1.4-ST-1   | 3.1 User Access | Unauthenticated user cannot access protected pages or APIs | User is logged out.                      | 1. Open a protected URL or call a protected endpoint directly.     | No session/token   | Access is denied or redirected to login; no protected data is returned.|               |
FR-1.4-ST-2   | 3.1 User Access | Authenticated user cannot access another user's resources | User A and User B exist; User B owns a dataset/run. | 1. Log in as User A. 2. Request User B's resource identifier. | User B dataset/run ID | The request is denied and no resource details or artifacts are disclosed. |            |

FR-2.1
Test Case ID    | Module                 | Test Case Description                   | Pre-conditions         | Test Steps                                               | Test Data                            | Expected Results                                                         | Actual Result | Test Result
----------------|------------------------|-----------------------------------------|------------------------|----------------------------------------------------------|--------------------------------------|--------------------------------------------------------------------------|---------------|------------
FR-2.1-UT-1     | 3.2 Dataset Management | Upload a valid CSV dataset              | User is authenticated. | 1. Open dataset upload. 2. Select valid CSV. 3. Submit.  | CSV with headers and data rows        | Upload succeeds and the dataset is associated with the authenticated user.|               |
FR-2.1-UT-2     | 3.2 Dataset Management | Reject an unsupported file type         | User is authenticated. | 1. Select a non-CSV file. 2. Submit.                     | PDF or executable extension           | Upload is rejected with a clear error message.                            |               |

FR-2.2
Test Case ID    | Module                 | Test Case Description                                     | Pre-conditions              | Test Steps                                                   | Test Data                         | Expected Results                                              | Actual Result | Test Result
----------------|------------------------|-----------------------------------------------------------|-----------------------------|--------------------------------------------------------------|-----------------------------------|---------------------------------------------------------------|---------------|------------
FR-2.2-UT-1     | 3.2 Dataset Management | Reject malformed or empty CSV                             | Upload page is available.   | 1. Upload an empty or malformed CSV. 2. Submit.              | Empty file / malformed data        | Validation fails and unacceptable data is not stored.         |               |
FR-2.2-IT-2     | 3.2 Dataset Management | Validate required tabular structure and report issues     | User is authenticated.      | 1. Upload a CSV with inconsistent column counts or no data rows. 2. Review response. | Misformed headers or missing rows | System reports the issue and does not proceed with the dataset.|               |

FR-2.3
Test Case ID    | Module                 | Test Case Description                         | Pre-conditions                         | Test Steps                                | Test Data                            | Expected Results                                                              | Actual Result | Test Result
----------------|------------------------|-----------------------------------------------|----------------------------------------|-------------------------------------------|--------------------------------------|-------------------------------------------------------------------------------|---------------|------------
FR-2.3-ST-1     | 3.2 Dataset Management | Preview displays correct headers and sample rows | A valid dataset is uploaded.          | 1. Open dataset preview. 2. Compare displayed values. | CSV with known headers and sample values | Preview shows the correct column names and rows without order or column shifts. |             |

FR-2.4
Test Case ID    | Module                 | Test Case Description                    | Pre-conditions                                        | Test Steps                               | Test Data                                       | Expected Results                                                  | Actual Result | Test Result
----------------|------------------------|------------------------------------------|-------------------------------------------------------|------------------------------------------|-------------------------------------------------|-------------------------------------------------------------------|---------------|------------
FR-2.4-UT-1     | 3.2 Dataset Management | Dataset statistics match a known dataset | A valid dataset with known dimensions is uploaded.    | 1. Open dataset statistics. 2. Compare stats. | 10 rows, 3 columns, known missing values and type info | Displayed dimensions and available information match the fixture. |               |

FR-2.5
Test Case ID    | Module                 | Test Case Description                                      | Pre-conditions                             | Test Steps                                                    | Test Data                              | Expected Results                                                     | Actual Result | Test Result
----------------|------------------------|------------------------------------------------------------|--------------------------------------------|-----------------------------------------------------------------|----------------------------------------|----------------------------------------------------------------------|---------------|------------
FR-2.5-IT-1     | 3.2 Dataset Management | Replacing a dataset updates the current user's selected dataset | User has already uploaded Dataset A.     | 1. Upload Dataset B. 2. Open metadata and review.              | Dataset A: 5 rows; Dataset B: 8 rows    | Current dataset reflects Dataset B; Dataset A's data is not shown.   |               |
FR-2.5-ST-2     | 3.2 Dataset Management | Dataset metadata is isolated by owner                       | User A and User B each have a dataset.    | 1. Sign in as each user. 2. Open dataset listing/history.      | Different dataset names per user        | Each user sees only their own datasets and never the other's.        |               |

FR-3.1
Test Case ID    | Module               | Test Case Description                                      | Pre-conditions                                 | Test Steps                                          | Test Data                                    | Expected Results                                                          | Actual Result | Test Result
----------------|----------------------|------------------------------------------------------------|------------------------------------------------|-----------------------------------------------------|----------------------------------------------|---------------------------------------------------------------------------|---------------|------------
FR-3.1-UT-1     | 3.3 Data Preparation | Apply a supported preprocessing option to valid data       | A dataset with missing values or categorical data is uploaded. | 1. Select a supported preprocessing option. 2. Apply it. | Dataset with known missing/categorical values | Preprocessing completes and output conforms to the selected option.       |               |
FR-3.1-UT-2     | 3.3 Data Preparation | Reject incompatible preprocessing configuration            | A dataset is uploaded.                         | 1. Select an incompatible option. 2. Submit.        | Invalid option/parameter combination          | Invalid configuration is rejected with a useful message.                   |               |

FR-3.2
Test Case ID    | Module               | Test Case Description                   | Pre-conditions                     | Test Steps                                                   | Test Data              | Expected Results                                                    | Actual Result | Test Result
----------------|----------------------|-----------------------------------------|------------------------------------|--------------------------------------------------------------|------------------------|---------------------------------------------------------------------|---------------|------------
FR-3.2-UT-1     | 3.3 Data Preparation | Select a valid target column            | Dataset has multiple columns.      | 1. Open target selector. 2. Select an existing column name.  | Target column: outcome | Selection is saved and used to configure the model.                 |               |
FR-3.2-UT-2     | 3.3 Data Preparation | Reject a missing or invalid target selection | Dataset is uploaded.           | 1. Leave target unset or provide a nonexistent column name. 2. Confirm. | No column / nonexistent | Training cannot start and the user is told to select a valid target. |               |

FR-3.3
Test Case ID    | Module               | Test Case Description                   | Pre-conditions                           | Test Steps                                           | Test Data                  | Expected Results                                                                 | Actual Result | Test Result
----------------|----------------------|-----------------------------------------|------------------------------------------|------------------------------------------------------|----------------------------|----------------------------------------------------------------------------------|---------------|------------
FR-3.3-UT-1     | 3.3 Data Preparation | Accept a valid train-test split         | Dataset and target are selected.         | 1. Choose supported proportions. 2. Save or confirm. | 80% train / 20% test        | Configuration is accepted and partitions are created with proportional row counts.|               |
FR-3.3-UT-2     | 3.3 Data Preparation | Reject invalid train-test split         | Dataset and target are selected.         | 1. Enter invalid proportions or values. 2. Submit.   | Negative, >100%, or empty value | Configuration is rejected with a clear validation message.                    |               |

FR-4.1
Test Case ID    | Module                  | Test Case Description                                     | Pre-conditions                          | Test Steps                                                | Test Data                                         | Expected Results                                                              | Actual Result | Test Result
----------------|-------------------------|-----------------------------------------------------------|-----------------------------------------|-----------------------------------------------------------|---------------------------------------------------|-------------------------------------------------------------------------------|---------------|------------
FR-4.1-UT-1     | 3.4 Model Configuration | Display supported algorithms and accept a compatible selection | Dataset and task configuration are available. | 1. Open algorithm selection. 2. Select a compatible algorithm. | One supported classification or regression algorithm | Selected algorithm is stored in the run configuration.                    |               |
FR-4.1-IT-2     | 3.4 Model Configuration | Prevent incompatible algorithm/task configuration          | Dataset/task type is known.             | 1. Attempt to select or configure an incompatible algorithm. | Algorithm mismatched with task type              | System prevents incompatible execution or returns a clear error.               |               |

FR-4.2
Test Case ID    | Module            | Test Case Description                                 | Pre-conditions                                     | Test Steps                                            | Test Data                                  | Expected Results                                              | Actual Result | Test Result
----------------|-------------------|-------------------------------------------------------|----------------------------------------------------|-------------------------------------------------------|--------------------------------------------|---------------------------------------------------------------|---------------|------------
FR-4.2-IT-1     | 3.4 Model Training| Complete training for a valid configuration           | Valid dataset, target, split, and algorithm are configured. | 1. Start training. 2. Wait for completion.  | Small deterministic dataset; supported algorithm | Training completes and results are stored for the user.   |               |
FR-4.2-IT-2     | 3.4 Model Training| Handle training failure without corrupting prior runs  | A previous completed run exists.                   | 1. Start a run with invalid or deliberately failing configuration. 2. Review status and prior run history. | Invalid configuration or controlled failure | Failure is reported; previous completed run history remains intact. |              |

FR-4.3
Test Case ID    | Module        | Test Case Description                                     | Pre-conditions                                      | Test Steps                                                   | Test Data                                          | Expected Results                                                    | Actual Result | Test Result
----------------|---------------|-----------------------------------------------------------|-----------------------------------------------------|--------------------------------------------------------------|----------------------------------------------------|---------------------------------------------------------------------|---------------|------------
FR-4.3-UT-1     | 3.5 Evaluation| Calculate applicable classification metrics               | A classification model has predictions and labels.  | 1. Evaluate the run. 2. Compare metrics with known labels.   | Known labels and expected classification metrics   | Applicable classification metrics match the expected calculation.   |               |
FR-4.3-UT-2     | 3.5 Evaluation| Calculate applicable regression metrics                   | A regression model has predictions and labels.      | 1. Evaluate the run. 2. Compare metrics with known numeric labels. | Known labels and expected regression metrics | Applicable regression metrics match expected values within tolerance. |             |
FR-4.3-ST-3     | 3.5 Evaluation| Display evaluation visualizations where applicable        | A completed run exists.                             | 1. Open results. 2. Inspect charts/plots.                    | Classification run or regression run               | Relevant visualizations are shown and correspond to the selected run.|               |

FR-4.4
Test Case ID    | Module         | Test Case Description                                    | Pre-conditions                                        | Test Steps                                       | Test Data                                             | Expected Results                                                                      | Actual Result | Test Result
----------------|----------------|----------------------------------------------------------|-------------------------------------------------------|--------------------------------------------------|-------------------------------------------------------|---------------------------------------------------------------------------------------|---------------|------------
FR-4.4-IT-1     | 3.5 Comparison | Compare two completed runs                               | At least two completed runs with compatible task/metric types exist. | 1. Select two runs. 2. Compare. | Two compatible runs                                 | Comparison shows run identities/configurations and compares metrics side by side.     |               |
FR-4.4-UT-2     | 3.5 Comparison | Prevent misleading comparison of incompatible metrics     | Runs of incompatible task types exist.                | 1. Select one classification and one regression run for comparison. | One classification, one regression | System separates incompatible metrics or explains why direct comparison is unavailable. |            |

FR-5.4
Test Case ID    | Module      | Test Case Description                                     | Pre-conditions                        | Test Steps                                                        | Test Data               | Expected Results                                                   | Actual Result | Test Result
----------------|-------------|-----------------------------------------------------------|---------------------------------------|-------------------------------------------------------------------|-------------------------|--------------------------------------------------------------------|---------------|------------
FR-5.4-IT-1     | 3.5 Export  | Download a supported model artifact or report             | A completed run with a downloadable artifact/report exists. | 1. Select download. 2. Open the downloaded file. | Completed run ID        | Download succeeds; file is readable and corresponds to the run.    |               |
FR-5.4-UT-2     | 3.5 Export  | Handle unavailable artifact                               | A run has no artifact of the requested type. | 1. Request the download.                             | Missing artifact type   | A clear error is shown and no file is returned.                    |               |

FR-6.1
Test Case ID    | Module          | Test Case Description                          | Pre-conditions                             | Test Steps                                                    | Test Data                          | Expected Results                                                           | Actual Result | Test Result
----------------|-----------------|------------------------------------------------|--------------------------------------------|---------------------------------------------------------------|------------------------------------|----------------------------------------------------------------------------|---------------|------------
FR-6.1-IT-1     | 3.6 Run History | Show a user's prior runs and configuration     | A user has at least one completed run.     | 1. Open run history. 2. Select a prior run.                   | Run with known algorithm, split, and status | History shows the run's algorithm, split, and status/results correctly.  |               |
FR-6.1-ST-2     | 3.6 Run History | Keep a user's prior run history private        | Two users have separate completed runs.    | 1. Sign in as User A. 2. Inspect history and request User B's run. | User B run ID                  | User A cannot see or retrieve User B's run.                                |               |

FR-6.2
Test Case ID    | Module  | Test Case Description                                   | Pre-conditions           | Test Steps                                                          | Test Data                   | Expected Results                                                    | Actual Result | Test Result
----------------|---------|---------------------------------------------------------|--------------------------|---------------------------------------------------------------------|-----------------------------|---------------------------------------------------------------------|---------------|------------
FR-6.2-IT-1     | 3.6 API | API returns a successful structured response for a valid request | Backend service is running. | 1. Call a documented endpoint with valid input. 2. Inspect response. | Valid request payload      | Expected success status and structured response are returned.       |               |
FR-6.2-IT-2     | 3.6 API | API returns an error for an invalid or incomplete request | Backend service is running. | 1. Call a documented endpoint with invalid or incomplete input.    | Malformed/missing field     | A suitable error status and structured error response are returned. |               |

FR-6.3
Test Case ID    | Module           | Test Case Description                                      | Pre-conditions           | Test Steps                                                      | Test Data                          | Expected Results                                                                         | Actual Result | Test Result
----------------|------------------|------------------------------------------------------------|--------------------------|-----------------------------------------------------------------|------------------------------------|------------------------------------------------------------------------------------------|---------------|------------
FR-6.3-ST-1     | 3.6 Error Handling | Show actionable errors for a failed operation            | Application is available.| 1. Trigger an invalid upload or run. 2. Review UI feedback.     | Malformed CSV or invalid config     | Message explains the problem without exposing internal details or stack traces.           |               |

NFR-1
Test Case ID    | Module            | Test Case Description                               | Pre-conditions                               | Test Steps                                                              | Test Data                           | Expected Results                                                           | Actual Result | Test Result
----------------|-------------------|-----------------------------------------------------|----------------------------------------------|-------------------------------------------------------------------------|-------------------------------------|----------------------------------------------------------------------------|---------------|------------
NFR-1-NFT-1     | 4. Non-Functional | Measure response time for common preview/list actions | Test environment and representative data are ready. | 1. Run the same preview/list request repeatedly under normal load. 2. Record response times. | Documented dataset size             | Response-time measurements are recorded and compared to the project target. |               |

NFR-2
Test Case ID    | Module            | Test Case Description                                 | Pre-conditions                                      | Test Steps                                               | Test Data                    | Expected Results                                                                 | Actual Result | Test Result
----------------|-------------------|-------------------------------------------------------|-----------------------------------------------------|----------------------------------------------------------|------------------------------|----------------------------------------------------------------------------------|---------------|------------
NFR-2-NFT-1     | 4. Non-Functional | Show progress/status for a long-running training job  | A configuration is available that takes longer than a normal request. | 1. Start training. 2. Observe UI while it runs. | Long-running but valid configuration | The user receives running/progress/status feedback while the job runs.          |               |

NFR-3
Test Case ID    | Module            | Test Case Description                            | Pre-conditions                          | Test Steps                                                           | Test Data              | Expected Results                                                    | Actual Result | Test Result
----------------|-------------------|--------------------------------------------------|-----------------------------------------|----------------------------------------------------------------------|------------------------|---------------------------------------------------------------------|---------------|------------
NFR-3-ST-1      | 4. Non-Functional | Verify passwords are not stored in plaintext     | A test account can be accessed and the datastore is inspectable. | 1. Register a test account. 2. Inspect the stored representation in the test database. | Test account password | Stored value is a secure hash, not the submitted plaintext.         |               |

NFR-4
Test Case ID    | Module            | Test Case Description                                           | Pre-conditions                      | Test Steps                                                                  | Test Data              | Expected Results                                              | Actual Result | Test Result
----------------|-------------------|-----------------------------------------------------------------|-------------------------------------|-----------------------------------------------------------------------------|------------------------|---------------------------------------------------------------|---------------|------------
NFR-4-ST-1      | 4. Non-Functional | Enforce authorization on direct backend requests regardless of UI | User A and User B each have resources. | 1. Authenticate as User B. 2. Call the backend directly for User A's resource. | User B identifier      | Backend denies access; resource is not returned.              |               |

NFR-5
Test Case ID    | Module            | Test Case Description                                    | Pre-conditions                                | Test Steps                                                | Test Data                      | Expected Results                                         | Actual Result | Test Result
----------------|-------------------|----------------------------------------------------------|-----------------------------------------------|-----------------------------------------------------------|--------------------------------|----------------------------------------------------------|---------------|------------
NFR-5-ST-1      | 4. Non-Functional | Verify isolation across datasets, runs, and artifacts    | Two users have completed uploads and runs.    | 1. Sign in as each user. 2. Check dataset and run lists and direct source IDs. | Distinct user-owned resources | No cross-user resources are visible or accessible.       |               |

NFR-6
Test Case ID    | Module            | Test Case Description                                      | Pre-conditions                  | Test Steps                                                                        | Test Data              | Expected Results                                                              | Actual Result | Test Result
----------------|-------------------|------------------------------------------------------------|----------------------------------|-----------------------------------------------------------------------------------|------------------------|-------------------------------------------------------------------------------|---------------|------------
NFR-6-IT-1      | 4. Non-Functional | Preserve completed results after a later operation fails   | A completed run exists.          | 1. Record prior result details. 2. Trigger a separate failing training/export operation. 3. Reopen prior run. | Known completed run | Prior result and metadata remain unchanged and accessible.                    |               |

NFR-7
Test Case ID    | Module            | Test Case Description                              | Pre-conditions              | Test Steps                                                                    | Test Data              | Expected Results                                                          | Actual Result | Test Result
----------------|-------------------|----------------------------------------------------|------------------------------|-------------------------------------------------------------------------------|------------------------|---------------------------------------------------------------------------|---------------|------------
NFR-7-IT-1      | 4. Non-Functional | Retain run configuration needed to explain a result | A model run completes.       | 1. Open run details/history. 2. Verify algorithm, target, split, and preprocessing settings. | Known run configuration | Stored details match the settings used for the run by the implementation. |               |

NFR-8
Test Case ID    | Module            | Test Case Description                                           | Pre-conditions                    | Test Steps                                                                       | Test Data          | Expected Results                                                               | Actual Result | Test Result
----------------|-------------------|-----------------------------------------------------------------|-----------------------------------|----------------------------------------------------------------------------------|--------------------|--------------------------------------------------------------------------------|---------------|------------
NFR-8-ST-1      | 4. Non-Functional | Verify the primary workflow is understandable in the desktop UI | Application is deployed.          | 1. Ask a tester to upload data, configure, train, and view results using UI labels only. 2. Record observations. | Desktop browser | Workflow steps and validation feedback are understandable; usability is observed. |             |

NFR-9
Test Case ID    | Module            | Test Case Description                              | Pre-conditions                 | Test Steps                                                                        | Test Data                                    | Expected Results                                                                | Actual Result | Test Result
----------------|-------------------|----------------------------------------------------|--------------------------------|-----------------------------------------------------------------------------------|----------------------------------------------|---------------------------------------------------------------------------------|---------------|------------
NFR-9-NFT-1     | 4. Non-Functional | Check core workflows in supported browsers         | Browser matrix is defined for the release. | 1. Execute login, upload, train, and results workflow in each browser in the matrix. | Current agreed versions of Firefox, Edge, Chrome | Core layout and interactions work in each browser; discrepancies are recorded. |               |

NFR-10
Test Case ID    | Module            | Test Case Description                                   | Pre-conditions                              | Test Steps                                                     | Test Data                             | Expected Results                                                                          | Actual Result | Test Result
----------------|-------------------|---------------------------------------------------------|---------------------------------------------|----------------------------------------------------------------|---------------------------------------|-------------------------------------------------------------------------------------------|---------------|------------
NFR-10-IT-1     | 4. Non-Functional | Verify separation of major application components       | Source repository and test environment are available. | 1. Review module boundaries and imports. 2. Run relevant tests. | Frontend, API/service, persistence, ML components | Responsibilities are separated as documented; no single module unexpectedly depends on another. |             |

NFR-11
Test Case ID    | Module            | Test Case Description                                   | Pre-conditions            | Test Steps                                                       | Test Data                               | Expected Results                                                            | Actual Result | Test Result
----------------|-------------------|---------------------------------------------------------|---------------------------|------------------------------------------------------------------|-----------------------------------------|-----------------------------------------------------------------------------|---------------|------------
NFR-11-NFT-1    | 4. Non-Functional | Verify upload/resource limits are enforced              | Configured limits are known. | 1. Upload a file below the limit. 2. Upload a file above the limit or a dataset exceeding configured constraints. | Below-limit and above-limit file fixtures | Supported input is accepted; over-limit input is rejected or safely constrained with clear feedback. |            |

NFR-12
Test Case ID    | Module            | Test Case Description                                         | Pre-conditions                               | Test Steps                                                                       | Test Data                                     | Expected Results                                                                        | Actual Result | Test Result
----------------|-------------------|---------------------------------------------------------------|----------------------------------------------|----------------------------------------------------------------------------------|-----------------------------------------------|-----------------------------------------------------------------------------------------|---------------|------------
NFR-12-IT-1     | 4. Non-Functional | Verify run metadata and artifacts map to the correct run      | Two runs exist with distinct settings and results. | 1. Open each run. 2. Inspect metrics, configurations, and artifact references. | Run A and Run B with different algorithms or targets | Each run displays only its own configuration, metrics, and artifact references. |               |

NFR-13
Test Case ID    | Module            | Test Case Description                                    | Pre-conditions                         | Test Steps                                                    | Test Data                    | Expected Results                                                                                     | Actual Result | Test Result
----------------|-------------------|----------------------------------------------------------|----------------------------------------|---------------------------------------------------------------|------------------------------|------------------------------------------------------------------------------------------------------|---------------|------------
NFR-13-ST-1     | 4. Non-Functional | Ensure errors do not reveal sensitive internals          | A controlled backend error can be triggered in the test environment. | 1. Trigger the error. 2. Inspect UI and API response. | Invalid request or controlled error | User-facing response does not contain secrets, passwords, stack traces, or internal configuration.   |               |

NFR-14
Test Case ID    | Module            | Test Case Description                                    | Pre-conditions                | Test Steps                                                      | Test Data                                   | Expected Results                                                                         | Actual Result | Test Result
----------------|-------------------|----------------------------------------------------------|-------------------------------|-----------------------------------------------------------------|---------------------------------------------|------------------------------------------------------------------------------------------|---------------|------------
NFR-14-ST-1     | 4. Non-Functional | Deploy from documented setup instructions                | A clean test environment is available. | 1. Follow setup instructions. 2. Install declared dependencies and start the application. | Clean environment and declared dependencies | Application starts using documented steps, or missing/incorrect instructions are recorded as defects. |             |

9. Entry and Exit Criteria

9.1 Entry Criteria
• A testable build is deployed and its required services are running.
• Test accounts, fixture datasets, and required ML dependencies are available.
• Role-specific test accounts (Admin and Instructor) have been created in the test environment.
• The team has identified the supported algorithms, formats, and browser matrix for the build.

9.2 Exit Criteria
• All planned cases have an execution status recorded.
• Critical access-control, user-isolation, data-loss, and training-workflow defects are resolved or formally documented.
• All Admin and Instructor role-based access control tests have been executed and outcomes recorded.
• Failed and blocked tests include notes and reproducible steps.
• Known deviations from the SRS and unsupported behaviour are documented for the evaluator.

10. Defect Reporting
Each defect should include a concise title, affected requirement/test case ID, environment, preconditions, reproduction steps, expected result, actual result, severity, evidence
(such as screenshot/log with secrets removed), and assignee. Re-test the failed case after a fix and record the new outcome.

11. Requirement Traceability Notes
Every detailed test case uses the requirement ID from the SRS as its prefix. The inventory includes functional and non-functional checks. Some NFRs (for example maintainability
and usability) require review or observation in addition to automated tests. The exact numeric performance target, maximum upload size, supported algorithm list, and supported
browser versions must be confirmed by the project team and recorded before final acceptance. FR-7.5 (role-based access control) must be implemented before the FR-7.1, FR-7.2, FR-7.3, and FR-7.4 test cases can be executed, as they depend on a working role field in the user account model.

12. Security Test Cases and Cross-Document Traceability
These cases supplement the functional and non-functional tests above. SEC IDs refer to the companion Security Requirements Document. They are planned tests, not completed
results; fill Actual Result and Test Result only after execution.
Security test ID convention: <SEC requirement ID>-<test type>-<sequence>. Example: SEC-AZ-2-ST-1. For review-based checks, REV denotes a security configuration/code review.

SEC Requirement | Test Case ID        | Linked SRS ID(s)                                           | Description                                                                                                      | Preconditions                                    | Test Steps                                                                                                             | Test Data                          | Expected Result                                                          | Actual Result | Test Result
----------------|---------------------|------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------|--------------------------------------------------|------------------------------------------------------------------------------------------------------------------------|------------------------------------|--------------------------------------------------------------------------|---------------|------------
SEC-AUTH-1      | SEC-AUTH-1-ST-1     | FR-1.4                                                     | Anonymous access to protected data is denied.                                                                    | User is logged out.                              | 1. Request a protected dataset, run history, or download endpoint. 2. Inspect response.                                 | No session                         | Request is denied; no protected content is returned.                     |               |
SEC-AUTH-2      | SEC-AUTH-2-ST-1     | NFR-3                                                      | Passwords are stored as salted hashes, not plaintext.                                                            | Test registration is enabled; authorized test database is accessible. | 1. Register a test user. 2. Inspect the stored password representation.                                   | Known test password                | Stored value is a salted password hash and does not equal the plaintext. |               |
SEC-AUTH-3      | SEC-AUTH-3-ST-1     | FR-1.2; NFR-13                                             | Login errors do not reveal account existence.                                                                    | Login endpoint is available.                    | 1. Attempt login with unknown username. 2. Attempt login with known username, wrong password. 3. Compare messages.      | Unknown user; wrong password       | Messages do not disclose whether an account exists.                      |               |
SEC-AUTH-4      | SEC-AUTH-4-NFT-1    | NFR-3; NFR-11                                              | Repeated failed requests trigger rate limiting or throttling.                                                    | Test environment and rate-limit policy are available. | 1. Submit repeated failed login or sensitive API requests. 2. Observe server response.                              | Repeated invalid credentials       | Configured throttling/lockout activates according to the documented policy. |             |
SEC-SES-1       | SEC-SES-1-ST-1      | FR-1.2; NFR-3                                              | Session handling avoids unnecessary credential exposure.                                                         | User can log in; test environment is available. | 1. Log in. 2. Inspect URLs, logs, and session tooling.                                                                  | Approved test account              | Credentials/tokens are not exposed in URLs or logs; session handling follows documented policy. |         |
SEC-SES-2       | SEC-SES-2-ST-1      | FR-1.3; NFR-3                                              | Expired session requires re-authentication.                                                                      | Session expiry policy is configured or documented. | 1. Log in. 2. Wait for or simulate expiry in the test environment. 3. Request a protected action.                     | Expired session                    | Protected action is denied until the user re-authenticates.              |               |
SEC-SES-3       | SEC-SES-3-ST-1      | FR-1.3                                                     | Logout invalidates the session.                                                                                  | User is logged in.                              | 1. Log out. 2. Replay the previous session/token against a protected endpoint.                                          | Old session/token                  | Previously valid session/token is denied access.                         |               |
SEC-AZ-1        | SEC-AZ-1-ST-1       | FR-1.4; NFR-4                                              | Backend enforces authorization independently of UI.                                                              | A protected endpoint exists.                    | 1. Call endpoint directly without authorization, with an unauthenticated or unauthorized account. 2. Repeat with authenticated but unauthorized account. | No session / unauthorized session | Backend denies the request; no protected data is returned.               |               |
SEC-AZ-2        | SEC-AZ-2-ST-1       | FR-2.5; FR-6.1; NFR-5                                      | User cannot access another user's datasets or runs.                                                              | User A and User B each own separate datasets and runs. | 1. Sign in as User A. 2. Request User B's dataset/run by identifier. 3. Try to download User B's artifact. | User B resource ID identifier      | All unauthorized access attempts are denied without leaking resource details. |            |
SEC-DAT-1       | SEC-DAT-1-ST-1      | NFR-5                                                      | Check cross-user exposure in listings, history, and direct IDs.                                                  | Two users have resources.                       | 1. Compare each user's dataset list and run history. 2. Try direct resource IDs from the other user.                    | Distinct user resources            | Only the owner's resources are visible and accessible.                   |               |
SEC-DAT-2       | SEC-DAT-2-IT-1      | FR-2.1; FR-2.2; NFR-11                                     | Reject malformed, unsupported, and over-limit uploads.                                                           | Upload endpoint and documented limits are available. | 1. Upload a valid CSV. 2. Upload a malformed CSV. 3. Upload an unsupported format. 4. Upload an over-limit file.     | Valid; malformed; non-CSV; oversized file | Valid input is accepted; malformed, non-CSV, and oversized input is rejected with clear feedback and without unsafe processing. |  |
SEC-DAT-3       | SEC-DAT-3-IT-1      | FR-4.3; FR-6.1; NFR-6; NFR-12                              | Failed run does not corrupt a completed run.                                                                     | A completed run exists.                         | 1. Record prior run details. 2. Trigger a separate failing run. 3. Reopen prior run.                                    | Completed and failing configurations | Prior run details and artifacts remain unchanged.                        |               |
SEC-DAT-4       | SEC-DAT-4-IT-1      | FR-5.4; NFR-12                                             | Downloaded artifact belongs to the selected run.                                                                 | Two runs have distinct IDs/configurations and available artifacts. | 1. Select Run A and download its artifact/report. 2. Select Run B and download. 3. Compare metadata/content. | Run A and Run B            | Each download corresponds to the authorized run and content.             |               |
SEC-INP-1       | SEC-INP-1-UT-1      | FR-2.2; FR-3.1; FR-3.2; FR-3.3; FR-4.1; FR-5.4            | Backend validates all user-controlled configuration identifiers.                                                 | Relevant API endpoints are available.           | 1. Submit invalid dataset ID, target column, split, algorithm, preprocessing option, and export values directly to the API. | Invalid configuration values     | Invalid requests are rejected; no processing or storage occurs.          |               |
SEC-INP-2       | SEC-INP-2-REV-1     | NFR-10; NFR-13                                             | Review database access for injection resistance.                                                                 | Source code and test environment are available. | 1. Review database access patterns. 2. Submit text containing SQL-like characters to controlled inputs.                 | Strings containing SQL syntax      | Queries treat user input as data; no injection occurs.                   |               |
SEC-INP-3       | SEC-INP-3-ST-1      | NFR-13                                                     | User text and errors do not expose internal details.                                                             | Text fields and error responses are controllable. | 1. Submit script-like text where accepted. 2. Trigger controlled errors. 3. Inspect UI and API response.              | Script-like input; invalid requests | Text is safely rendered and error response does not expose stack traces, secrets, or internal paths. |      |
SEC-OPS-1       | SEC-OPS-1-REV-1     | NFR-3; NFR-13; NFR-14                                      | No real credentials or secrets are committed to the repository or exposed in builds.                             | Repository and build artifacts are available.   | 1. Search tracked files and built frontend for secrets. 2. Verify test-only sentinel credentials are not in the main branch. | Known test-only sentinel values  | No real credentials or secrets are present.                              |               |
SEC-OPS-2       | SEC-OPS-2-REV-1     | NFR-10; NFR-14                                             | Dependencies are declared and a review process is available.                                                     | Dependency files are available.                 | 1. Verify dependencies are declared. 2. Inspect requirements/package files. 3. Review the dependency vulnerability-check process if configured. | Requirements documentation | Dependencies are declared and the team can review the vulnerability-scanning process. |              |
SEC-OPS-3       | SEC-OPS-3-REV-1     | NFR-6; NFR-14                                             | Recovery steps are documented for persistent data.                                                               | The application stores persistent data or artifacts. | 1. Review backup and restore instructions. 2. If configured, restore in a safe environment.                          | Backup/restore documentation        | Recovery steps are documented; any unconfigured capability is recorded as a gap. |              |
SEC-OPS-4       | SEC-OPS-4-IT-1      | FR-6.3; NFR-13                                             | Security events are logged without sensitive information.                                                        | Logging is enabled in the test environment.     | 1. Trigger failed login and denied access. 2. Inspect the log entries.                                                  | Test account; denied resource access | Relevant events are logged without passwords, tokens, or dataset contents. |              |
SEC-OPS-5       | SEC-OPS-5-NFT-1     | NFR-3; NFR-14                                             | Deployed credential/data traffic uses HTTPS/TLS.                                                                 | A deployed test environment is available.       | 1. Open the application over HTTPS. 2. Inspect connection/security configuration.                                      | Deployed URL                       | Credentials and uploaded data use HTTPS/TLS; any local-development HTTP exception is documented. |          |

12.1 Three-Document Traceability Rules
SRS FR/NFR IDs remain the primary functional and quality requirement identifiers. SEC IDs add security-specific detail. Test cases link to both where applicable. If a SEC
requirement is marked proposed in the Security Requirements Document, the team should approve it before treating a failed test as a release-blocking defect.

12.2 Security Test Status
No security test is marked Pass by default. Execute the test, record evidence where appropriate, and fill in Actual Result and Test Result. Code-review checks should record
reviewer, date, files/areas reviewed, and findings.

13. Additional Tests for Administrative and Instructor Use Cases
These cases align the test plan with UC-09 and UC-12 to UC-14 in the Use Case Flow document, and with FR-7.1 through FR-7.5 in the SRS. They are planned tests; record actual outcomes only after execution. All tests in this section require FR-7.5 (role-based access control) to be implemented before they can run.

Test Case ID  | Requirement Trace        | Description                                                                         | Preconditions                                                  | Test Steps                                                                                  | Test Data                         | Expected Result                                                                                                          | Actual Result | Test Result
--------------|--------------------------|-------------------------------------------------------------------------------------|----------------------------------------------------------------|---------------------------------------------------------------------------------------------|------------------------------------|--------------------------------------------------------------------------------------------------------------------------|---------------|------------
FR-7.1-ST-1   | FR-7.1; SEC-AZ-3         | Admin can view the registered users list.                                           | Admin account exists and is authenticated.                     | 1. Open the user-management area. 2. Review the user list.                                  | Several test accounts               | The Admin can view the registered user list populated by real accounts.                                                 |               |
FR-7.1-ST-2   | FR-7.1; SEC-AZ-3         | Admin can perform a supported account management action.                            | Admin account exists and a non-admin test account exists.      | 1. Select a test account. 2. Perform a supported management action (e.g., view or deactivate). 3. Record the action confirmation. | Dedicated test account | The action is validated, confirmed, and reflected in the account list.                                                  |               |
FR-7.1-ST-3   | FR-7.1; SEC-AZ-3         | Non-Admin cannot access or call the user-management area.                           | A Student and an Instructor test account exist.                | 1. Log in as a regular user. 2. Open the user-management URL or call the management API directly. | Regular-user session             | The request is denied for both the UI and the direct API call.                                                          |               |
FR-7.2-ST-1   | FR-7.2; SEC-AZ-4         | Admin can view stored dataset records and metadata.                                 | Admin account exists and datasets have been uploaded by test users. | 1. Open dataset management area. 2. Inspect a stored dataset record.                    | Test datasets with known metadata   | The Admin view shows accurate dataset owner, row count, column count, and the supported metadata.                       |               |
FR-7.2-ST-2   | FR-7.2; SEC-AZ-4         | Dataset management preserves ownership associations.                                | Admin account exists and datasets have been uploaded.          | 1. Inspect a dataset record. 2. Perform a supported management operation.                   | Dataset associated with a test user | The operation follows permissions and does not alter the dataset's user_id or disassociate it from its model runs.      |               |
FR-7.2-ST-3   | FR-7.2; SEC-AZ-4         | Non-Admin cannot access administrative dataset-management functions.                | A Student and an Instructor test account exist.                | 1. Log in as a regular user or Instructor. 2. Call the dataset-management API endpoint directly. | Regular-user or Instructor session | The request is denied; no administrative view of other users' dataset records is returned.                             |               |
FR-7.3-ST-1   | FR-7.3; SEC-AUD-1        | Admin can view application activity logs.                                           | Admin account exists and system activity has been recorded.    | 1. Open the system-log interface as Admin. 2. Review available log entries.                 | Log entries from uploads and training runs | Admin can view relevant log events; log entries do not expose passwords, session tokens, or raw dataset contents.  |               |
FR-7.3-ST-2   | FR-7.3; SEC-AUD-1        | Activity logs are read-only and do not expose sensitive data.                       | Admin account exists and log entries are available.            | 1. Review log entries as Admin. 2. Confirm no write or delete operations are exposed. 3. Confirm no sensitive data appears in log content. | Log entries containing security events | Logs display only non-sensitive event data; no edit or delete controls are available through the log interface.   |               |
FR-7.3-ST-3   | FR-7.3; SEC-AZ-6         | Non-Admin and Instructor cannot access the system-log interface or its endpoints.   | A Student and an Instructor test account exist.                | 1. Log in as a Student. 2. Call the log API endpoint directly. 3. Log in as an Instructor. 4. Call the log API endpoint directly. | Student session; Instructor session | Both requests are denied with an authorization error; no log data is returned.                                    |               |
FR-7.4-ST-1   | FR-7.4; SEC-AZ-5         | Instructor can view evaluation results that have been made available for review.    | Instructor account exists and evaluation results have been explicitly made available for the Instructor to view. | 1. Log in as Instructor. 2. Open the evaluation results interface. 3. Review an available result. | Instructor session; available evaluation result | Instructor can see the result details in read-only mode with no modification controls available.               |               |
FR-7.4-ST-2   | FR-7.4; SEC-AZ-5         | Instructor cannot modify, delete, or create any resource.                           | Instructor account is authenticated.                           | 1. Attempt to upload a dataset. 2. Attempt to start training. 3. Attempt to modify or delete an evaluation result. | Instructor session                | All write, delete, and upload operations are denied for the Instructor role.                                            |               |
FR-7.4-ST-3   | FR-7.4; SEC-AZ-5         | Instructor cannot access evaluation results not made available for review.          | Instructor account exists and a result not shared with the Instructor exists. | 1. Log in as Instructor. 2. Attempt to access the non-shared evaluation result by direct ID. | Instructor session; non-shared result ID | Access is denied; no result details are returned.                                                               |               |
FR-7.5-ST-1   | FR-7.5; NFR-4            | Role-based access control is enforced server-side for all three roles.              | Student, Instructor, and Admin accounts exist.                 | 1. For each role, call endpoints that belong to a higher-privileged role directly via the API. | Student trying Admin endpoint; Instructor trying Admin endpoint | All cross-role API calls are denied by the backend regardless of UI state.                                      |               |
FR-7.5-IT-1   | FR-7.5; FR-1.1           | Newly registered users are assigned the Student role by default.                   | Registration is functional.                                    | 1. Register a new user. 2. Inspect the stored role in the database or via the session endpoint. | New user with no explicit role set | The new user's role is Student; they cannot access Admin or Instructor-only endpoints.                                  |               |
