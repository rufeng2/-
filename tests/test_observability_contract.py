from backend.middleware.production import normalized_route


def test_uuid_and_numeric_paths_have_bounded_metric_labels():
    assert normalized_route("/api/documents/123e4567-e89b-12d3-a456-426614174000/chunks/42") == "/api/documents/{id}/chunks/{id}"


def test_static_paths_are_preserved():
    assert normalized_route("/api/health/ready") == "/api/health/ready"
