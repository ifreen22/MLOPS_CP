# AIOps Sentinel — Final Project Audit

**Audit date:** 2026-10-21  
**Deployment reviewed:** local Windows host, Docker Compose backend/frontend, PostgreSQL, and the Windows telemetry agent.

## Executive summary

The local application is running and its main telemetry, authentication, frontend build, API, and model-loading paths are operational. This work closed several concrete integration and safety gaps: authenticated Mission Control hooks use the shared JWT client; process actions require authorization, fresh telemetry, and a PID/name/process-creation-time match; the Windows agent revalidates that identity before acting; action requests and completions are recorded; and Mission Control now displays recent action history.

The project is **not production-ready and is not 100% complete**. Critical integrations still lack production data or infrastructure: tenant isolation is inconsistent across APIs, RCA has no real cluster topology, alert clustering has no live alert corpus, risk scoring is trained on synthetic examples, Kubernetes/GitHub/notification integrations are incomplete, and no real process termination was executed. “Ready” model artifacts indicate loadability, not production validation.

The full page/control, API operation, model, and infrastructure checklist is maintained in [`PROJECT_AUDIT.md`](./PROJECT_AUDIT.md).

## Status key

1. **Implemented and working** — exercised behavior or verified live operation.
2. **Implemented but partially working** — code exists, but data, infrastructure, safety conditions, or end-to-end evidence are missing.
3. **UI only (no backend)** — visible interface without a functioning persistence/API capability.
4. **Missing** — no usable implementation is present.

## Dashboard page checklist

| Page / area | Status | Verified behavior and remaining limitation |
|---|---:|---|
| Mission Control | 2 | Authenticated telemetry/settings integration, monitoring controls, recommendations, process display, and action queue UI are wired. Process action requires confirmation and Auto Recovery. New recent-action history polls the authenticated API. No real termination was attempted. |
| Situation Room | 2 | Page, refresh, and situation API are wired. No live situations were available to verify resolve/report behavior with populated records. |
| Root Cause Graph | 2 | Graph view, topology API, model health, and guarded training are wired; a trained GraphSAGE artifact loads. No compatible live Kubernetes/service topology is available for RCA inference. |
| Alert Clustering | 2 | Page and clustering API/model path exist. No open alerts/clusters were present, so real cluster formation and populated export were not demonstrated. |
| Change Intelligence | 2 | Page/API list exists, but there are no ingested Kubernetes/deployment change events to display or validate. |
| Remediation Playbooks | 2 | Built-in high-CPU process playbook has a dry-run and guarded queued execution path. Other saved playbooks do not have execution handlers; no real termination was run. |
| SLO Dashboard | 1 | Local create/list/evaluate/delete flow was exercised against persisted telemetry. |
| Settings | 2 | Authentication and admin-protected user APIs exist. Policy/Rego, service tiers, and outbound notification routing remain informational or unconfigured. |
| Shared application shell | 1 | Login, protected routing, navigation, theme toggle, and sign-out flow are implemented; route smoke checks covered the eight dashboard routes. |

## Backend, telemetry, observability, and infrastructure

| Component | Status | Evidence / remaining limitation |
|---|---:|---|
| FastAPI service | 1 | Rebuilt container is healthy; `/api/v1/health` returned `ok`. |
| API inventory | 2 | Current OpenAPI schema contains **84 operations: 49 GET, 34 POST, and 1 DELETE**. The detailed endpoint-by-endpoint checklist and evidence are in `PROJECT_AUDIT.md`; not every mutation was run because some can alter data or trigger host actions. |
| Local authentication | 1 | Bootstrap-admin login returned a bearer token. Protected action-history access succeeded; unauthenticated access returned 401. |
| Windows telemetry agent | 1 | Restarted with the identity-revalidation implementation. A fresh sample included CPU/system telemetry, 24 processes, and `create_time` values. |
| Prometheus | 1 | Earlier audit found all five configured targets up. |
| Grafana | 2 | Service health is available, but datasource/dashboard provisioning is not reproducible from source and the live instance had no configured dashboards/datasources during the earlier check. |
| Loki / Promtail | 2 | Services and configuration exist; complete host/Docker log ingestion is not proven end to end. |
| OpenTelemetry | 2 | Collector is configured, but traces are exported only to debug and have no persistence backend. |
| PostgreSQL / Prisma | 2 | Local database and schema push work. No checked-in migration history exists; `db push` is not a production migration strategy. |
| Docker Compose | 2 | Local services run, but this does not establish production deployment, backup, recovery, or secret-rotation readiness. |

## Recovery-action safety slice implemented

- Auto Recovery can only be enabled by an administrator; process-action requests require an administrator or operator.
- Queueing requires Auto Recovery to be enabled, a recent timezone-aware telemetry sample, a process above the CPU threshold, a non-protected process name, and a finite process creation time.
- The queue stores the organization, requester, process name, and process creation time. Request audit logging is transactional.
- The Windows agent checks the latest sample and revalidates PID, process name, and creation time against the queued snapshot before termination. It reports a bounded success/failure result.
- Completion state and audit logging are persisted transactionally. Completion status is validated as `SUCCESS` or `FAILED`.
- An authenticated, organization-scoped action-history API and a Mission Control history panel were added.
- Regression tests cover stale/missing/invalid telemetry, role checks, Auto Recovery gating, history scoping, request/completion audit records, and invalid completion status.
- **No process termination was queued or executed during this audit. Auto Recovery remains disabled.** Persistence behavior for action request/completion is covered with mocked database transactions; an end-to-end destructive action remains intentionally unverified.

