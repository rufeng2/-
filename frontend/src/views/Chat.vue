<template>
  <div class="chat-layout">
    <!-- 侧边栏 -->
    <div class="sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="sidebar-header">
        <h3>📚 知识库</h3>
        <el-button text @click="newConversation">
          <el-icon><Plus /></el-icon>
          新对话
        </el-button>
      </div>

      <div class="conversation-list">
        <div
          v-for="conv in conversations"
          :key="conv.id"
          class="conv-item"
          :class="{ active: conv.id === currentConvId }"
          @click="switchConversation(conv.id)"
        >
          <div class="conv-title">{{ conv.title }}</div>
          <div class="conv-time">{{ formatTime(conv.updated_at) }}</div>
          <el-button
            text
            type="danger"
            size="small"
            class="conv-delete"
            @click.stop="deleteConv(conv.id)"
          >
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
      </div>

      <div class="sidebar-footer">
        <span>{{ authStore.username }}</span>
        <el-button text @click="logout">退出</el-button>
      </div>
    </div>

    <!-- 主聊天区 -->
    <div class="chat-main">
      <div class="messages" ref="messagesRef">
        <div v-if="messages.length === 0" class="empty-state">
          <div class="empty-icon">📚</div>
          <h3>企业知识库智能问答</h3>
          <p>上传文档后，我可以帮你回答关于企业制度、流程、产品的问题</p>
        </div>

        <div
          v-for="msg in messages"
          :key="msg.id"
          class="message"
          :class="msg.role"
        >
          <div class="avatar">{{ msg.role === 'user' ? '👤' : '🤖' }}</div>
          <div class="bubble">
            <div v-if="msg.images?.length" class="message-images">
              <img v-for="image in msg.images" :key="image.id" :src="image.url" :alt="image.name" />
            </div>
            <div class="content markdown-body" v-html="renderMarkdown(msg.content)"></div>
            <div v-if="msg.references && msg.references.length" class="references">
              <div class="ref-title">📎 参考来源</div>
              <button v-for="(ref, i) in msg.references" :key="i" class="ref-item" @click="openReference(ref)">
                <span class="ref-badge">{{ i + 1 }}</span>
                <img v-if="ref.preview_url" :src="ref.preview_url" class="ref-preview" alt="引用图片预览" />
                <span>《{{ ref.title }}》<small v-if="ref.page">第 {{ ref.page }} 页</small></span>
              </button>
            </div>
            <div v-if="msg.role === 'assistant'" class="msg-actions">
              <el-button text size="small" @click="copyAnswer(msg.content)"><el-icon><CopyDocument /></el-icon>复制</el-button>
              <el-button text size="small" @click="regenerate"><el-icon><RefreshRight /></el-icon>重新生成</el-button>
              <el-button
                text
                size="small"
                :type="msg.feedback === 1 ? 'primary' : 'default'"
                @click="feedback(msg, 1)"
              >
                👍 有用
              </el-button>
              <el-button
                text
                size="small"
                :type="msg.feedback === -1 ? 'danger' : 'default'"
                @click="feedback(msg, -1)"
              >
                👎 没用
              </el-button>
            </div>
          </div>
        </div>

        <!-- 加载中 -->
        <div v-if="loading" class="message assistant">
          <div class="avatar">🤖</div>
          <div class="bubble">
            <div class="typing-indicator">
              <span></span><span></span><span></span>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入框 -->
      <div class="chat-tools">
        <el-select
          v-model="selectedKnowledgeBases"
          multiple
          collapse-tags
          placeholder="全部可访问知识库"
        >
          <el-option v-for="item in knowledgeBases" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>
        <el-upload :show-file-list="false" :auto-upload="true" :http-request="uploadChatImage" accept="image/*" :disabled="loading || pendingImages.length >= 3">
          <el-button :disabled="loading || pendingImages.length >= 3"><el-icon><Picture /></el-icon>添加图片</el-button>
        </el-upload>
        <el-button :disabled="!inputText.trim()" @click="debugRetrieval">
          <el-icon><Search /></el-icon>
          检索调试
        </el-button>
      </div>
      <div v-if="pendingImages.length" class="pending-images">
        <div v-for="image in pendingImages" :key="image.id" class="pending-image">
          <img :src="image.url" :alt="image.name" />
          <span>{{ image.name }}</span>
          <button type="button" title="移除图片" @click="removePendingImage(image.id)">×</button>
        </div>
      </div>
      <div class="input-area">
        <el-input
          v-model="inputText"
          type="textarea"
          :rows="2"
          placeholder="输入你的问题..."
          @keydown.enter.prevent="sendMessage"
          :disabled="loading"
        />
        <el-button
          v-if="!loading"
          type="primary"
          @click="sendMessage"
          class="send-btn"
        >
          <el-icon><Promotion /></el-icon>
          发送
        </el-button>
        <el-button v-else type="danger" plain class="send-btn" @click="stopGeneration">停止</el-button>
      </div>
    </div>
  </div>

  <el-dialog v-model="debugVisible" title="检索调试" width="820px">
    <div class="debug-query">问题：{{ debugQuery }}</div>
    <div v-if="debugRewrittenQuery !== debugQuery" class="debug-query">改写后：{{ debugRewrittenQuery }}</div>
    <el-table :data="debugItems" max-height="520">
      <el-table-column prop="rank" label="#" width="48" />
      <el-table-column prop="document_title" label="文档" width="160" />
      <el-table-column prop="search_type" label="召回" width="110" />
      <el-table-column label="分数" width="90">
        <template #default="{ row }">{{ Number(row.score || 0).toFixed(4) }}</template>
      </el-table-column>
      <el-table-column prop="page" label="页" width="55" />
      <el-table-column prop="snippet" label="命中内容" min-width="300" show-overflow-tooltip />
    </el-table>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from "vue"
