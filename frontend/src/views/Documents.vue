<template>
  <div class="documents-page">
    <header class="page-header">
      <div>
        <h2>文档与知识库</h2>
        <p>管理资料、切分方式和索引结果</p>
      </div>
      <div class="header-actions">
        <el-button v-if="canWrite" @click="kbDialogVisible = true">
          <el-icon><FolderAdd /></el-icon>
          新建知识库
        </el-button>
        <el-upload
          :auto-upload="true"
          :http-request="uploadFile"
          :show-file-list="false"
          accept=".pdf,.docx,.xlsx,.pptx,.txt,.md,.csv,.jpg,.jpeg,.png,.bmp,.tiff"
        >
          <el-button type="primary" :disabled="!selectedKnowledgeBase">
            <el-icon><Upload /></el-icon>
            上传文档
          </el-button>
        </el-upload>
      </div>
    </header>

    <div class="toolbar">
      <el-input v-model="searchText" clearable placeholder="搜索文件名" :prefix-icon="Search" />
      <el-select v-model="statusFilter" clearable placeholder="全部状态"><el-option label="处理中" value="pending"/><el-option label="解析中" value="parsing"/><el-option label="已完成" value="indexed"/><el-option label="失败" value="failed"/></el-select>
      <el-select v-model="selectedKnowledgeBase" placeholder="选择知识库" @change="loadDocuments">
        <el-option
          v-for="item in knowledgeBases"
          :key="item.id"
          :label="item.name + ' (' + item.document_count + ')'"
          :value="item.id"
        />
      </el-select>
      <el-segmented v-model="chunkTemplate" :options="templateOptions" />
      <span class="template-note">{{ templateDescription }}</span>
    </div>

    <el-table :data="filteredDocuments" stripe v-loading="loading">
      <el-table-column prop="title" label="文件名" min-width="220" />
      <el-table-column prop="knowledge_base_name" label="知识库" width="140" />
      <el-table-column prop="file_type" label="类型" width="80" />
      <el-table-column label="切分模板" width="100">
        <template #default="{ row }">{{ templateLabel(row.chunk_template) }}</template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tooltip :content="row.error_message || ''" :disabled="!row.error_message">
            <el-tag :type="statusTag(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
          </el-tooltip>
        </template>
      </el-table-column>
      <el-table-column prop="page_count" label="页/表" width="70" />
      <el-table-column label="清洗质量" width="100">
        <template #default="{ row }">
          <el-tooltip :content="qualitySummary(row.quality_report)" placement="top">
            <el-tag :type="qualityTag(row.quality_report)" size="small">
              {{ qualityText(row.quality_report) }}
            </el-tag>
          </el-tooltip>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="上传时间" width="175" />
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" @click="showChunks(row)">
            <el-icon><View /></el-icon>分块
          </el-button>
          <el-dropdown v-if="canWrite" @command="(command: string) => reindexDoc(row, command)">
            <el-button text>
              <el-icon><Refresh /></el-icon>重切
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item v-for="option in templateOptions" :key="option.value" :command="option.value">
                  {{ option.label }}
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <el-button v-if="canDelete" text type="danger" @click="deleteDoc(row.id)">
            <el-icon><Delete /></el-icon>
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="page-footer">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        @current-change="loadDocuments"
      />
    </div>

    <el-dialog v-model="kbDialogVisible" title="新建知识库" width="460px">
      <el-form label-position="top">
        <el-form-item label="名称">
          <el-input v-model="kbForm.name" placeholder="例如：保险产品库" maxlength="120" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="kbForm.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="可见范围">
          <el-radio-group v-model="kbForm.visibility">
            <el-radio-button value="internal">企业内部</el-radio-button>
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
      <div class="chunk-summary">
        共 {{ chunkTotal }} 个分块，模板：{{ templateLabel(chunkDocumentTemplate) }}
      </div>
      <div v-if="chunkQualityReport.quality_score !== undefined" class="quality-detail">
        <strong>清洗质量 {{ qualityText(chunkQualityReport) }}</strong>
        <span>内容保留 {{ percent(chunkQualityReport.retained_ratio) }}</span>
        <span>去除噪声 {{ chunkQualityReport.removed_noise_lines || 0 }} 行</span>
        <span>去除重复块 {{ chunkQualityReport.duplicate_chunks || 0 }} 个</span>
        <span v-if="chunkQualityReport.visual_chunks">视觉解析 {{ chunkQualityReport.vision_analyzed || 0 }}/{{ chunkQualityReport.visual_chunks }} 个</span>
        <el-tag v-for="warning in chunkQualityReport.warnings || []" :key="warning" size="small" type="warning">
          {{ warning }}
        </el-tag>
      </div>
      <div class="chunk-list">
        <section v-for="item in chunks" :key="item.id" class="chunk-item">
          <div class="chunk-meta">
            <strong>#{{ item.chunk_index + 1 }}</strong>
            <span v-if="item.metadata?.page">第 {{ item.metadata.page }} 页</span>
            <span v-if="item.metadata?.sheet">工作表：{{ item.metadata.sheet }}</span>
            <span>{{ item.content.length }} 字符</span>
            <el-tag size="small" :type="item.has_embedding ? 'success' : 'warning'">
              {{ item.has_embedding ? "已向量化" : "无向量" }}
            </el-tag>
          </div>
          <pre>{{ item.content }}</pre>
        </section>
      </div>
      <el-pagination
        v-model:current-page="chunkPage"
        :page-size="10"
        :total="chunkTotal"
        layout="prev, pager, next"
        @current-change="loadChunks"
      />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from "vue"