## ML services and model-training status

| Model/service | Status | Dataset and verified behavior | Remaining gap |
|---|---:|---|---|
| Isolation Forest anomaly detection | 2 | Artifact/scaler load; a live host telemetry analysis previously returned an anomaly result. | Training provenance/benchmark quality is undocumented; requires representative data and calibration. |
| HDBSCAN + MiniLM alert clustering | 2 | Clustering/embedding artifacts load; inference is gated on actual alert/log text. | No live open-alert corpus was present to validate persistent clustering. |
| LightGBM deployment-risk scoring | 2 | Artifact loads; orchestrator rejects incomplete deployment context. | Training uses 5,000 synthetic deployment examples; real deployment outcomes and calibration are absent. |
| GraphSAGE root-cause analysis | 2 | Trained weights load and report ready; retraining has freshness and free-memory safeguards. | Training used synthetic Sock Shop fault samples. Live inference requires a compatible real topology matrix, which is unavailable. |
| ML orchestrator | 2 | Live telemetry path is exercised and unavailable inputs are reported honestly rather than fabricated. | Clustering, RCA, and deployment-risk paths need real input sources and evaluation data. |

## Completed features and verification results

- Mission Control telemetry and settings hooks use the shared JWT-aware API client.
- Authenticated process action queueing, process identity checks, result persistence/auditing, and recent-action history are implemented.
- Backend and frontend containers were rebuilt and redeployed; Prisma client generation and schema push completed.
- Focused backend suite: **25 passed** in the rebuilt backend container.
- Backend Python compile check: passed.
- Windows agent syntax check: `python -m py_compile windows_agent.py` passed.
- Frontend production build and TypeScript build: passed.
- Frontend lint: passed with one pre-existing Fast Refresh warning in `ThemeProvider.tsx`.
- Runtime smoke checks: backend health returned `ok`; frontend returned HTTP 200; action-history route was registered, rejected unauthenticated access with HTTP 401, and returned an empty array to the bootstrap administrator.
- Live agent verification: fresh timestamp, 24 processes, and process creation-time values were observed after restart.
- No real process action or model retraining was attempted.

## Remaining limitations and production blockers

1. **Tenant isolation:** organization scoping is inconsistent across existing controllers. A comprehensive API-by-API tenant-boundary review and negative cross-organization tests are required before multi-tenant deployment.
2. **RCA and change intelligence:** provide Kubernetes credentials/event ingestion and a stable topology schema; train/evaluate against labeled, representative incidents.
3. **Alert clustering:** populate representative persisted alert/log records and validate clustering, deduplication, and cluster lifecycle.
4. **Risk scoring:** replace synthetic-only training evidence with deployment history/outcome labels, then calibrate and monitor model performance.
5. **Playbooks:** implement and validate handlers for saved playbooks other than the built-in process action. Keep destructive operations gated and independently reviewed.
6. **GitHub integration:** implement signed webhook ingestion and repository/service mapping; configure a public HTTPS callback endpoint.
7. **Notifications and policy:** implement a configured delivery provider, delivery status/retries, persisted policy rules, and actual policy evaluation.
8. **Observability:** provision Grafana dashboards/datasources from source; verify Windows/Docker log ingestion; configure trace persistence.
9. **Database operations:** replace schema push deployment with reviewed, versioned migrations; define backups and restore tests.
10. **Operations/security:** define secret rotation and token-expiry procedures; scope/rotate the agent credential; conduct an end-to-end authorization review and security testing.
11. **Automated UI testing:** add a maintained frontend test/e2e suite; the production build and manual/browser checks do not replace it.
12. **Native startup:** ensure the supported Windows startup flow launches and supervises the telemetry agent, not just the app services.

## Verification steps

1. Start the local stack from the project directory with `docker compose up -d --build`; start the Windows agent from the project root using the configured local environment.
2. Open the dashboard at `http://localhost:8081` and sign in with the local administrator credentials configured in the ignored `.env` file. Do not copy those credentials into logs or source.
3. Confirm Mission Control receives changing host telemetry. The agent sample should include process `create_time` values.
4. Confirm the Recent Process Actions panel loads and refreshes. With no queued actions it should show an empty-history message.
5. Verify the authenticated history API returns an array and that an unauthenticated request returns 401.
6. Keep Auto Recovery disabled for routine checks. Do not test termination on a real host process; the unit tests cover identity mismatch rejection without performing a destructive action.
7. Run the focused backend tests inside the backend container: `docker exec mlops_cp-backend-1 python -m pytest -q /app/tests/test_orchestrator.py`.
8. Build/lint the frontend from `aiops-sentinel`: `npm run build` and `npm run lint`.

## Production readiness score

**46 / 100 — local integrated prototype; not production-ready.**

This is a reasoned readiness estimate, not a certification. The score recognizes that authentication, the local telemetry path, core dashboard routes, the backend, and several model artifacts operate. It is reduced by incomplete tenant isolation, synthetic-only training evidence, absent production data sources, incomplete integrations, migration/observability gaps, and lack of automated UI and destructive-action end-to-end validation. The project must not be represented as 100% complete.
