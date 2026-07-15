# Quarterly Restore Drill

Run only in an isolated environment. Record the operator, date, source backup, application image, Alembic revision, start/end time, and result.

1. Provision empty PostgreSQL and object storage instances.
2. Run `python scripts/restore.py BACKUP --confirm RESTORE`.
3. Run `alembic current` and `alembic upgrade head`.
4. Start the application and require live/readiness success.
5. Verify user authentication, document counts, representative source downloads, retrieval references, and one cache-miss RAG answer.
6. Verify that deleted and private documents remain unavailable.
7. Compare measured recovery time with the organization's RTO and the backup timestamp with its RPO.

The drill fails if any required document is missing, authorization differs from production, migrations fail, or readiness does not become healthy.
