"""Small repeatable OpenSearch Chinese retrieval validation."""
import argparse
import statistics
import time
import httpx

parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://localhost:9200")
parser.add_argument("--count", type=int, default=1000)
args = parser.parse_args()
index = "rag-validation"
client = httpx.Client(base_url=args.url, timeout=30)
client.delete(f"/{index}")
client.put(f"/{index}", json={"mappings": {"properties": {"content": {"type": "text"}, "document_id": {"type": "keyword"}}}}).raise_for_status()
lines = []
for i in range(args.count):
    lines += [{"index": {"_index": index}}, {"document_id": str(i), "content": f"企业员工培训制度 第{i}条 年假报销信息安全流程"}]
client.post("/_bulk?refresh=true", content="\n".join(__import__("json").dumps(x, ensure_ascii=False) for x in lines) + "\n", headers={"Content-Type": "application/x-ndjson"}).raise_for_status()
latencies = []
for _ in range(20):
    start = time.perf_counter()
    response = client.post(f"/{index}/_search", json={"size": 10, "query": {"match": {"content": "员工培训制度"}}})
    response.raise_for_status()
    latencies.append((time.perf_counter() - start) * 1000)
print({"documents": args.count, "hits": response.json()["hits"]["total"]["value"], "p50_ms": round(statistics.median(latencies), 2), "max_ms": round(max(latencies), 2)})