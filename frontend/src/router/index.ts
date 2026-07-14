/**
 * 路由配置
 */
import { createRouter, createWebHistory } from "vue-router"

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "login",
      component: () => import("@/views/Login.vue"),
      meta: { title: "登录", public: true },
    },
    {
      path: "/chat",
      name: "chat",
      component: () => import("@/views/Chat.vue"),
      meta: { title: "智能问答", requiresAuth: true },
    },
    {
      path: "/documents",
      name: "documents",
      component: () => import("@/views/Documents.vue"),
      meta: { title: "文档管理", requiresAuth: true },
    },
    {
      path: "/evaluation",
      name: "evaluation",
      component: () => import("@/views/Evaluation.vue"),
      meta: { title: "RAG 自动评测", requiresAuth: true, requiresAdmin: true },
    },    {
      path: "/admin",
      name: "admin",
      component: () => import("@/views/Admin/Dashboard.vue"),
      meta: { title: "管理后台", requiresAuth: true, requiresAdmin: true },
    },
  ],
})

// 路由守卫
router.beforeEach((to, _from, next) => {
  document.title = `${to.meta.title || "企业知识库"} - RAG 系统`

  const token = localStorage.getItem("token")
  const role = localStorage.getItem("role")

  if (to.meta.requiresAuth && !token) {
    next({ name: "login" })
  } else if (to.meta.requiresAdmin && role !== "admin") {
    next({ name: "chat" })
  } else {
    next()
  }
})

export default router