import { ElMessage, ElMessageBox } from "element-plus"
import { Delete, FolderAdd, Refresh, Search, Upload, View } from "@element-plus/icons-vue"
import { documentAPI, knowledgeBaseAPI } from "@/api/client"
import { useAuthStore } from "@/store/auth"

const auth = useAuthStore()
const documents = ref<any[]>([])
const searchText = ref("")
const statusFilter = ref("")
const loading = ref(false)
const canWrite = computed(() => ["admin", "editor", "user"].includes(auth.role))
const canDelete = computed(() => ["admin", "editor"].includes(auth.role))
const filteredDocuments = computed(() => documents.value.filter(item => (!searchText.value || item.title.toLowerCase().includes(searchText.value.toLowerCase())) && (!statusFilter.value || item.status === statusFilter.value)))
const knowledgeBases = ref<any[]>([])
const selectedKnowledgeBase = ref("")
const chunkTemplate = ref("general")
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
const chunkDocumentTemplate = ref("general")
const chunkQualityReport = ref<any>({})

const templateOptions = [
  { label: "通用", value: "general" },
  { label: "短句", value: "sentence" },
  { label: "表格", value: "table" },
  { label: "问答", value: "qa" },
]

const templateDescription = computed(() => ({
  general: "适合制度、合同和普通文档",
  sentence: "适合条款和短句精确检索",
  table: "适合 Excel 和结构化数据",
  qa: "适合常见问题与培训材料",
}[chunkTemplate.value] || ""))

let statusTimer: number | undefined
onMounted(async () => {
  await loadKnowledgeBases()
  await loadDocuments()
  statusTimer = window.setInterval(() => {
    if (documents.value.some(item => ["pending", "parsing"].includes(item.status))) loadDocuments()
  }, 3000)
})
onUnmounted(() => { if (statusTimer) window.clearInterval(statusTimer) })

async function loadKnowledgeBases() {
  const res = await knowledgeBaseAPI.list()
  knowledgeBases.value = res.data.data || []
  if (!selectedKnowledgeBase.value && knowledgeBases.value.length) {
    selectedKnowledgeBase.value = knowledgeBases.value[0].id
  }
}

async function loadDocuments() {
  try {
    const res = await documentAPI.list(page.value, pageSize, "", selectedKnowledgeBase.value)
    documents.value = res.data.data?.items || []
    total.value = res.data.data?.total || 0
  } catch {
    documents.value = []
  }
}

async function createKnowledgeBase() {
  if (!kbForm.name.trim()) {
    ElMessage.warning("请输入知识库名称")
    return
  }
  const res = await knowledgeBaseAPI.create({ ...kbForm, name: kbForm.name.trim() })
  if (res.data.code === 200) {
    kbDialogVisible.value = false
    kbForm.name = ""
    kbForm.description = ""
    await loadKnowledgeBases()
    selectedKnowledgeBase.value = res.data.data.id
    await loadDocuments()
    ElMessage.success("知识库创建成功")
  } else {
    ElMessage.error(res.data.msg)
  }
}

