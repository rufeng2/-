<template>
  <section class="page-surface">
    <div class="page-heading">
      <div>
        <h1>运营知识库</h1>
        <p>沉淀商品资料、品牌规则、活动复盘和客服 SOP，为运营 Agent 提供可检索资料。</p>
      </div>
      <div class="toolbar-row">
        <el-button v-if="canWrite" @click="kbDialogVisible = true"><el-icon><FolderAdd /></el-icon>新建知识库</el-button>
        <el-upload
          :auto-upload="true"
          :http-request="uploadFile"
          :show-file-list="false"
          accept=".pdf,.docx,.xlsx,.pptx,.txt,.md,.csv,.jpg,.jpeg,.png,.bmp,.tiff"
        >
          <el-button type="primary" :disabled="!selectedKnowledgeBase"><el-icon><Upload /></el-icon>上传运营资料</el-button>
        </el-upload>
      </div>
    </div>

    <div class="panel knowledge-panel">
      <div class="toolbar-row filters">
        <el-select v-model="selectedKnowledgeBase" placeholder="选择运营知识库" @change="loadDocuments">
          <el-option v-for="item in knowledgeBases" :key="item.id" :label="item.name + ' (' + item.document_count + ')'" :value="item.id" />
        </el-select>
        <el-input v-model="searchText" clearable placeholder="搜索资料名称" :prefix-icon="Search" />
        <el-select v-model="statusFilter" clearable placeholder="全部状态">
          <el-option label="处理中" value="pending" />
          <el-option label="解析中" value="parsing" />
          <el-option label="已索引" value="indexed" />
          <el-option label="失败" value="failed" />
        </el-select>
      </div>

      <el-table :data="filteredDocuments" stripe v-loading="loading">
        <el-table-column prop="title" label="资料名称" min-width="220" />
        <el-table-column prop="knowledge_base_name" label="知识库" width="150" />
        <el-table-column prop="file_type" label="类型" width="80" />
        <el-table-column prop="status" label="状态" width="110">
          <template #default="{ row }"><el-tag :type="statusTag(row.status)">{{ statusText(row.status) }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="page_count" label="页/行" width="80" />
        <el-table-column prop="created_at" label="上传时间" width="180" />
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" @click="showChunks(row)">分块</el-button>
            <el-button v-if="canDelete" text type="danger" @click="deleteDoc(row.id)"><el-icon><Delete /></el-icon></el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="page-footer">
        <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total" layout="prev, pager, next" @current-change="loadDocuments" />
      </div>
    </div>

    <el-dialog v-model="kbDialogVisible" title="新建运营知识库" width="460px">
      <el-form label-position="top">
        <el-form-item label="名称"><el-input v-model="kbForm.name" placeholder="例如：大促活动复盘库" maxlength="120" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="kbForm.description" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="可见范围">
          <el-radio-group v-model="kbForm.visibility">
            <el-radio-button value="internal">团队内部</el-radio-button>
            <el-radio-button value="confidential">机密</el-radio-button>
            <el-radio-button value="public">公开</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="kbDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createKnowledgeBase">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="chunksVisible" :title="chunkDocumentTitle" width="820px">
      <div class="chunk-summary">共 {{ chunkTotal }} 个分块</div>
      <div class="chunk-list">
        <section v-for="item in chunks" :key="item.id" class="chunk-item">
          <div class="chunk-meta">
            <strong>#{{ item.chunk_index + 1 }}</strong>
            <span>{{ item.content.length }} 字符</span>
            <el-tag size="small" :type="item.has_embedding ? 'success' : 'warning'">{{ item.has_embedding ? "已向量化" : "无向量" }}</el-tag>
          </div>
          <pre>{{ item.content }}</pre>
        </section>
      </div>
      <el-pagination v-model:current-page="chunkPage" :page-size="10" :total="chunkTotal" layout="prev, pager, next" @current-change="loadChunks" />
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue"
import { ElMessage, ElMessageBox } from "element-plus"
import { Delete, FolderAdd, Search, Upload } from "@element-plus/icons-vue"
import { documentAPI, knowledgeBaseAPI } from "@/api/client"
import { useAuthStore } from "@/store/auth"

