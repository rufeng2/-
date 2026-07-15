from backend.services.dependency_health import DependencySnapshot, capability_available


def healthy_snapshot(**overrides):
    values = {"postgres": True, "redis": True, "rabbitmq": True, "minio": True}
    values.update(overrides)
    return DependencySnapshot(**values)


def test_postgres_is_required_for_every_business_capability():
    snapshot = healthy_snapshot(postgres=False)
    assert not capability_available(snapshot, "chat.read")
    assert not capability_available(snapshot, "documents.upload")


def test_redis_failure_allows_safe_reads_but_blocks_expensive_chat_and_mutations():
    snapshot = healthy_snapshot(redis=False)
    assert capability_available(snapshot, "documents.read")
    assert not capability_available(snapshot, "chat.expensive")
    assert not capability_available(snapshot, "auth.login")


def test_rabbitmq_failure_only_blocks_indexing_operations():
    snapshot = healthy_snapshot(rabbitmq=False)
    assert capability_available(snapshot, "chat.read")
    assert not capability_available(snapshot, "documents.upload")
    assert not capability_available(snapshot, "documents.reindex")


def test_minio_failure_blocks_file_and_image_operations():
    snapshot = healthy_snapshot(minio=False)
    assert capability_available(snapshot, "chat.read")
    assert not capability_available(snapshot, "documents.upload")
    assert not capability_available(snapshot, "documents.download")
    assert not capability_available(snapshot, "chat.image")
