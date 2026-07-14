"""
下载精排模型脚本
用法: python scripts/download_reranker.py

自动尝试多个源，下载 BGE Reranker 或备选轻量模型
"""
import os
import sys
import urllib.request

# 当前使用的模型：cross-encoder/ms-marco-MiniLM-L-6-v2（86MB，已下载）
# 
# 如需切换到 BGE 系列，取消下面的注释并注释上面的配置
# 下载命令：python scripts/download_reranker.py

MODELS = [
    # 当前使用的：轻量快速，~86MB  ✅ 已下载
    {
        "name": "cross-encoder/ms-marco-MiniLM-L-6-v2",
        "files": [
            "pytorch_model.bin",
            "config.json",
            "tokenizer.json",
            "tokenizer_config.json",
            "special_tokens_map.json",
        ],
        "mirrors": [
            "https://hf-mirror.com",
            "https://huggingface.co",
        ],
    },
    # 备选 1：中文更强，~440MB
    # {
    #     "name": "BAAI/bge-reranker-base",
    #     "files": ["model.safetensors", "config.json", "tokenizer.json", ...],
    #     "mirrors": ["https://hf-mirror.com", "https://huggingface.co"],
    # },
]


def download_file(url: str, dest: str) -> bool:
    """下载单个文件，支持断点续传"""
    if os.path.exists(dest):
        existing_size = os.path.getsize(dest)
        print(f"  已存在: {os.path.getsize(dest)/1024/1024:.1f} MB", flush=True)
        return True

    os.makedirs(os.path.dirname(dest), exist_ok=True)
    print(f"  下载: {url.split('/')[-1]}", flush=True)

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            if total:
                print(f"  大小: {total/1024/1024:.1f} MB", flush=True)
            with open(dest + ".tmp", "wb") as f:
                f.write(resp.read())
            os.rename(dest + ".tmp", dest)
            print(f"  ✓ {os.path.getsize(dest)/1024/1024:.1f} MB", flush=True)
            return True
    except Exception as e:
        print(f"  ✗ {e}", flush=True)
        return False


def main():
    for model in MODELS:
        name = model["name"]
        cache_dir = os.path.join(
            os.path.expanduser("~"),
            ".cache",
            "huggingface",
            "hub",
            "models--" + name.replace("/", "--"),
            "snapshots",
            "main",
        )
        os.makedirs(cache_dir, exist_ok=True)

        print(f"\n=== {name} ===", flush=True)

        all_ok = True
        for fname in model["files"]:
            dest = os.path.join(cache_dir, fname)
            if os.path.exists(dest) and os.path.getsize(dest) > 1000:
                print(f"  ✓ {fname} ({os.path.getsize(dest)/1024/1024:.1f} MB, 已缓存)", flush=True)
                continue

            downloaded = False
            for mirror in model["mirrors"]:
                url = f"{mirror}/{name}/resolve/main/{fname}"
                if download_file(url, dest):
                    downloaded = True
                    break

            if not downloaded:
                all_ok = False
                print(f"  ✗ {fname} 下载失败", flush=True)

        if all_ok:
            print(f"  ✓ {name} 下载完成", flush=True)
            # 不再尝试其他模型
            return 0
        else:
            print(f"  × {name} 下载不完整，尝试下一个...", flush=True)

    print("\n所有模型下载失败。你可以在网络环境好时手动运行此脚本：", flush=True)
    print("  python scripts/download_reranker.py", flush=True)
    print("或者暂时关闭精排功能（在 .env 中设置 RETRIEVAL_USE_RERANK=false）", flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
