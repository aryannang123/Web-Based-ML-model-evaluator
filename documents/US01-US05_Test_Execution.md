# US-01 to US-05 Test Execution Record

**Execution date:** 2026-10-22

**Environment:** Windows, Python 3.13, Flask test client, SQLite in-memory database

**Command:** `python -m unittest discover -s tests -v` from `backend/`

**Result:** 30 tests passed. The focused US-01 to US-05 acceptance module contains 12 passing tests.

The entries below give the Actual Result and Test Result values for the related rows in the repository Test Plan. These are automated results from the local test environment; they do not claim that manual browser compatibility or deployment checks have been completed.

| Test Plan ID | Actual Result to record | Test Result |
| --- | --- | --- |
| FR-1.1-UT-1 | Registration returned HTTP 201, confirmed success, and saved the new user. | Pass |
| FR-1.1-UT-2 | Missing fields, invalid email, and passwords below 8 or above 128 characters returned HTTP 400; valid 8- and 128-character passwords were accepted. No invalid account was saved. | Pass |
| FR-1.2-UT-1 | Valid credentials returned HTTP 200, created an authenticated session, and returned dashboard redirect `/`. | Pass |
| FR-1.2-UT-2 | Wrong password and unknown username both returned HTTP 401 with the same generic error response. | Pass |
| FR-1.4-ST-1 | Anonymous requests to `/` and `/index.html` redirected to `/login`; a protected API request returned HTTP 401 without protected data. | Pass |
| SEC-AUTH-1-ST-1 | Anonymous access to the protected dashboard and API was denied. | Pass |
| SEC-AUTH-2-ST-1 | Registration stored a Werkzeug password hash; the stored value differed from and verified against the submitted password. | Pass |
| SEC-AUTH-3-ST-1 | Unknown-user and wrong-password attempts returned identical status and error content. | Pass |
| SEC-AZ-1-ST-1 | A direct unauthenticated API request was rejected with HTTP 401. | Pass |

Additional acceptance checks for the five GitHub user stories:

| Story | Actual Result | Result |
| --- | --- | --- |
| US-01 | Required frontend, backend, database, ML, model, route, README, requirements, and ignore paths exist. | Pass |
| US-02 | Required user, dataset, model, and evaluation tables, foreign keys, ORM relationships, and schema document are present; SQLite creates the schema successfully. | Pass |
| US-03 | Health endpoint returns JSON HTTP 200; login page, JavaScript, and stylesheet are served successfully from their configured routes. | Pass |
| US-04 | Valid registration, input validation, duplicate username/email rejection, 8–128 character password bounds, and hashed password storage pass automated checks. | Pass |
| US-05 | Valid login creates a session and reaches the protected dashboard; invalid credentials are rejected and anonymous access is blocked. | Pass |

**Not recorded as passed:** the Test Plan's manual browser matrix, browser usability, deployment HTTPS/TLS, and performance checks require a running browser or deployment environment and separate evidence.
