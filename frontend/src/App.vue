<template>
  <router-view v-if="route.meta.public" />
  <div v-else class="app-shell">
    <aside
      class="app-sidebar"
      :class="{ open: mobileOpen, collapsed }"
      :style="{ width: sidebarWidth + 'px', flexBasis: sidebarWidth + 'px' }"
    >
      <div class="brand">
        <span class="brand-mark">K</span>
        <div class="sidebar-copy"><strong>企业知识库</strong><small>RAG Workspace</small></div>
      </div>
      <nav>
        <router-link to="/chat" title="智能问答"><el-icon><ChatDotRound /></el-icon><span class="sidebar-copy">智能问答</span></router-link>
        <router-link to="/documents" title="文档与知识库"><el-icon><Files /></el-icon><span class="sidebar-copy">文档与知识库</span></router-link>
        <router-link v-if="auth.isAdmin" to="/evaluation" title="自动评测"><el-icon><DataAnalysis /></el-icon><span class="sidebar-copy">自动评测</span></router-link>
        <router-link v-if="auth.isAdmin" to="/admin" title="管理与运维"><el-icon><Setting /></el-icon><span class="sidebar-copy">管理与运维</span></router-link>
      </nav>
      <div class="account">
        <div class="avatar">{{ auth.username.slice(0, 1).toUpperCase() }}</div>
        <div class="account-copy sidebar-copy"><strong>{{ auth.username }}</strong><small>{{ roleName }}</small></div>
        <el-dropdown trigger="click">
          <el-button text circle title="账号菜单"><el-icon><MoreFilled /></el-icon></el-button>
          <template #dropdown><el-dropdown-menu>
            <el-dropdown-item @click="exportData">导出我的数据</el-dropdown-item>
            <el-dropdown-item divided @click="logout">退出登录</el-dropdown-item>
          </el-dropdown-menu></template>
        </el-dropdown>
      </div>

      <button class="collapse-handle" type="button" :title="collapsed ? '展开导航' : '折叠导航'" @click="toggleCollapsed">
        <el-icon><ArrowRight v-if="collapsed" /><ArrowLeft v-else /></el-icon>
      </button>
      <div
        v-if="!collapsed"
        class="resize-handle"
        title="拖动调整导航宽度"
        @pointerdown="startResize"
      ></div>
    </aside>

    <div v-if="mobileOpen" class="shell-mask" @click="mobileOpen = false"></div>
    <main class="app-main">
      <header class="mobile-header">
        <el-button text circle @click="mobileOpen = true"><el-icon><Menu /></el-icon></el-button>
        <strong>企业知识库</strong><span></span>
      </header>
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import { ElMessage } from "element-plus"
import { useAuthStore } from "@/store/auth"
import { operationsAPI } from "@/api/client"

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const mobileOpen = ref(false)
const savedWidth = Number(localStorage.getItem("sidebar-width") || 190)
const sidebarWidth = ref(Math.min(280, Math.max(150, savedWidth)))
const previousWidth = ref(sidebarWidth.value)
const collapsed = ref(localStorage.getItem("sidebar-collapsed") === "true")
if (collapsed.value) sidebarWidth.value = 64

const roleName = computed(() => ({ admin: "系统管理员", editor: "知识库编辑", viewer: "只读用户", user: "普通用户" } as any)[auth.role] || auth.role)
watch(() => route.path, () => { mobileOpen.value = false })

function toggleCollapsed() {
  collapsed.value = !collapsed.value
  if (collapsed.value) {
    previousWidth.value = sidebarWidth.value
    sidebarWidth.value = 64
  } else {
    sidebarWidth.value = Math.max(150, previousWidth.value || 190)
  }
  localStorage.setItem("sidebar-collapsed", String(collapsed.value))
}

function startResize(event: PointerEvent) {
  if (window.innerWidth <= 760) return
  event.preventDefault()
  const startX = event.clientX
  const startWidth = sidebarWidth.value
  document.body.classList.add("resizing-sidebar")

  const move = (moveEvent: PointerEvent) => {
    sidebarWidth.value = Math.min(280, Math.max(150, startWidth + moveEvent.clientX - startX))
  }
  const stop = () => {
    previousWidth.value = sidebarWidth.value
    localStorage.setItem("sidebar-width", String(sidebarWidth.value))
    document.body.classList.remove("resizing-sidebar")
    window.removeEventListener("pointermove", move)
    window.removeEventListener("pointerup", stop)
  }
  window.addEventListener("pointermove", move)
  window.addEventListener("pointerup", stop, { once: true })
}

onBeforeUnmount(() => document.body.classList.remove("resizing-sidebar"))

async function exportData() {
  const response = await operationsAPI.exportPrivacy()
  const blob = new Blob([JSON.stringify(response.data.data, null, 2)], { type: "application/json" })
  const link = document.createElement("a")
  link.href = URL.createObjectURL(blob)
  link.download = "knowledge-rag-" + auth.username + ".json"
  link.click()
  URL.revokeObjectURL(link.href)
  ElMessage.success("个人数据已导出")
}
function logout() { auth.logout(); router.push("/") }
</script>