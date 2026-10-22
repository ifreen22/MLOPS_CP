# Production Testing Plan

## Release gates

Every pull request must pass the test gates below. A release candidate must repeat every gate against the production build and publish the generated reports as CI artifacts. A test failure, missing report, or coverage result at or below 95.00% blocks release.

| Test layer | Command / environment | Required evidence | Gate |
| --- | --- | --- | --- |
| Unit | `coverage run -m pytest tests` | JUnit-style terminal result and `coverage.xml` | All tests pass; Python `app` line-and-branch coverage is greater than 95.00% |
| API | FastAPI `TestClient` with mocked Prisma boundaries | Success, validation, auth and error-path assertions | All endpoint contract tests pass |
| Integration | In-process FastAPI flow with deterministic database doubles | Telemetry-to-remediation workflow result | All workflow tests pass |
| UI | `npm run test:ui` in jsdom | Vitest result | All component interaction tests pass |
| Playwright | `npm run test:e2e` against `vite preview` production assets | Playwright HTML report, traces and screenshots on failure | Chromium suite passes |
| Performance | `pytest tests/test_performance.py` in an isolated, warmed environment | Per-endpoint p95 output and host specification | Regression is reviewed; target is p95 under 200 ms for the existing synthetic checks |
| Security | `pytest tests/test_security_rbac.py` plus dependency and secret scanning in CI | RBAC, token, security-header evidence and scanner output | No unapproved high/critical findings |

## Coverage scope and measurement

Coverage is measured only for executable backend production code under `backend/app`, using the committed `.coveragerc`. Seed scripts and the explicitly listed research-validation module are excluded because they are not invoked by the runtime API. The gate uses `fail_under = 95.01`, so a rounded 95.00% result cannot pass. The command below produces the auditable text, XML and HTML reports:

```powershell
cd backend
python -m pip install -r requirements-test.txt
python -m prisma generate
coverage erase
coverage run -m pytest tests
coverage report --show-missing
coverage xml -o coverage.xml
coverage html -d htmlcov
```

## Execution cadence

- Pull request: unit, API, integration, UI, coverage and build gates.
- Nightly: Playwright on the production build, performance baseline, dependency scan and a deployment smoke test.
- Release candidate: repeat all gates in a production-like environment with the intended database migration, credentials supplied through the secret manager, and no mock for external dependencies that are in release scope.
- Post-deploy: authenticated `/api/v1/health` and metrics probes, canary user journey, error-rate/latency observation, and rollback validation.

## Test data and safety controls

Use synthetic accounts, anonymized telemetry, isolated databases and non-production webhook endpoints. Destructive remediation must be exercised only through dry-run mode or a disposable workload. Performance runs must not share production capacity. Production credentials, customer telemetry and action tokens are never written into test output or artifacts.

## Windows-host telemetry prerequisite

The browser cannot safely start a local Python process. The `Start Monitoring` control saves the monitoring state; a separately running Windows agent gathers host data and sends it to `/api/v1/system/telemetry`. On a native run, `start_windows.bat` now installs and starts that agent. For an already-running Docker stack, run the following once from the repository root:

```powershell
py -3.13 -m pip install -r windows-agent-requirements.txt
py -3.13 windows_agent.py
```

Use the same `AGENT_API_TOKEN` in the root `.env` file and the backend container. The dashboard deliberately reports no telemetry until an authenticated agent sends a fresh sample; it does not fabricate host data.
