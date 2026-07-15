# Production Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a secure, testable single-host production baseline with immutable deployment, versioned migrations, dependency-aware degradation, reliable health checks, actionable telemetry, and authorization regression coverage.

**Architecture:** Configuration validation and dependency probes are isolated services consumed by startup, health routes, middleware, and upload admission. Alembic owns schema evolution outside application startup. Production Compose builds immutable non-root images, while runtime behavior uses risk-classified RAG streaming and stable degraded-service errors.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy async, Alembic, PostgreSQL/pgvector, Redis, RabbitMQ, MinIO, Prometheus, Grafana, Docker Compose, GitHub Actions, pytest, Locust.

## Global Constraints

- Target a single-host Docker Compose production deployment and preserve future Kubernetes portability.
- Use classified failure behavior: critical mutations fail closed; explicitly safe reads may degrade.
- Keep local authentication, require administrator password rotation, and reject unsafe production defaults.
- Database migration uses a maintenance window, backup, Alembic upgrade, readiness gate, and image rollback.
- Do not introduce knowledge graphs or NL2SQL.
- Preserve all unrelated user changes in the dirty worktree.

---

### Task 1: Production Configuration And Bootstrap Security

**Files:**
- Create: `backend/security/production_config.py`
- Modify: `backend/config.py`
- Modify: `backend/db/models.py`
- Modify: `backend/main.py`
- Modify: `backend/api/auth.py`
- Modify: `.env.example`
- Test: `tests/test_production_config.py`

**Interfaces:**
- Produces: `validate_production_settings(settings) -> list[str]` and `require_password_rotation(user, path) -> None`.
- Removes implicit administrator creation from application startup.

- [ ] Write tests that production rejects debug mode, repository default secrets, missing provider credentials, excessive token lifetime, and insecure object-storage defaults.
- [ ] Run `python -m pytest tests/test_production_config.py -q` and confirm failures are caused by missing validation.
- [ ] Implement deterministic production validation and call it before application startup.
- [ ] Add `must_change_password` to the user model and authentication claims; restrict a flagged administrator to password rotation and logout.
- [ ] Add an explicit idempotent administrator bootstrap command.
- [ ] Run focused tests and the full `tests/` suite.

### Task 2: CI And Immutable Production Images

**Files:**
- Create: `pytest.ini`
- Create: `backend/entrypoint.sh`
- Modify: `backend/Dockerfile`
- Modify: `docker-compose.production.yml`
- Modify: `.github/workflows/ci.yml`
- Modify: `requirements-dev.txt`
- Test: `tests/test_deployment_contract.py`

**Interfaces:**
- Produces: a non-root production image with an immutable application filesystem and a merged Compose config without reload or source bind mounts.

- [ ] Write deployment-contract tests that parse Dockerfile, Compose, pytest, and CI configuration.
- [ ] Run the focused tests and confirm the current reload, source mount, missing runtime dependency install, and root image are detected.
- [ ] Configure pytest to collect only `tests/`; make test dependencies include runtime dependencies.
- [ ] Add a non-root runtime user and production command to the image.
- [ ] Override development volumes/commands in the production Compose file; add resource limits, log rotation, health checks, and internal-only infrastructure ports.
- [ ] Extend CI with dependency audit, secret scan, production image build, and integration services.
- [ ] Validate `docker compose ... config`, build the image, and run focused/full tests.

### Task 3: Alembic Migration Ownership

**Files:**
- Create: `alembic.ini`
- Create: `backend/db/alembic/env.py`
- Create: `backend/db/alembic/script.py.mako`
- Create: `backend/db/alembic/versions/20260715_0001_baseline.py`
- Create: `scripts/bootstrap_admin.py`
- Modify: `backend/main.py`
- Modify: `backend/requirements.txt`
- Modify: `scripts/deploy.ps1`
- Test: `tests/test_migration_contract.py`

**Interfaces:**
- Produces: `alembic upgrade head` for an empty database and `alembic stamp` workflow for a reviewed existing installation.
- Application startup performs no DDL.

- [ ] Write tests asserting startup does not call runtime schema creation and that Alembic metadata contains all current ORM tables.
- [ ] Confirm tests fail against startup DDL and absent Alembic configuration.
- [ ] Configure async Alembic and create a baseline revision matching current models and pgvector indexes.
- [ ] Remove startup DDL execution and document/stage the existing-database stamp procedure.
- [ ] Update deployment to run preflight, backup, migration, readiness, and smoke checks before declaring success.
- [ ] Verify upgrade on an empty temporary PostgreSQL database and run all tests.

### Task 4: Health Probes And Classified Dependency Policy

**Files:**
- Create: `backend/services/dependency_health.py`
- Create: `backend/api/health.py`
- Modify: `backend/main.py`
- Modify: `backend/middleware/production.py`
- Modify: `backend/api/documents.py`
- Modify: `backend/services/storage_service.py`
- Test: `tests/test_dependency_health.py`

**Interfaces:**
- Produces: `DependencySnapshot`, `/api/health/live`, `/api/health/ready`, and authenticated `/api/operations/diagnostics/dependencies`.
- Produces: `require_capability(capability)`, returning stable `503` errors when dependencies cannot safely support an operation.

