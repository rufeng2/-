<template>
  <div class="page-surface">
    <header class="page-heading"><div><h1>管理与运维</h1><p>用户权限、运行状态、操作审计与生产配置</p></div><el-button :loading="loading" @click="loadAll"><el-icon><Refresh /></el-icon>刷新</el-button></header>
    <section class="summary">
      <div v-for="item in summary" :key="item.label" class="summary-item"><span>{{ item.label }}</span><strong>{{ item.value }}</strong><small>{{ item.note }}</small></div>
    </section>
    <el-tabs v-model="tab" class="admin-tabs">
      <el-tab-pane label="运行概览" name="overview">
        <div class="two-column">
          <section class="panel block">
            <h3>服务状态</h3>
            <div class="health-line"><span><i class="status-dot"></i>API 服务</span><el-tag type="success">{{ health.status || "正常" }}</el-tag></div>
            <div class="health-line"><span>对话模型</span><b>{{ health.models?.chat || "--" }}</b></div>
            <div class="health-line"><span>重排模型</span><b>{{ health.models?.reranker?.model || "已配置" }}</b></div>
            <div class="health-line"><span>OIDC / LDAP</span><b>{{ sso.oidc ? "OIDC 已启用" : "OIDC 未启用" }} · {{ sso.ldap ? "LDAP 已启用" : "LDAP 未启用" }}</b></div>
          </section>
          <section class="panel block">
            <h3>生产保护</h3>
            <div class="capabilities">
              <el-tag v-for="item in capabilities" :key="item" effect="plain">{{ item }}</el-tag>
            </div>
            <p class="muted">备份、ClamAV、Grafana 与 OpenSearch 由 Docker profile 和运维脚本控制，页面仅展示应用侧状态。</p>
          </section>
        </div>
      </el-tab-pane>
      <el-tab-pane label="用户与角色" name="users">
        <div class="tab-toolbar"><el-input v-model="userSearch" placeholder="搜索用户名" clearable :prefix-icon="Search" /><el-button type="primary" @click="userDialog=true"><el-icon><Plus /></el-icon>新建用户</el-button></div>
        <el-table :data="filteredUsers" v-loading="loading">
          <el-table-column prop="username" label="用户名" min-width="130" /><el-table-column prop="display_name" label="显示名称" min-width="130" />
          <el-table-column label="角色" width="120"><template #default="{row}"><el-tag :type="roleTag(row.role)">{{ roleText(row.role) }}</el-tag></template></el-table-column>
          <el-table-column prop="department" label="部门" min-width="150" />
          <el-table-column label="状态" width="90"><template #default="{row}"><el-tag :type="row.is_active?'success':'danger'">{{ row.is_active?"启用":"禁用" }}</el-tag></template></el-table-column>
          <el-table-column label="操作" width="180"><template #default="{row}"><el-button text @click="toggleUser(row)">{{ row.is_active?"禁用":"启用" }}</el-button><el-button text type="danger" :disabled="row.username===auth.username" @click="removeUser(row)">删除</el-button></template></el-table-column>
        </el-table>
      </el-tab-pane>
      <el-tab-pane label="部门管理" name="departments">
        <div class="tab-toolbar"><span class="muted">部门用于知识库和文档的可见范围控制</span><el-button type="primary" @click="deptDialog=true"><el-icon><Plus /></el-icon>新建部门</el-button></div>
        <el-table :data="departments"><el-table-column prop="name" label="部门" /><el-table-column prop="description" label="说明" /><el-table-column width="100"><template #default="{row}"><el-button text type="danger" @click="removeDepartment(row)">删除</el-button></template></el-table-column></el-table>
      </el-tab-pane>
      <el-tab-pane label="操作审计" name="audit">
        <div class="tab-toolbar"><el-select v-model="auditAction" clearable placeholder="全部操作" @change="loadAudit"><el-option v-for="x in ['POST','PUT','PATCH','DELETE']" :key="x" :label="x" :value="x"/></el-select><span class="muted">最近 {{ audits.length }} 条写操作</span></div>
        <el-table :data="audits" height="520"><el-table-column prop="created_at" label="时间" width="185"/><el-table-column prop="username" label="操作者" width="130"/><el-table-column prop="action" label="方法" width="80"/><el-table-column prop="path" label="资源" min-width="280" show-overflow-tooltip/><el-table-column prop="status_code" label="状态" width="80"/><el-table-column prop="request_id" label="请求 ID" min-width="190" show-overflow-tooltip/></el-table>
      </el-tab-pane>
    </el-tabs>
    <el-dialog v-model="userDialog" title="新建用户" width="460px"><el-form label-position="top"><el-form-item label="用户名"><el-input v-model="userForm.username"/></el-form-item><el-form-item label="密码"><el-input v-model="userForm.password" type="password" show-password placeholder="至少 8 位"/></el-form-item><el-form-item label="显示名称"><el-input v-model="userForm.display_name"/></el-form-item><el-form-item label="角色"><el-select v-model="userForm.role"><el-option v-for="r in roles" :key="r.value" :label="r.label" :value="r.value"/></el-select></el-form-item></el-form><template #footer><el-button @click="userDialog=false">取消</el-button><el-button type="primary" @click="createUser">创建</el-button></template></el-dialog>
    <el-dialog v-model="deptDialog" title="新建部门" width="460px"><el-form label-position="top"><el-form-item label="部门名称"><el-input v-model="deptForm.name"/></el-form-item><el-form-item label="说明"><el-input v-model="deptForm.description" type="textarea"/></el-form-item></el-form><template #footer><el-button @click="deptDialog=false">取消</el-button><el-button type="primary" @click="createDepartment">创建</el-button></template></el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue"
