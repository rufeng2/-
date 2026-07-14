<template>
  <div class="page-surface">
    <header class="page-heading"><div><h1>RAG 自动评测</h1><p>数据集、检索与回答指标、版本基线和回归诊断</p></div><div class="toolbar-row"><el-switch v-model="generateAnswers" active-text="生成回答"/><el-input-number v-model="runLimit" :min="1" :max="100"/><el-button type="primary" :loading="running" @click="runEvaluation"><el-icon><VideoPlay/></el-icon>开始评测</el-button></div></header>
    <el-alert type="info" :closable="false" show-icon title="检索命中率不等于回答正确率。开启生成回答后才会计算忠实度、答案相关性与幻觉率。" class="note"/>
    <section v-if="selectedRun" class="metric-grid">
      <div v-for="metric in metricCards" :key="metric.key" class="metric"><span>{{ metric.label }}</span><strong>{{ formatMetric(metric.key, selectedRun.metrics?.[metric.key]) }}</strong><small v-if="comparison?.delta?.[metric.key] !== undefined" :class="{bad:isBadDelta(metric.key,comparison.delta[metric.key])}">{{ deltaText(comparison.delta[metric.key]) }}</small></div>
    </section>
    <div v-if="selectedRun && ['pending','running'].includes(selectedRun.status)" class="panel progress"><span>后台评测中</span><el-progress :percentage="selectedRun.progress||0"/></div>
    <el-tabs v-model="tab" class="eval-tabs">
      <el-tab-pane label="评测数据集" name="dataset">
        <div class="tab-toolbar"><span>共 {{ items.length }} 条，{{ annotatedCount }} 条已标注标准答案</span><el-button type="primary" @click="openAdd"><el-icon><Plus/></el-icon>添加题目</el-button></div>
        <el-table :data="items" v-loading="loading" height="520"><el-table-column prop="category" label="类别" width="100"/><el-table-column prop="question" label="问题" min-width="260"/><el-table-column label="正确文档" min-width="180"><template #default="{row}">{{ (row.expected_document_titles||[]).join("、")||"待标注" }}</template></el-table-column><el-table-column prop="expected_answer" label="标准答案" min-width="240" show-overflow-tooltip/><el-table-column label="操作" width="105"><template #default="{row}"><el-button text @click="openEdit(row)"><el-icon><Edit/></el-icon></el-button><el-button text type="danger" @click="removeItem(row.id)"><el-icon><Delete/></el-icon></el-button></template></el-table-column></el-table>
      </el-tab-pane>
      <el-tab-pane label="版本历史" name="history">
        <div class="tab-toolbar"><span>选择历史版本查看指标或与生产基线比较</span><el-input v-model="baselineName" placeholder="基线名称" style="width:180px"/></div>
        <el-table :data="runs" height="520"><el-table-column prop="created_at" label="时间" width="190"/><el-table-column prop="sample_count" label="样本" width="80"/><el-table-column prop="status" label="状态" width="100"/><el-table-column label="命中率" width="100"><template #default="{row}">{{ formatMetric("retrieval_hit_rate",row.metrics?.retrieval_hit_rate) }}</template></el-table-column><el-table-column label="Recall@5" width="100"><template #default="{row}">{{ formatMetric("recall_at_5",row.metrics?.recall_at_5) }}</template></el-table-column><el-table-column label="标记" width="120"><template #default="{row}"><el-tag v-if="row.is_baseline" type="success">{{ row.baseline_name||"基线" }}</el-tag></template></el-table-column><el-table-column label="操作" min-width="210"><template #default="{row}"><el-button text @click="selectRun(row)">查看</el-button><el-button text :disabled="row.status!=='completed'" @click="saveBaseline(row)">设为基线</el-button><el-button text @click="compareRun(row)">对比</el-button></template></el-table-column></el-table>
      </el-tab-pane>
      <el-tab-pane label="逐题诊断" name="details">
        <el-table :data="selectedRun?.details||[]" height="520"><el-table-column prop="category" label="类别" width="90"/><el-table-column prop="question" label="问题" min-width="240"/><el-table-column label="命中" width="80"><template #default="{row}"><el-tag :type="row.retrieval_hit?'success':'danger'">{{ row.retrieval_hit?"是":"否" }}</el-tag></template></el-table-column><el-table-column label="R@5" width="80"><template #default="{row}">{{ row.recall_at_5?"是":"否" }}</template></el-table-column><el-table-column prop="generated_answer" label="生成答案" min-width="280" show-overflow-tooltip/></el-table>
      </el-tab-pane>
    </el-tabs>
    <el-dialog v-model="dialog" :title="editingId?'编辑评测题':'添加评测题'" width="560px"><el-form label-position="top"><el-form-item label="类别"><el-input v-model="form.category"/></el-form-item><el-form-item label="问题"><el-input v-model="form.question" type="textarea" :rows="3"/></el-form-item><el-form-item label="正确文档名（逗号分隔）"><el-input v-model="form.documents"/></el-form-item><el-form-item label="关键词（逗号分隔）"><el-input v-model="form.keywords"/></el-form-item><el-form-item label="人工标准答案"><el-input v-model="form.answer" type="textarea" :rows="4"/></el-form-item></el-form><template #footer><el-button @click="dialog=false">取消</el-button><el-button type="primary" @click="saveItem">保存</el-button></template></el-dialog>
  </div>
