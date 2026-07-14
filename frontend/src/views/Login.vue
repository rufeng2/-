<template>
  <main class="login-page">
    <section class="login-panel">
      <div class="product"><span>K</span><div><h1>企业知识库</h1><p>多模态知识检索与智能问答</p></div></div>
      <el-tabs v-model="tab" stretch>
        <el-tab-pane label="账号登录" name="login">
          <el-form label-position="top" @submit.prevent="submitLogin">
            <el-form-item label="用户名"><el-input v-model="login.username" size="large" :prefix-icon="User" autocomplete="username" /></el-form-item>
            <el-form-item label="密码"><el-input v-model="login.password" size="large" type="password" show-password :prefix-icon="Lock" autocomplete="current-password" @keyup.enter="submitLogin" /></el-form-item>
            <el-button type="primary" size="large" class="full" :loading="loading" @click="submitLogin">登录</el-button>
          </el-form>
          <div v-if="sso.oidc || sso.ldap" class="enterprise">
            <el-divider>企业身份认证</el-divider>
            <el-button v-if="sso.oidc" size="large" class="full" @click="oidcLogin"><el-icon><OfficeBuilding /></el-icon>使用企业 SSO 登录</el-button>
            <p v-if="sso.ldap">此账号页已支持企业 LDAP 账号直接登录</p>
          </div>
        </el-tab-pane>
        <el-tab-pane label="注册账号" name="register">
          <el-form label-position="top" @submit.prevent="submitRegister">
            <el-form-item label="用户名"><el-input v-model="register.username" size="large" :prefix-icon="User" /></el-form-item>
            <el-form-item label="密码"><el-input v-model="register.password" size="large" type="password" show-password :prefix-icon="Lock" placeholder="至少 8 位" @keyup.enter="submitRegister" /></el-form-item>
            <el-button type="primary" size="large" class="full" :loading="loading" @click="submitRegister">创建账号</el-button>
          </el-form>
        </el-tab-pane>
      </el-tabs>
      <footer><span class="status-dot"></span>知识库服务已连接</footer>
    </section>
  </main>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue"
import { useRouter } from "vue-router"
import { Lock, OfficeBuilding, User } from "@element-plus/icons-vue"
import { ElMessage } from "element-plus"
import { useAuthStore } from "@/store/auth"
import { operationsAPI } from "@/api/client"

const router = useRouter()
const auth = useAuthStore()
const tab = ref("login")
const loading = ref(false)
const login = reactive({ username: "", password: "" })
const register = reactive({ username: "", password: "" })
const sso = reactive({ oidc: false, ldap: false })

onMounted(async () => {
  try { Object.assign(sso, (await operationsAPI.ssoConfig()).data) } catch {}
  const params = new URLSearchParams(location.search)
  const token = params.get("token")
  if (token) {
    localStorage.setItem("token", token)
    localStorage.setItem("role", params.get("role") || "user")
    location.href = "/chat"
  }
})
async function submitLogin() {
  if (!login.username || !login.password) return ElMessage.warning("请输入用户名和密码")
  loading.value = true
  try {
    const result = await auth.login(login.username, login.password)
    if (result.code !== 200) return ElMessage.error(result.msg || "登录失败")
    router.push(result.role === "admin" ? "/admin" : "/chat")
  } catch (error: any) { ElMessage.error(error.response?.data?.detail || "登录服务不可用") }
  finally { loading.value = false }
}
async function submitRegister() {
  if (register.username.length < 3 || register.password.length < 8) return ElMessage.warning("用户名至少 3 位，密码至少 8 位")
  loading.value = true
  try {
    const result = await auth.register(register.username, register.password)
    if (result.code !== 200) return ElMessage.error(result.msg || "注册失败")
    login.username = register.username; register.password = ""; tab.value = "login"; ElMessage.success("账号已创建，请登录")
  } catch { ElMessage.error("注册失败") } finally { loading.value = false }
}
function oidcLogin() { location.href = "/api/sso/oidc/login" }
</script>

<style scoped>
.login-page{min-height:100%;display:grid;place-items:center;padding:24px;background:#e9efec}.login-panel{width:min(420px,100%);background:#fff;border:1px solid #dfe6e2;border-radius:8px;padding:32px;box-shadow:0 18px 55px rgba(31,53,43,.1)}.product{display:flex;align-items:center;gap:12px;margin-bottom:24px}.product>span{display:grid;place-items:center;width:44px;height:44px;border-radius:8px;background:#18794e;color:#fff;font-size:20px;font-weight:800}.product h1{font-size:22px;margin:0}.product p{margin:3px 0 0;color:#667085;font-size:13px}.full{width:100%}.enterprise p,footer{font-size:12px;color:#667085;text-align:center}.enterprise .el-button{margin-bottom:8px}footer{border-top:1px solid #edf0ee;margin-top:24px;padding-top:18px}
</style>