async function uploadFile(options: any) {
  try {
    const res = await documentAPI.upload(
      options.file,
      "internal",
      selectedKnowledgeBase.value,
      chunkTemplate.value,
    )
    if (res.data.code === 200) {
      ElMessage.success(res.data.msg || "上传成功，正在后台建立索引")
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
  chunkDocumentTitle.value = row.title + " · 分块预览"
  chunkDocumentTemplate.value = row.chunk_template
  chunkPage.value = 1
  chunksVisible.value = true
  await loadChunks()
}

async function loadChunks() {
  const res = await documentAPI.chunks(chunkDocumentId.value, chunkPage.value, 10)
  chunks.value = res.data.data?.items || []
  chunkTotal.value = res.data.data?.total || 0
  chunkQualityReport.value = res.data.data?.document?.quality_report || {}
}

async function reindexDoc(row: any, template: string) {
  await ElMessageBox.confirm("重新切分会替换现有分块和向量，是否继续？", "重新索引")
  const res = await documentAPI.reindex(row.id, template)
  if (res.data.code === 200) {
    ElMessage.success(res.data.msg || "已提交后台重新索引")
    loadDocuments()
  } else {
    ElMessage.error(res.data.msg)
  }
}

async function deleteDoc(id: string) {
  try {
    await ElMessageBox.confirm("删除后将同时移除原文和向量，是否继续？", "删除文档")
    const res = await documentAPI.delete(id)
    if (res.data.code === 200) {
      ElMessage.success("删除成功")
      await loadKnowledgeBases()
      loadDocuments()
    }
  } catch {
    // cancelled
  }
}

function templateLabel(value: string) {
  return templateOptions.find(item => item.value === value)?.label || value
}

function statusTag(status: string) {
  return ({ pending: "info", parsing: "warning", indexed: "success", failed: "danger" } as any)[status] || "info"
}

function statusText(status: string) {
  return ({ pending: "待处理", parsing: "解析中", indexed: "已完成", failed: "失败" } as any)[status] || status
}

function percent(value: unknown) {
  return typeof value === "number" ? `${Math.round(value * 100)}%` : "--"
}

function qualityText(report: any) {
  return typeof report?.quality_score === "number" ? percent(report.quality_score) : "待重建"
}

function qualityTag(report: any) {
  if (typeof report?.quality_score !== "number") return "info"
  if (report.quality_score >= 0.85) return "success"
  if (report.quality_score >= 0.65) return "warning"
  return "danger"
}

function qualitySummary(report: any) {
  if (typeof report?.quality_score !== "number") return "重建索引后生成清洗质量报告"
  return `保留 ${percent(report.retained_ratio)}，去噪 ${report.removed_noise_lines || 0} 行，去重 ${report.duplicate_chunks || 0} 块`
}
</script>

<style scoped>
.documents-page { padding: 24px; max-width: 1440px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; }
.page-header h2 { margin: 0; font-size: 22px; }
.page-header p { margin: 5px 0 0; color: #73767a; font-size: 13px; }
.header-actions, .toolbar { display: flex; align-items: center; gap: 10px; }
.toolbar { min-height: 54px; border-top: 1px solid #e4e7ed; border-bottom: 1px solid #e4e7ed; margin-bottom: 16px; }
.toolbar .el-select { width: 180px; }.toolbar .el-input { width: 210px; }
.template-note { color: #73767a; font-size: 13px; }
.page-footer { display: flex; justify-content: center; margin-top: 18px; }
.chunk-summary { color: #606266; margin-bottom: 12px; }
.quality-detail { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 14px; padding: 10px 12px; margin-bottom: 12px; background: #f5f7fa; border-left: 3px solid #409eff; color: #606266; font-size: 13px; }
.chunk-list { max-height: 58vh; overflow-y: auto; padding-right: 6px; }
.chunk-item { border-top: 1px solid #e4e7ed; padding: 12px 0; }
.chunk-meta { display: flex; gap: 12px; align-items: center; color: #73767a; font-size: 12px; margin-bottom: 8px; }
.chunk-item pre { margin: 0; white-space: pre-wrap; word-break: break-word; font: inherit; line-height: 1.65; color: #303133; }
</style>


<style scoped>
@media (max-width: 760px) {
  .documents-page { padding: 16px; }
  .page-header { align-items: stretch; flex-direction: column; }
  .header-actions { width: 100%; }
  .toolbar { align-items: stretch; flex-direction: column; padding: 12px 0; }
  .toolbar .el-select, .toolbar .el-input { width: 100%; }
  .template-note { line-height: 1.5; }
}
</style>