import { useRouter } from "vue-router"
import { ElMessage, ElMessageBox } from "element-plus"
import { Plus, Delete, Promotion, Search, Picture, CopyDocument, RefreshRight } from "@element-plus/icons-vue"
import { marked } from "marked"
import { useAuthStore } from "@/store/auth"
import { chatAPI, documentAPI, knowledgeBaseAPI } from "@/api/client"

const router = useRouter()
const authStore = useAuthStore()

const sidebarCollapsed = ref(false)
const messages = ref<any[]>([])
const conversations = ref<any[]>([])
const currentConvId = ref("")
const inputText = ref("")
const loading = ref(false)
const messagesRef = ref<HTMLElement | null>(null)
const knowledgeBases = ref<any[]>([])
const selectedKnowledgeBases = ref<string[]>([])
const debugVisible = ref(false)
const debugItems = ref<any[]>([])
const debugQuery = ref("")
const debugRewrittenQuery = ref("")
const pendingImages = ref<any[]>([])
const abortController = ref<AbortController | null>(null)

onMounted(() => {
  loadConversations()
  loadKnowledgeBases()
})

async function loadKnowledgeBases() {
  try {
    const res = await knowledgeBaseAPI.list()
    knowledgeBases.value = res.data.data || []
  } catch {
    knowledgeBases.value = []
  }
}

async function debugRetrieval() {
  const question = inputText.value.trim()
  if (!question) return
  try {
    const res = await chatAPI.debug(question, selectedKnowledgeBases.value, currentConvId.value)
    debugQuery.value = question
    debugRewrittenQuery.value = res.data.data?.rewritten_query || question
    debugItems.value = res.data.data?.items || []
    debugVisible.value = true
  } catch {
    ElMessage.error("检索调试失败")
  }
}

async function openReference(ref: any) {
  if (!ref.document_id) {
    ElMessage.warning("旧引用没有原文定位信息")
    return
  }
  try {
    const res = await documentAPI.content(ref.document_id)
    const url = URL.createObjectURL(res.data)
    window.open(url + (ref.page ? "#page=" + ref.page : ""), "_blank")
    window.setTimeout(() => URL.revokeObjectURL(url), 60000)
  } catch {
    ElMessage.error("无法打开原文")
  }
}
async function loadConversations() {
  try {
    const res = await chatAPI.getConversations()
    conversations.value = res.data.data || []
  } catch {
    // ignore
  }
}

async function newConversation() {
  currentConvId.value = ""
  messages.value = []
}

function switchConversation(id: string) {
  currentConvId.value = id
  loadHistory(id)
}

async function loadHistory(convId: string) {
  try {
    const res = await chatAPI.getHistory(convId)
    messages.value = res.data.data || []
    scrollToBottom()
  } catch {
    messages.value = []
  }
}

async function uploadChatImage(options: any) {
  try {
    const response = await chatAPI.uploadImage(options.file)
    if (response.data.code !== 200) throw new Error(response.data.msg)
    pendingImages.value.push({
      id: response.data.data.image_id,
      name: response.data.data.name,
      url: URL.createObjectURL(options.file),
    })
  } catch (error: any) {
    ElMessage.error(error.response?.data?.msg || error.message || "图片上传失败")
  }
}

function removePendingImage(id: string) {
  const image = pendingImages.value.find(item => item.id === id)
  if (image?.url) URL.revokeObjectURL(image.url)
  pendingImages.value = pendingImages.value.filter(item => item.id !== id)
}

