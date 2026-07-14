# API Key 获取教程

本项目使用三个模型服务，两个需要 API Key，一个不需要。

```
                         需要 API Key                     不 需 要
  ┌────────────────┐  ┌──────────────────────┐  ┌────────────────────┐
  │ DeepSeek V4    │  │ DashScope（通义千问）  │  │ BGE Reranker V2   │
  │ 问答主力模型    │  │ 多模态看图备用         │  │ 精排模型           │
  │ 月均 ¥5-20     │  │ 月均 < ¥1             │  │ 免费，本地跑       │
  │ sk-开头的Key    │  │ sk-开头的Key           │  │ 自动下载(~500MB)   │
  └────────────────┘  └──────────────────────┘  └────────────────────┘
```

---

## 1️⃣ DeepSeek API Key（主力模型 ✅ 已配置）

**用途**：所有纯文本对话都用 DeepSeek V4，是日常跑得最多的模型。

**获取步骤**：

```
① 打开 https://platform.deepseek.com/
② 点击右上角「登录」→ 用邮箱/手机号注册
③ 登录后进入「API Keys」页面
④ 点击「创建 API Key」
⑤ 复制生成的 sk-... 开头的密钥
```

**填入 `.env` 文件**：
```env
DEEPSEEK_API_KEY=sk-你复制的那一串
LLM_MODEL=deepseek-chat
```

**费用参考**（2026年）：
| 项目 | 价格 |
|-----|------|
| 输入（对话/文档） | ¥2/百万 token |
| 输出（生成的回答） | ¥8/百万 token |
| 一个普通问答 | ≈ 2000 token，约 ¥0.01 |
| 1000 次问答 | ≈ ¥10 |

---

## 2️⃣ DashScope API Key（多模态看图）

**用途**：只有用户上传图片/问流程图时才用到。纯文本对话用 DeepSeek，**不走这个路径就不花钱**。

**获取步骤**：

```
① 打开 https://help.aliyun.com/zh/dashscope/
② 用阿里云账号登录（支付宝账号可以直接登）
③ 进入「模型广场」→ 找到「通义千问-VL-Plus」
④ 点击「立即开通」
⑤ 在「API Key 管理」中创建 Key
```

**填入 `.env` 文件**：
```env
DASHSCOPE_API_KEY=sk-你复制的那一串
```

**费用参考**：
| 项目 | 价格 |
|-----|------|
| Qwen-VL-Plus 图片分析 | ¥0.008/张 （即 8 厘/张） |
| text-embedding-v3 文本嵌入 | ¥0.0007/千 token ≈ 百万级数据几毛钱 |

**注意事项**：
- DashScope 有 **免费额度**（开通即送百万 token），一般够用很久
- 如果只是纯文本问答，完全不配 DashScope 也能跑（DeepSeek 不需要它）
- 嵌入模型（text-embedding-v3）也走 DashScope，这个必须配——但极其便宜

---

## 3️⃣ BGE Reranker（无需 API Key，本地运行）

**用途**：对检索结果进行精排。把 Top-20 候选压缩到 Top-3，提升回答质量、节省 LLM token。

| 项目 | 说明 |
|-----|------|
| 模型 | BAAI/bge-reranker-v2-m3 |
| 大小 | ~500MB |
| 运行方式 | CPU（不需要 GPU） |
| 首次加载 | 自动从 HuggingFace 下载，受网络影响 |
| 后续使用 | HuggingFace 缓存，加载约 3-5 秒 |

**首次启动时如果下载慢**：
```bash
# 方法 1：设置国内镜像（推荐）
export HF_ENDPOINT=https://hf-mirror.com

# 方法 2：手动下载后放入缓存目录
# 模型文件在 ~/.cache/huggingface/hub/models--BAAI--bge-reranker-v2-m3/
```

**如果网络实在不好**：在 `.env` 中关闭精排即可，系统降级为普通混合检索：
```env
RETRIEVAL_USE_RERANK=false
```

---

## 最终 `.env` 配置

```env
# 必须配
DEEPSEEK_API_KEY=sk-你获取的key
LLM_MODEL=deepseek-chat

# 建议配（嵌入用，极便宜）
DASHSCOPE_API_KEY=sk-你获取的key

# 可选配（网络不好时关闭）
RETRIEVAL_USE_RERANK=true
```

---

## 验证方法

启动后端后，调用健康检查端点验证配置：

```bash
# 检查所有模型状态
curl http://localhost:8000/api/health
```

正常返回应包含：
```json
{
  "status": "ok",
  "models": {
    "chat": "deepseek-chat (DeepSeek V4)",
    "embedding": "text-embedding-v3 (DashScope)",
    "reranker": "BAAI/bge-reranker-v2-m3 (CPU, ready)",
    "vision": "qwen-vl-plus (DashScope, 可选)"
  }
}
```
