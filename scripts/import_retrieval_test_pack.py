"""Upload generated retrieval documents and evaluation questions through public APIs."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import httpx


def request_json(client, method: str, url: str, **kwargs):
    last_error = None
    for attempt in range(3):
        try:
            response = client.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(1 + attempt)
    raise RuntimeError(f"API returned an invalid response for {url}: {last_error}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8080/api")
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--knowledge-base-id", required=True)
    parser.add_argument("--pack", default="demo_data/retrieval_recall_test_pack")
    args = parser.parse_args()

    root = Path(args.pack).resolve()
    client = httpx.Client(base_url=args.base_url, timeout=120)
    login = client.post("/login", json={"username": args.username, "password": args.password})
    login.raise_for_status()
    token = login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    existing_docs = client.get(
        "/documents/list",
        params={"page": 1, "page_size": 100, "knowledge_base_id": args.knowledge_base_id},
        headers=headers,
    ).json()["data"]["items"]
    existing_titles = {item["title"] for item in existing_docs}
    submitted = []
    for path in sorted(root.glob("*.docx")):
        if path.name in existing_titles:
            continue
        with path.open("rb") as stream:
            response = client.post(
                "/documents/upload",
                params={
                    "visibility": "internal",
                    "knowledge_base_id": args.knowledge_base_id,
                    "chunk_template": "general",
                },
                files={"file": (path.name, stream, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
                headers=headers,
            )
        payload = response.json()
        if payload.get("code") != 200:
            raise RuntimeError(f"Upload failed for {path.name}: {payload.get('msg')}")
        submitted.append(payload["data"]["id"])

    existing_items = client.get("/evaluation/items", headers=headers).json()["data"]
    existing_by_question = {item["question"]: item for item in existing_items}
    questions = json.loads((root / "recall_evaluation_50.json").read_text(encoding="utf-8"))
    imported_questions = updated_questions = 0
    for item in questions:
        request_body = {
            "question": item["question"], "expected_answer": item["expected_answer"],
            "expected_keywords": item["expected_keywords"], "category": item["category"],
            "expected_document_titles": item["expected_documents"],
            "expected_chunk_ids": item.get("expected_chunk_ids", []),
            "expected_pages": item.get("expected_pages", []),
            "knowledge_base_id": args.knowledge_base_id, "enabled": True,
        }
        existing = existing_by_question.get(item["question"])
        if existing:
            payload = request_json(client, "PUT", f"/evaluation/items/{existing['id']}", headers=headers, json=request_body)
            updated_questions += 1
        else:
            payload = request_json(client, "POST", "/evaluation/items", headers=headers, json=request_body)
            imported_questions += 1
        if payload.get("code") != 200:
            raise RuntimeError(f"Evaluation import failed: {payload.get('msg')}")
    final_statuses = {}
    for _ in range(90):
        docs = client.get(
            "/documents/list",
            params={"page": 1, "page_size": 100, "knowledge_base_id": args.knowledge_base_id},
            headers=headers,
        ).json()["data"]["items"]
        final_statuses = {item["id"]: item["status"] for item in docs if item["id"] in submitted}
        if len(final_statuses) == len(submitted) and all(value in {"indexed", "failed"} for value in final_statuses.values()):
            break
        time.sleep(2)

    result = {
        "documents_submitted": len(submitted),
        "documents_indexed": sum(value == "indexed" for value in final_statuses.values()),
        "documents_failed": sum(value == "failed" for value in final_statuses.values()),
        "evaluation_questions_imported": imported_questions,
        "evaluation_questions_updated": updated_questions,
    }
    print(json.dumps(result, ensure_ascii=False))
    if result["documents_failed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
