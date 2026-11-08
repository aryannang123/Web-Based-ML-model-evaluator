# GitHub Actions and Dependency Audit Evidence

**Repository:** `aryannang123/Web-Based-ML-model-evaluator`

**Pull request:** [#42 — Application validation and dependency audit](https://github.com/aryannang123/Web-Based-ML-model-evaluator/pull/42)

**Base commit:** `fd1fb2542f5f723cfc04f51fad08df28c5ab60e8` (`main`)

**Verified workflow commit:** `79aa0de49e98312a5c4bf75b0e002d77f1c69c5c`

**Run created:** 2026-11-08 20:43:58 UTC

## Results

| Check | GitHub Actions run | Result |
|---|---|---|
| Application validation | [Run 42521610265](https://github.com/aryannang123/Web-Based-ML-model-evaluator/actions/runs/42521610265) | **PASS** |
| Dependency security audit | [Run 42521610274](https://github.com/aryannang123/Web-Based-ML-model-evaluator/actions/runs/42521610274) | **PASS** |

Application validation ran the backend regression suite: **204 tests passed** in 44.179 seconds. The frontend JavaScript syntax check passed. The browser smoke flow passed in all three engines: Chromium 141.0.7390.37, Firefox 142.0.1, and WebKit 26.0. The browser flow registers and signs in a user, uploads a CSV, trains a classification model, and verifies the evaluation chart.

The dependency audit ran:

```text
pip-audit -r backend/requirements.txt -r backend/requirements-e2e.txt
No known vulnerabilities found
```

The requirements use open version ranges rather than a lock file, so this result covers the compatible package versions resolved by the runner on this date. It is a Python package advisory scan; it does not claim a deployment, operating-system package, or production security audit.

## Resolved CI setup issue

The first browser-matrix attempt failed because `ubuntu-latest` resolved to Ubuntu 26.04, which Playwright 1.56.0 did not support. The workflows now pin Ubuntu 24.04. The action references were also updated to the Node 24-compatible v7 releases. The runs linked above are from the updated workflow commit and completed successfully.

## Main-branch status

These checks ran on pull request #42 against `main` at `fd1fb2542f5f723cfc04f51fad08df28c5ab60e8`. They provide successful pull-request evidence. The workflows have not yet been merged, so there is no successful post-merge `push` run on `main` recorded here. The main-branch run will be recorded after the pull request is merged.

The validation workflow runs for pull requests, pushes to `main`, and manual dispatch. The dependency audit also runs weekly. Dependabot is configured for weekly Python dependency and GitHub Actions updates.