async function hydrateReferenceImages(references: any[]) {
  await Promise.all(references.filter(ref => ref.has_image).map(async ref => {
    try {
      const response = await documentAPI.chunkImage(ref.document_id, ref.chunk_id)
      ref.preview_url = URL.createObjectURL(response.data)
    } catch {
      ref.preview_url = ""
    }
  }))
}
async function sendMessage() {
  const text = inputText.value.trim()
  if ((!text && !pendingImages.value.length) || loading.value) return
  const question = text || "请分析上传的图片"
  const attachments = [...pendingImages.value]

  // 添加用户消息
  const userMsg = { id: Date.now().toString(), role: "user", content: question, images: attachments }
  messages.value.push(userMsg)
  inputText.value = ""
  pendingImages.value = []
  loading.value = true
  scrollToBottom()

  try {
    // 使用 fetch 处理 SSE 流
    const token = localStorage.getItem("token")
    abortController.value = new AbortController()
    const resp = await fetch("/api/chat/send", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      signal: abortController.value.signal,
      body: JSON.stringify({
        question,
        conversation_id: currentConvId.value,
        knowledge_base_ids: selectedKnowledgeBases.value,
        image_ids: attachments.map(item => item.id),
      }),
    })

    if (!resp.ok) throw new Error(resp.statusText)

    const reader = resp.body?.getReader()
    if (!reader) throw new Error("No response body")

    const decoder = new TextDecoder()
    let assistantMsg: any = { id: "", role: "assistant", content: "", references: [], feedback: 0 }
    let eventBuffer = ""

    const handleEvent = async (event: string) => {
      const dataLines = event.split(/\r?\n/).filter(line => line.startsWith("data:"))
      if (!dataLines.length) return
      const payload = dataLines.map(line => line.slice(5).trimStart()).join("\n")
      const data = JSON.parse(payload)
      if (data.done) {
        assistantMsg.id = data.message_id || Date.now().toString()
        currentConvId.value = data.conversation_id || ""
        assistantMsg.references = data.references || []
        await hydrateReferenceImages(assistantMsg.references)
        const streamingIdx = messages.value.findIndex(m => m.id === "streaming")
        if (streamingIdx >= 0) messages.value[streamingIdx] = { ...assistantMsg }
        else messages.value.push({ ...assistantMsg })
        loadConversations()
      } else if (data.token) {
        assistantMsg.content += data.token
        const idx = messages.value.findIndex(m => m.id === "streaming")
        if (idx >= 0) messages.value[idx].content = assistantMsg.content
        else messages.value.push({ ...assistantMsg, id: "streaming" })
        scrollToBottom()
      } else if (data.error) {
        ElMessage.error(data.error)
      }
    }

    while (true) {
      const { done, value } = await reader.read()
      eventBuffer += decoder.decode(value || new Uint8Array(), { stream: !done })
      let boundary = eventBuffer.search(/\r?\n\r?\n/)
      while (boundary >= 0) {
        const event = eventBuffer.slice(0, boundary)
        const separator = eventBuffer.slice(boundary).match(/^\r?\n\r?\n/)?.[0] || "\n\n"
        eventBuffer = eventBuffer.slice(boundary + separator.length)
        if (event.trim()) await handleEvent(event)
        boundary = eventBuffer.search(/\r?\n\r?\n/)
      }
      if (done) break
    }
    if (eventBuffer.trim()) await handleEvent(eventBuffer)


  } catch (e: any) {
    ElMessage.error("发送失败: " + (e.message || "未知错误"))
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

function stopGeneration() {
  abortController.value?.abort()
}

async function copyAnswer(content: string) {
  await navigator.clipboard.writeText(content)
  ElMessage.success("答案已复制")
}

function regenerate() {
  const lastQuestion = [...messages.value].reverse().find(item => item.role === "user")
  if (!lastQuestion || loading.value) return
  inputText.value = lastQuestion.content
  sendMessage()
}
async function deleteConv(id: string) {
  try {
    await ElMessageBox.confirm("确定删除此对话？", "确认")
    await chatAPI.deleteConversation(id)
    if (currentConvId.value === id) {
      currentConvId.value = ""
      messages.value = []
    }
    loadConversations()
    ElMessage.success("删除成功")
  } catch {
    // user cancelled
  }
}

async function feedback(msg: any, rating: number) {
  if (!msg.id) return
  try {
    await chatAPI.submitFeedback(msg.id, rating)
    msg.feedback = rating
    ElMessage.success("感谢反馈")
  } catch {
    ElMessage.error("反馈失败")
  }
}

function renderMarkdown(text: string) {
  if (!text) return ""
  const cleaned = text
    .replace(/\n+(?:\*\*)?📎?\s*参考来源(?:\*\*)?[：:]?[\s\S]*$/u, "")
    .trim()
  return marked(cleaned) as string
}

function formatTime(dateStr: string) {
  if (!dateStr) return ""
  const d = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${d.getHours()}:${String(d.getMinutes()).padStart(2, "0")}`
  return `${d.getMonth() + 1}/${d.getDate()}`
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

function logout() {
  authStore.logout()
  router.push("/")
}
</script>

<style scoped>
.chat-layout {
  display: flex;
  height: 100%;
  overflow: hidden;
}

/* 侧边栏 */
.sidebar {
  width: 280px;
  min-width: 280px;
  background: #f0f2f5;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #e4e7ed;
}

.sidebar-header {
  padding: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #e4e7ed;
}

.sidebar-header h3 {
  font-size: 16px;
  font-weight: 600;
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.conv-item {
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  position: relative;
  margin-bottom: 4px;
  transition: background 0.2s;
}

.conv-item:hover, .conv-item.active {
  background: #e4e7ed;
}

.conv-title {
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding-right: 20px;
}

.conv-time {
  font-size: 12px;
  color: #909399;
}

.conv-delete {
  position: absolute;
  right: 4px;
  top: 50%;
  transform: translateY(-50%);
  opacity: 0;
}

.conv-item:hover .conv-delete {
  opacity: 1;
}

.sidebar-footer {
  padding: 12px 16px;
  border-top: 1px solid #e4e7ed;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: #606266;
}

/* 主聊天区 */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #909399;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.empty-state h3 {
  font-size: 20px;
  color: #303133;
  margin-bottom: 8px;
}

/* 消息气泡 */
.message {
  display: flex;
  margin-bottom: 20px;
  gap: 12px;
}

.message.user {
  flex-direction: row-reverse;
}

.avatar {
  font-size: 32px;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.bubble {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.6;
}

.user .bubble {
  background: #409eff;
  color: white;
  border-bottom-right-radius: 4px;
}

.assistant .bubble {
  background: white;
  border: 1px solid #e4e7ed;
  border-bottom-left-radius: 4px;
}

.message-images { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 8px; }
.message-images img { width: 160px; height: 120px; object-fit: cover; border: 1px solid #dcdfe6; }
.pending-images { display: flex; gap: 8px; padding: 8px 24px 0; background: #fff; }
.pending-image { display: grid; grid-template-columns: 42px minmax(0, 130px) 24px; align-items: center; gap: 7px; border: 1px solid #dcdfe6; padding: 5px; font-size: 12px; }
.pending-image img { width: 42px; height: 42px; object-fit: cover; }
.pending-image span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pending-image button { border: 0; background: transparent; cursor: pointer; font-size: 18px; }
.ref-preview { width: 52px; height: 40px; object-fit: cover; border: 1px solid #dcdfe6; }
.ref-item small { display: block; color: #909399; }
.references {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #e4e7ed;
}

.ref-title {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}

.ref-item {
  font-size: 12px;
  margin-bottom: 2px;
}

.ref-badge {
  display: inline-block;
  background: #ecf5ff;
  color: #409eff;
  padding: 0 4px;
  border-radius: 3px;
  margin-right: 4px;
  font-size: 11px;
}

.msg-actions {
  margin-top: 8px;
  display: flex;
  gap: 8px;
}

/* 输入区域 */
.input-area {
  padding: 16px 24px;
  background: white;
  border-top: 1px solid #e4e7ed;
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.input-area .el-textarea {
  flex: 1;
}

.send-btn {
  height: 60px;
  width: 100px;
}

/* 打字指示器 */
.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 4px 0;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background: #909399;
  border-radius: 50%;
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
  0%, 60%, 100% { opacity: 0.3; transform: translateY(0); }
  30% { opacity: 1; transform: translateY(-4px); }
}

.chat-tools {
  padding: 10px 24px 0;
  background: white;
  display: flex;
  gap: 10px;
}
.chat-tools .el-select { width: 280px; }
.ref-item {
  display: block;
  border: 0;
  background: transparent;
  padding: 3px 0;
  cursor: pointer;
  color: #337ecc;
  text-align: left;
}
.ref-item:hover { text-decoration: underline; }
.debug-query { margin-bottom: 12px; color: #606266; }
</style>

<style scoped>
@media (max-width: 760px) {
  .chat-layout { min-height: calc(100vh - 50px); }
  .sidebar { display: none; }
  .messages { padding: 14px 12px; }
  .bubble { max-width: calc(100% - 44px); }
  .chat-tools { padding: 8px 12px 0; flex-wrap: wrap; }
  .chat-tools .el-select { width: 100%; }
  .pending-images { padding: 8px 12px 0; overflow-x: auto; }
  .input-area { padding: 12px; }
  .send-btn { width: 64px; }
}
</style>