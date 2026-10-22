# Final Deployment Report

## Executive summary

The repository is not currently deployed as a runnable Docker stack under the project name `mlops_cp`.

Fresh verification evidence:

- `docker compose ps` for this repo returned no running services.
- `docker compose ps --all` for this repo returned no containers for the project.
- URL probes to `http://localhost:80`, `http://localhost:3000`, `http://localhost:9090`, `http://localhost:8000`, `http://localhost:5432`, and `http://localhost:6379` all failed.
- The only active Docker containers visible were unrelated Supabase services and a separate project (`flow-scribe-48-main`), not this repository’s stack.

Overall deployment score: 0 / 100

---

## Containers

| Container / service | Status | Evidence | Port(s) |
|---|---|---|---|
| db | Not running | `docker compose ps` shows no `mlops_cp` containers | 5432 |
| redis | Not running | no project container present | 6379 |
| backend | Not running | no project container present | 8000 |
| frontend | Not running | no project container present | 80 / 3000 (via nginx/front-end) |
| nginx | Not running | no project container present | 80 |
| prometheus | Not running | no project container present | 9090 |
| grafana | Not running | no project container present | 3000 |
| loki | Not running | no project container present | 3100 |
| promtail | Not running | no project container present | none |
| otel-collector | Not running | no project container present | 4317 / 4318 |
| node-exporter | Not running | no project container present | none |
| cadvisor | Not running | no project container present | none |

---

## Status

### Verified live status

- Compose project `mlops_cp` has zero containers.
- `docker compose ps --all` returns empty for this repository’s stack.
- `docker compose logs` returns empty because no containers were started under this project.

### Unrelated Docker activity observed

The host has other running containers unrelated to this repository, including Supabase services. These were not part of the `mlops_cp` app deployment.

---

## Ports

Expected ports from [docker-compose.yml](docker-compose.yml):

- Postgres: 5432
- Redis: 6379
- Backend: 8000
- Frontend via nginx: 80
- Grafana: 3000
- Prometheus: 9090
- Loki: 3100
- OTel collector: 4317, 4318

Actual observed results:

- Port 80: connection failed
- Port 3000: connection failed
- Port 9090: connection failed
- Port 8000: connection failed
- Port 5432: connection failed
- Port 6379: connection failed

---

## URLs

| URL | Result | Notes |
|---|---|---|
| http://localhost | Failed | no nginx instance bound |
| http://localhost:80 | Failed | no service listening |
| http://localhost:3000 | Failed | no frontend or Grafana container |
| http://localhost:9090 | Failed | no Prometheus container |
| http://localhost:8000 | Failed | no backend container |
| http://localhost:5432 | Failed | no Postgres container |
| http://localhost:6379 | Failed | no Redis container |
| http://localhost/api/v1/health | Failed | backend not running |
| http://localhost/swagger | Failed | API not running |
| http://localhost/docs | Failed | API not running |

---

## Health checks

### Frontend
- Status: failed / not running
- Evidence: no project container, no port binding, no HTTP response

### Backend
- Status: failed / not running
- Evidence: no project container, no port binding, health endpoint unavailable

### Database
- Status: failed / not running
- Evidence: no Postgres container for the project

### Redis
- Status: failed / not running
- Evidence: no Redis container for the project

### Prometheus
- Status: failed / not running
- Evidence: no Prometheus container

### Grafana
- Status: failed / not running
- Evidence: no Grafana container

### Nginx
- Status: failed / not running
- Evidence: no nginx container bound to port 80

---

## Remaining issues

1. No `mlops_cp` Docker Compose project is currently running.
2. The stack never reached container startup under the repo’s current Docker context.
3. No backend or frontend health checks succeeded.
4. No project URLs responded with HTTP 200.
5. Docker is running, but it is hosting unrelated containers rather than this repository’s deployment.

---

## Root cause

The Docker stack is configured correctly in [docker-compose.yml](docker-compose.yml), and `docker compose config` resolves its variables successfully, but the application stack never actually launched under the current environment. The container runtime is active, yet no services for this repository were created or remained running under the `mlops_cp` project name.

This indicates a deployment orchestration/runtime issue in the current environment, not a missing `.env` issue.

---

## Deployment verdict

Status: Failed

This repository is not currently deployable in the active Docker environment as configured.