</template>
<script setup lang="ts">
import { computed,onMounted,reactive,ref } from "vue"
import { ElMessage,ElMessageBox } from "element-plus"
import { Delete,Edit,Plus,VideoPlay } from "@element-plus/icons-vue"
import { evaluationAPI,operationsAPI } from "@/api/client"
const items=ref<any[]>([]),runs=ref<any[]>([]),selectedRun=ref<any>(null),comparison=ref<any>(null),loading=ref(false),running=ref(false),runLimit=ref(20),generateAnswers=ref(true),tab=ref("dataset"),dialog=ref(false),editingId=ref(""),baselineName=ref("production")
const form=reactive({category:"通用",question:"",documents:"",keywords:"",answer:""})
const metricCards=[{key:"retrieval_hit_rate",label:"检索命中率"},{key:"recall_at_5",label:"Recall@5"},{key:"ndcg_at_10",label:"nDCG@10"},{key:"mrr",label:"MRR"},{key:"context_precision",label:"上下文精确率"},{key:"faithfulness",label:"答案忠实度"},{key:"answer_relevance",label:"答案相关性"},{key:"hallucination_rate",label:"幻觉率"}]
const annotatedCount=computed(()=>items.value.filter(x=>x.expected_answer).length)
onMounted(loadAll)
async function loadAll(){loading.value=true;try{const [a,b]=await Promise.all([evaluationAPI.items(),evaluationAPI.runs()]);items.value=a.data.data||[];runs.value=b.data.data||[];if(!selectedRun.value)selectedRun.value=runs.value[0]||null}finally{loading.value=false}}
async function runEvaluation(){running.value=true;try{const run=(await evaluationAPI.run(runLimit.value,generateAnswers.value)).data.data;selectedRun.value=run;tab.value="details";while(["pending","running"].includes(selectedRun.value?.status)){await new Promise(r=>setTimeout(r,1500));await loadAll();selectedRun.value=runs.value.find(x=>x.id===run.id)||selectedRun.value}ElMessage.success("评测已完成")}catch{ElMessage.error("评测任务失败")}finally{running.value=false}}
function selectRun(row:any){selectedRun.value=row;comparison.value=null;tab.value="details"}
async function saveBaseline(row:any){const r=await operationsAPI.setBaseline(row.id,baselineName.value||"production");if(r.data.code===200){ElMessage.success("基线已保存");await loadAll()}}
async function compareRun(row:any){try{comparison.value=(await operationsAPI.compare(row.id,baselineName.value||"production")).data.data;selectedRun.value=row;ElMessage.success("已加载与基线的差值")}catch{ElMessage.warning("请先为该名称保存一个基线")}}
function openAdd(){editingId.value="";Object.assign(form,{category:"通用",question:"",documents:"",keywords:"",answer:""});dialog.value=true}
function openEdit(row:any){editingId.value=row.id;Object.assign(form,{category:row.category,question:row.question,documents:(row.expected_document_titles||[]).join(","),keywords:(row.expected_keywords||[]).join(","),answer:row.expected_answer||""});dialog.value=true}
async function saveItem(){if(!form.question.trim())return ElMessage.warning("请输入问题");const payload={question:form.question,category:form.category,expected_answer:form.answer,expected_keywords:split(form.keywords),expected_document_titles:split(form.documents),expected_chunk_ids:[],expected_pages:[],enabled:true};if(editingId.value)await evaluationAPI.update(editingId.value,payload);else await evaluationAPI.create(payload);dialog.value=false;await loadAll()}
async function removeItem(id:string){await ElMessageBox.confirm("确认删除这条评测题？","确认");await evaluationAPI.delete(id);await loadAll()}
const split=(v:string)=>v.split(/[,，]/).map(x=>x.trim()).filter(Boolean)
const formatMetric=(key:string,v:any)=>v==null?"--":(["mrr","ndcg_at_10"].includes(key)?Number(v).toFixed(3):(Number(v)*100).toFixed(1)+"%")
const deltaText=(v:number)=>(v>=0?"+":"")+(v*100).toFixed(1)+"%"
const isBadDelta=(key:string,v:number)=>key==="hallucination_rate"?v>0:v<0
</script>
<style scoped>
.note{margin-bottom:14px}.metric-grid{display:grid;grid-template-columns:repeat(4,1fr);background:#fff;border:1px solid #e1e6e3;border-radius:7px;margin-bottom:16px}.metric{padding:16px 18px;border-right:1px solid #e7ebe9;border-bottom:1px solid #e7ebe9}.metric span,.metric small{display:block;font-size:12px;color:#667085}.metric strong{display:block;font-size:23px;margin:5px 0}.metric small{color:#168457}.metric small.bad{color:#d04444}.progress{padding:14px;margin-bottom:14px}.eval-tabs{background:#fff;border:1px solid #e1e6e3;border-radius:7px;padding:0 18px 18px}.tab-toolbar{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:12px;color:#667085;font-size:13px}@media(max-width:780px){.metric-grid{grid-template-columns:repeat(2,1fr)}.tab-toolbar{align-items:stretch;flex-direction:column}}
</style>