import { ElMessage, ElMessageBox } from "element-plus"
import { Plus, Refresh, Search } from "@element-plus/icons-vue"
import { adminAPI, operationsAPI } from "@/api/client"
import { useAuthStore } from "@/store/auth"
const auth=useAuthStore(), tab=ref("overview"), loading=ref(false), users=ref<any[]>([]), departments=ref<any[]>([]), audits=ref<any[]>([]), stats=reactive<any>({}), health=reactive<any>({}), sso=reactive<any>({}), userSearch=ref(""), auditAction=ref(""), userDialog=ref(false), deptDialog=ref(false)
const roles=[{label:"系统管理员",value:"admin"},{label:"知识库编辑",value:"editor"},{label:"只读用户",value:"viewer"},{label:"普通用户",value:"user"}]
const userForm=reactive({username:"",password:"",display_name:"",department:"",role:"user"}),deptForm=reactive({name:"",description:""})
const filteredUsers=computed(()=>users.value.filter(x=>!userSearch.value||x.username.toLowerCase().includes(userSearch.value.toLowerCase())))
const summary=computed(()=>[{label:"用户",value:stats.users||0,note:"企业账号"},{label:"文档",value:stats.documents||0,note:(stats.indexed_documents||0)+" 已索引"},{label:"对话",value:stats.conversations||0,note:(stats.messages||0)+" 条消息"},{label:"反馈",value:stats.feedback_positive||0,note:(stats.feedback_negative||0)+" 条负向"}])
const capabilities=["请求限流","并发保护","写操作审计","密钥文件","数据保留","文件安全扫描","Prometheus 指标","评测基线"]
onMounted(loadAll)
async function loadAll(){loading.value=true;try{const [a,b,c,d,e]=await Promise.all([adminAPI.stats(),adminAPI.users(),adminAPI.departments(),operationsAPI.auditLogs(),operationsAPI.health()]);Object.assign(stats,a.data.data||{});users.value=b.data.data||[];departments.value=c.data.data||[];audits.value=d.data.data||[];Object.assign(health,e.data||{});try{Object.assign(sso,(await operationsAPI.ssoConfig()).data)}catch{}}finally{loading.value=false}}
async function loadAudit(){audits.value=(await operationsAPI.auditLogs(100,auditAction.value)).data.data||[]}
async function createUser(){if(userForm.username.length<3||userForm.password.length<8)return ElMessage.warning("用户名至少 3 位，密码至少 8 位");const r=await adminAPI.createUser(userForm);if(r.data.code!==200)return ElMessage.error(r.data.msg);userDialog.value=false;Object.assign(userForm,{username:"",password:"",display_name:"",department:"",role:"user"});await loadAll();ElMessage.success("用户已创建")}
async function toggleUser(row:any){await adminAPI.toggleUser(row.id);await loadAll()}
async function removeUser(row:any){await ElMessageBox.confirm("确认删除用户 "+row.username+"？","删除用户");await adminAPI.deleteUser(row.id);await loadAll()}
async function createDepartment(){if(!deptForm.name.trim())return;await adminAPI.createDepartment(deptForm.name,deptForm.description);deptDialog.value=false;Object.assign(deptForm,{name:"",description:""});await loadAll()}
async function removeDepartment(row:any){await ElMessageBox.confirm("确认删除部门 "+row.name+"？","删除部门");await adminAPI.deleteDepartment(row.id);await loadAll()}
const roleText=(v:string)=>roles.find(x=>x.value===v)?.label||v
const roleTag=(v:string)=>({admin:"danger",editor:"warning",viewer:"info",user:"success"} as any)[v]||"info"
</script>
<style scoped>
.summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));background:#fff;border:1px solid #e1e6e3;border-radius:7px;margin-bottom:18px}.summary-item{padding:18px 20px;border-right:1px solid #e5e9e7}.summary-item:last-child{border:0}.summary-item span,.summary-item small{display:block;color:#667085;font-size:12px}.summary-item strong{display:block;font-size:27px;margin:6px 0 3px}.admin-tabs{background:#fff;border:1px solid #e1e6e3;border-radius:7px;padding:0 18px 18px}.two-column{display:grid;grid-template-columns:1fr 1fr;gap:16px}.block{padding:18px}.block h3{font-size:15px;margin:0 0 16px}.health-line{display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-top:1px solid #edf0ee;font-size:13px}.health-line b{font-weight:500;color:#475467;max-width:60%;text-align:right}.capabilities{display:flex;flex-wrap:wrap;gap:8px}.muted{color:#667085;font-size:12px;line-height:1.6}.tab-toolbar{display:flex;justify-content:space-between;gap:10px;align-items:center;margin-bottom:14px}.tab-toolbar .el-input{max-width:260px}
@media(max-width:800px){.summary{grid-template-columns:repeat(2,1fr)}.summary-item:nth-child(2){border-right:0}.two-column{grid-template-columns:1fr}.tab-toolbar{align-items:stretch;flex-direction:column}.tab-toolbar .el-input{max-width:none}}
</style>