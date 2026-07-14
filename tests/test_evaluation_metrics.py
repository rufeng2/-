from types import SimpleNamespace

from backend.services.evaluation_service import retrieval_metrics


def item(**overrides):
    values = {
        "expected_chunk_ids": [],
        "expected_document_titles": [],
        "expected_pages": [],
        "expected_keywords": [],
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def result(title: str, chunk_id: str, content: str = "", page=None):
    return {
        "document_title": title,
        "chunk_id": chunk_id,
        "content": content,
        "metadata": {"page": page} if page else {},
    }


def test_context_precision_counts_each_relevant_chunk():
    evaluation_item = item(expected_document_titles=["policy.docx"])
    results = [
        result("policy.docx", "1"),
        result("policy.docx", "2"),
        result("other.docx", "3"),
        result("policy.docx", "4"),
        result("other.docx", "5"),
        result("other.docx", "6"),
    ]
    metrics = retrieval_metrics(evaluation_item, results, context_k=6)
    assert metrics["context_relevant_count"] == 3
    assert metrics["context_count"] == 6
    assert metrics["context_precision"] == 0.5
    assert metrics["relevant_ranks"] == [1]


def test_context_precision_only_uses_llm_context_window():
    evaluation_item = item(expected_document_titles=["policy.docx"])
    results = [
        result("policy.docx", "1"),
        result("other.docx", "2"),
        result("other.docx", "3"),
        result("other.docx", "4"),
        result("other.docx", "5"),
        result("other.docx", "6"),
        result("policy.docx", "7"),
    ]
    metrics = retrieval_metrics(evaluation_item, results, context_k=6)
    assert metrics["context_count"] == 6
    assert metrics["context_relevant_count"] == 1
    assert metrics["context_precision"] == 1 / 6


def test_chunk_labels_take_priority_over_document_labels():
    evaluation_item = item(
        expected_chunk_ids=["wanted"],
        expected_document_titles=["policy.docx"],
    )
    results = [
        result("policy.docx", "wrong"),
        result("other.docx", "wanted"),
    ]
    metrics = retrieval_metrics(evaluation_item, results, context_k=2)
    assert metrics["context_relevant_count"] == 1
    assert metrics["relevant_ranks"] == [2]