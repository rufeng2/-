# Production Reliability Design

## Goal

Turn the current single-host Docker Compose deployment into a controlled production baseline while preserving a clean migration path to Kubernetes. The work covers secure configuration, immutable releases, versioned database migrations, dependency-aware degradation, health checks, observability, cold-request latency, and authorization regression testing. Knowledge graphs and NL2SQL remain out of scope.

## Delivery Strategy

Changes are delivered as four independently testable and reversible stages:

1. Secure configuration, local administrator password rotation, CI repair, and immutable non-root images.
2. Alembic migrations, deployment gates, backup integration, and dependency-aware health checks.
3. Classified dependency degradation, queue admission checks, Redis enforcement, and model timeouts/circuit breaking.
4. Risk-based answer streaming, TTFT/SLO telemetry, dashboards, alerts, authorization tests, and fault injection.

The target platform is a single-host Docker Compose deployment. Components must not rely on container-local mutable state or startup-time schema creation so they can later move to Kubernetes without redesigning application contracts.

## Secure Configuration And Identity

Development retains convenient defaults. When `APP_ENV=production`, startup fails if any of these conditions are present:

- `DEBUG=true`.
- The JWT key is empty or equals the repository default.
- The administrator password is empty or equals the repository default.
- Required model credentials are absent.
- Access tokens remain valid for more than the production maximum.
- Object storage uses an insecure default credential or an invalid transport configuration.

The local administrator account remains supported. A newly initialized administrator has `must_change_password=true`. Until the password is rotated, authorization permits only password change, token inspection, and logout. Administrator bootstrap becomes an explicit deployment command rather than an application-start side effect. OIDC remains available for a future identity migration but is not required for this release.

## Build, CI, And Deployment

The production image is immutable, runs as a non-root user, contains no development bind mounts, and starts Uvicorn without reload. The production Compose overlay specifies resource limits, log rotation, health checks, and versioned image references. Nginx is the only public business entry point. PostgreSQL, Redis, MinIO, and the RabbitMQ management interface are not publicly exposed by default.

CI performs these gates on a clean runner:

- Install runtime and test dependencies from reproducible dependency definitions.
- Restrict pytest collection to `tests/`.
- Compile and test the backend against PostgreSQL with pgvector and Redis.
- Build the frontend.
- Validate the merged Compose configuration.
- Scan Python and Node dependencies, repository secrets, and the built container image.
- Build the exact production image used by deployment.

The release flow is configuration preflight, backup, schema migration, image start, readiness validation, and smoke tests. Failure stops the deployment and restores the previous image. Database restoration is reserved for a verified migration failure during the maintenance window; destructive automated downgrades are prohibited.

## Database Migrations

Alembic owns all schema changes. Existing installations receive a reviewed baseline revision and are stamped only after backup and schema verification. Empty databases must upgrade from zero to head. Application startup no longer executes DDL and the runtime database role does not need schema-owner privileges.

Migration verification covers both an empty database and the current schema baseline. Every release records the image version and Alembic revision so backup and rollback procedures can validate compatibility.

## Health And Dependency Degradation

Health endpoints have separate contracts:

- `/api/health/live` confirms that the application process and event loop are alive.
- `/api/health/ready` verifies production configuration, PostgreSQL, Redis, and required storage connectivity.
- An authenticated diagnostic endpoint reports RabbitMQ and model-provider state without invoking a paid model request on every probe.

Failures are classified by capability:

- PostgreSQL failure makes readiness fail and stops business traffic.
- Redis failure marks the service degraded. Public read-only operations may continue, but login, mutation, upload, administration, and expensive chat operations fail with `503` so rate and quota enforcement cannot be bypassed.
- RabbitMQ failure leaves existing-document question answering available but rejects uploads and reindex requests with `503` before accepting files.
- Model-provider failure returns structured `AI_PROVIDER_UNAVAILABLE` with a request ID. Retrieved document text is never presented as a generated answer.
- MinIO failure disables upload, original-file download, and image question answering. Existing text-index question answering may continue.

External calls have explicit connect/read/total timeouts. Model calls use a small circuit breaker with observable open, half-open, and closed states. Degradation responses are stable API errors that the frontend can distinguish from validation and authorization failures.

## RAG Streaming And Validation

Answer handling is risk-based:

- Answer-cache hits stream immediately.
- Normal knowledge questions pass input safety and retrieval checks, then stream model tokens immediately. Lightweight deterministic validation runs as the stream completes. A failed post-stream validation marks the response as requiring regeneration; it does not silently replace already emitted text.
- Requests involving sensitive data, privileged actions, low-confidence retrieval, or detected instruction risk remain buffered. They follow generate, validate, at-most-once retry, output-safety, then emit.
- LLM reflection is not called for every normal request. It is reserved for high-risk requests or deterministic validation failures where no answer has been exposed.

SSE events expose stable states for progress, normal completion, degraded service, blocked input, and retryable failure. Completion metadata includes `ttft_ms`, total duration, stage timings, cache outcomes, validation source, and retry status.

## Observability And SLOs

Prometheus labels use route templates rather than concrete UUID paths. Metrics cover:

- HTTP and RAG TTFT and total latency.
- Per-stage RAG latency.
- Retrieval, intent, and answer cache outcomes.
- Empty retrieval, safety rejection, reflection retry, provider timeout, circuit state, and dependency degradation.
- Database pool pressure and Celery queue backlog.

Grafana includes a provisioned RAG operations dashboard. Prometheus alerts cover backend readiness, error rate, P95/P99 latency, TTFT regression, cache degradation, provider errors, queue backlog, database saturation, and storage capacity. Alert receivers are environment-specific and no credentials are stored in the repository.

Initial release gates are zero authorization-test failures, HTTP error rate below 1% in the load profile, and P95 TTFT no worse than the recorded baseline. Numeric production SLOs are finalized after representative load testing rather than invented from development hardware.

## Security And Reliability Tests

Tests verify behavior rather than only helper functions:

- User, department, knowledge-base, document, chunk, cache, reference, and long-term-memory isolation.
- Deleting or restricting a document invalidates vectors, object references, and relevant caches.
- Prompt injection through questions, indexed documents, OCR text, Unicode confusables, and encoded variants.
- Redis, RabbitMQ, MinIO, PostgreSQL, and model-provider fault behavior.
- Alembic upgrade from an empty database and from the reviewed existing-schema baseline.
- CI smoke tests through Nginx and Locust profiles for normal RAG, cache hits, concurrent uploads, and dependency degradation.

Backups and restores are exercised in a separate environment and recorded. The production runbook specifies the responsible operator, evidence to collect, and acceptance criteria for quarterly restore drills.

## Explicit Non-Goals

- Kubernetes manifests or a service mesh.
- Multi-node database, Redis, RabbitMQ, or object-storage high availability.
- Knowledge graph retrieval without a demonstrated entity-relationship query requirement.
- NL2SQL without a demonstrated business-database query requirement and its separate read-only security design.