const auth = useAuthStore()
const documents = ref<any[]>([])
const searchText = ref("")
const statusFilter = ref("")
const loading = ref(false)
const knowledgeBases = ref<any[]>([])
const selectedKnowledgeBase = ref("")
const page = ref(1)
const pageSize = 20
const total = ref(0)
const kbDialogVisible = ref(false)
const kbForm = reactive({ name: "", description: "", visibility: "internal" })
const chunksVisible = ref(false)
const chunks = ref<any[]>([])
const chunkTotal = ref(0)
const chunkPage = ref(1)
const chunkDocumentId = ref("")
const chunkDocumentTitle = ref("")

const canWrite = computed(() => ["admin", "editor", "user"].includes(auth.role))
const canDelete = computed(() => ["admin", "editor"].includes(auth.role))
const filteredDocuments = computed(() => documents.value.filter(item => (!searchText.value || item.title.toLowerCase().includes(searchText.value.toLowerCase())) && (!statusFilter.value || item.status === statusFilter.value)))

onMounted(async () => {
  await loadKnowledgeBases()
  await loadDocuments()
})

async function loadKnowledgeBases() {
  const res = await knowledgeBaseAPI.list()
  knowledgeBases.value = res.data.data || []
  if (!selectedKnowledgeBase.value && knowledgeBases.value.length) selectedKnowledgeBase.value = knowledgeBases.value[0].id
}

async function loadDocuments() {
  loading.value = true
  try {
    const res = await documentAPI.list(page.value, pageSize, "", selectedKnowledgeBase.value)
    documents.value = res.data.data?.items || []
    total.value = res.data.data?.total || 0
  } finally {
    loading.value = false
  }
}

async function createKnowledgeBase() {
  if (!kbForm.name.trim()) return ElMessage.warning("请输入知识库名称")
  const res = await knowledgeBaseAPI.create({ ...kbForm, name: kbForm.name.trim() })
  if (res.data.code === 200) {
    kbDialogVisible.value = false
    kbForm.name = ""
    kbForm.description = ""
    await loadKnowledgeBases()
    selectedKnowledgeBase.value = res.data.data.id
    await loadDocuments()
    ElMessage.success("运营知识库已创建")
  } else {
    ElMessage.error(res.data.msg)
  }
}

async function uploadFile(options: any) {
  try {
    const res = await documentAPI.upload(options.file, "internal", selectedKnowledgeBase.value, "general")
    if (res.data.code === 200) {
      ElMessage.success(res.data.msg || "资料已上传，正在建立索引")
      await loadKnowledgeBases()
      await loadDocuments()
    } else {
      ElMessage.error(res.data.msg || "任务提交失败")
    }
  } catch (error: any) {
    ElMessage.error(error.response?.data?.msg || "上传失败")
  }
}

async function showChunks(row: any) {
  chunkDocumentId.value = row.id
  chunkDocumentTitle.value = row.title + " - 分块预览"
  chunkPage.value = 1
  chunksVisible.value = true
  await loadChunks()
}

async function loadChunks() {
  const res = await documentAPI.chunks(chunkDocumentId.value, chunkPage.value, 10)
  chunks.value = res.data.data?.items || []
  chunkTotal.value = res.data.data?.total || 0
}

async function deleteDoc(id: string) {
  try {
    await ElMessageBox.confirm("删除后将移除原文和向量，是否继续？", "删除资料")
    const res = await documentAPI.delete(id)
    if (res.data.code === 200) {
      ElMessage.success("删除成功")
      await loadKnowledgeBases()
      await loadDocuments()
    }
  } catch {
    // cancelled
  }
}

function statusTag(status: string) {
  return ({ pending: "info", parsing: "warning", indexed: "success", failed: "danger" } as any)[status] || "info"
}

function statusText(status: string) {
  return ({ pending: "待处理", parsing: "解析中", indexed: "已完成", failed: "失败" } as any)[status] || status
}
</script>

<style scoped>
.knowledge-panel{padding:16px}.filters{margin-bottom:14px}.filters .el-select{width:190px}.filters .el-input{width:230px}.page-footer{display:flex;justify-content:center;margin-top:18px}.chunk-summary{color:var(--ink-muted);margin-bottom:12px}.chunk-list{max-height:58vh;overflow:auto}.chunk-item{border-top:1px solid var(--border);padding:12px 0}.chunk-meta{display:flex;gap:12px;align-items:center;color:var(--ink-muted);font-size:12px;margin-bottom:8px}.chunk-item pre{margin:0;white-space:pre-wrap;word-break:break-word;font:inherit;line-height:1.65}
@media(max-width:760px){.filters{align-items:stretch;flex-direction:column}.filters .el-select,.filters .el-input{width:100%}}
</style>