- [ ] Write tests for PostgreSQL readiness failure, Redis degraded reads, Redis-closed expensive operations, RabbitMQ upload rejection, and MinIO capability loss.
- [ ] Run tests and verify the current unconditional health response fails them.
- [ ] Implement short-timeout cached probes and capability classification.
- [ ] Add health routes and enforce capability admission before saving uploads or starting expensive chat.
- [ ] Return stable error codes and request IDs from failure responses.
- [ ] Run focused tests, fault injection against Compose, and all tests.

### Task 5: Provider Timeout And Circuit Breaker

**Files:**
- Create: `backend/services/circuit_breaker.py`
- Modify: `backend/services/llm_gateway.py`
- Modify: `backend/services/embedding_service.py`
- Modify: `backend/config.py`
- Test: `tests/test_provider_resilience.py`

**Interfaces:**
- Produces: `AsyncCircuitBreaker.call(operation)` with closed, open, and half-open states.
- Provider failures surface as `ProviderUnavailableError` and never expose retrieved context as a fabricated answer.

- [ ] Write tests for timeout, breaker opening, half-open recovery, and structured provider errors.
- [ ] Confirm failures against current unbounded provider calls.
- [ ] Add explicit connect/read/total timeout configuration and minimal circuit breaker behavior.
- [ ] Replace raw-context generation fallback with stable `AI_PROVIDER_UNAVAILABLE` SSE failure.
- [ ] Run focused tests and all tests.

### Task 6: Metrics, Alerts, And Dashboard

**Files:**
- Modify: `backend/middleware/production.py`
- Modify: `backend/services/observability.py`
- Modify: `backend/core/rag_pipeline.py`
- Modify: `ops/prometheus/alerts.yml`
- Create: `ops/grafana/provisioning/dashboards/dashboard.yml`
- Create: `ops/grafana/dashboards/rag-operations.json`
- Test: `tests/test_observability_contract.py`

**Interfaces:**
- Produces bounded route-template labels and metrics for TTFT, total latency, cache, empty retrieval, retries, provider failures, dependency degradation, and circuit state.

- [ ] Write tests proving UUID paths collapse to route templates and TTFT is recorded once per response.
- [ ] Confirm current concrete-path metric behavior fails.
- [ ] Normalize route labels and instrument first emitted answer token.
- [ ] Add alert rules and a provisioned dashboard using the new metrics.
- [ ] Validate Prometheus rules, Grafana JSON, metrics output, and all tests.

### Task 7: Risk-Based Streaming And Validation

**Files:**
- Modify: `backend/core/rag_pipeline.py`
- Modify: `backend/services/reflection_service.py`
- Modify: `backend/security/ai_guardrails.py`
- Modify: `frontend/src` chat stream consumer files discovered during implementation
- Test: `tests/test_rag_streaming_policy.py`

**Interfaces:**
- Produces: deterministic `classify_response_risk(...)` and SSE completion states `completed`, `blocked`, `degraded`, and `retryable_failure`.

- [ ] Write tests showing normal answers stream before reflection, high-risk answers buffer, and exposed output is never silently replaced.
- [ ] Confirm current all-buffered behavior fails normal streaming expectations.
- [ ] Implement deterministic risk classification and stream normal model tokens after retrieval.
- [ ] Restrict LLM reflection to buffered high-risk requests or deterministic pre-output validation failures.
- [ ] Update the frontend to render stable completion/failure states and TTFT metadata.
- [ ] Run focused tests, frontend build, live SSE checks, and all tests.

### Task 8: Authorization, Deletion, And Fault Regression Suite

**Files:**
- Create: `tests/integration/test_authorization_isolation.py`
- Create: `tests/integration/test_cache_memory_isolation.py`
- Create: `tests/integration/test_document_deletion.py`
- Create: `tests/integration/test_dependency_faults.py`
- Create: `tests/integration/test_migrations.py`
- Modify: `tests/locustfile.py`
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Produces release-gate evidence for zero cross-user access, complete deletion invalidation, correct degradation, migration success, error rate below 1%, and non-regressing P95 TTFT.

- [ ] Add fixtures for two users, departments, private knowledge bases, documents, memories, and cache entries.
- [ ] Write cross-user API and retrieval denial tests and confirm any discovered leak reproduces before fixing it.
- [ ] Test deletion invalidates database chunks, object storage, retrieval cache, and answer cache.
- [ ] Add Unicode/encoded/document-sourced injection cases and dependency fault cases.
- [ ] Add empty-database and stamped-existing-database migration jobs.
- [ ] Run the Locust baseline, record P95 TTFT/error rate, and enforce comparison in CI.
- [ ] Run backend tests, frontend build, Compose validation, image smoke test, and production readiness checks.

### Task 9: Runbook And Release Verification

**Files:**
- Modify: `ops/PRODUCTION.md`
- Create: `ops/RELEASE_CHECKLIST.md`
- Create: `ops/RESTORE_DRILL.md`

**Interfaces:**
- Produces operator procedures for bootstrap, backup, migration, rollback, alert routing, and quarterly restore evidence.

- [ ] Document exact initial deployment and existing-database baseline commands.
- [ ] Document classified dependency failures and operator actions.
- [ ] Add release and quarterly restore evidence templates with owners and pass/fail criteria.
- [ ] Execute the release checklist against the local Compose stack and record the results.
- [ ] Run final repository verification and review the complete diff for secret or unrelated-file changes.
