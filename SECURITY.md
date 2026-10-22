# Security Policy

The AIOps Sentinel project takes the security of our infrastructure telemetry, machine learning pipelines, and self-healing automation seriously. This policy outlines our vulnerability disclosure process, threat model, and security best practices.

---

## 1. Supported Versions

Security updates and critical patches are actively provided for the following releases:

| Version | Supported Status | Patch Level |
| :--- | :--- | :--- |
| **1.0.x** | :white_check_mark: Supported | Critical & High Vulnerabilities |
| **< 1.0.0** | :x: End of Life | Not Supported |

---

## 2. Reporting a Vulnerability

**DO NOT report security vulnerabilities through public GitHub issues, discussions, or pull requests.**

If you discover or suspect a security vulnerability within AIOps Sentinel:
1. Privately email the core security maintainers at **`security@aiops-sentinel.local`** (or contact repository leads via GitHub Security Advisories).
2. Include the following details:
   - Component affected (e.g., FastAPI backend, Windows Agent, Prisma ORM, Nginx configuration).
   - Step-by-step reproduction instructions or proof-of-concept (PoC) exploit payload.
   - Assessment of impact (e.g., privilege escalation, unauthorized process termination, SQL injection, token leakage).
3. The security team will acknowledge receipt of your report within **48 hours** and provide an estimated remediation timeline.
4. We adhere to responsible disclosure: We request that you give us **90 days** to patch and release a fix before public disclosure.

---

## 3. Threat Model & Security Controls

AIOps Sentinel operates with high privileges because it monitors and terminates operating system processes. The platform implements multi-layered security controls to mitigate risks:

### 3.1 Role-Based Access Control (RBAC)
- All endpoints strictly enforce role authorization:
  - `ADMIN`: User management, organization settings, auto-recovery enablement.
  - `OPERATOR`: Monitoring toggles, incident resolution. Strictly prohibited from user creation and autonomous recovery activation.
  - `VIEWER`: Read-only access across telemetry, alerts, and audit logs.
- Password hashing is enforced via `bcrypt` with automatic salting. Authentication uses signed JWT bearer tokens with short lifespans (15-30 minutes).

### 3.2 Guarded Process Remediation Controls
- To prevent accidental or malicious termination of operating system processes:
  - Critical OS PIDs ($\le 4$, `system`, `csrss.exe`, `lsass.exe`, `explorer.exe`) are hardcoded as non-terminable.
  - Target processes must have been captured in live telemetry samples within the last 120 seconds.
  - Only administrators can toggle autonomous remediation (`autoRecovery`).

### 3.3 Network Ingress & Header Hardening
- Nginx acts as the edge reverse proxy, dropping unauthenticated internal requests.
- The FastAPI middleware automatically enforces:
  - `Strict-Transport-Security` (HSTS)
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - Content Security Policy (`CSP`)
