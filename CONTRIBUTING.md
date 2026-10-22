# Contributing to AIOps Sentinel

Welcome to the AIOps Sentinel open-source community! We appreciate your interest in contributing to our platform. This guide provides standards and procedures to ensure high code quality, security, and reproducibility.

---

## 1. Code of Conduct
All contributors and maintainers are expected to adhere to our [Code of Conduct](file:///c:/Users/Ifreen/Downloads/MLOPS_CP/CODE_OF_CONDUCT.md). Please report any unacceptable behavior to `security@aiops-sentinel.local`.

---

## 2. Getting Started & Development Setup

### 2.1 Fork & Clone
1. Fork the repository on GitHub.
2. Clone your fork locally:
   ```bash
   git clone https://github.com/your-username/MLOPS_CP.git
   cd MLOPS_CP
   ```

### 2.2 Local Environment Setup
Execute the automated setup script to provision dependencies, build the frontend, and start Docker:
```powershell
# Windows:
.\setup.ps1

# Linux / macOS / WSL:
./setup.sh
```

---

## 3. Development Standards & Conventions

### 3.1 Python Backend Guidelines
- **Code Style:** Adhere to PEP 8. Format using `black` (line length 100) and sort imports using `isort`.
- **Type Annotations:** All functions and methods must have strict type hints.
- **Asynchronous Code:** Use `async` / `await` for I/O operations (database queries, network requests, HTTP handlers).
- **Prisma Schema Changes:** If modifying `backend/prisma/schema.prisma`, always run `python -m prisma generate` and test migrations using `npx prisma db push`.
- **Testing Standard:** Every new feature or controller must include unit and integration tests under `backend/tests/`. Backend code coverage must remain **above 95.0%**.

### 3.2 Frontend React Guidelines
- **Framework:** React 18, TypeScript, Tailwind CSS.
- **Component Patterns:** Prefer functional components with hooks (`useState`, `useQuery`, `useMutation`).
- **No Implicit Any:** Code must compile with zero errors under `npm run build` (`tsc -b`).
- **UI Tests:** Add unit tests using Vitest (`*.test.tsx`) and verify user interactions with Playwright (`aiops-sentinel/e2e/*.spec.ts`).

---

## 4. Submitting Pull Requests

1. **Create a Feature Branch:**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-description
   ```
2. **Run All Local Quality Gates:**
   ```powershell
   # 1. Run backend pytest and verify coverage > 95%
   cd backend
   & .\.venv\Scripts\python.exe -m pytest tests --cov=app --cov-fail-under=95
   cd ..

   # 2. Run frontend component tests
   npm --prefix aiops-sentinel run test:ui

   # 3. Run full Playwright browser tests
   npm --prefix aiops-sentinel run test:e2e

   # 4. Verify system health
   .\healthcheck.ps1
   ```
3. **Commit Messages:** Follow the Conventional Commits specification:
   - `feat(ml): add cyclical temporal features to anomaly service`
   - `fix(auth): prevent session token leak in logout redirect`
   - `docs(readme): update zero-to-hero setup instructions`
   - `test(e2e): add playwright coverage for situation resolution`
4. **Open a PR:** Push your branch to GitHub and open a Pull Request against the `main` branch. Fill out all sections of the Pull Request template.
