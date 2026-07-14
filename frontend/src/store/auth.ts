/**
 * 认证状态管理
 */
import { defineStore } from "pinia"
import { ref, computed } from "vue"
import { authAPI } from "@/api/client"

export const useAuthStore = defineStore("auth", () => {
  const token = ref(localStorage.getItem("token") || "")
  const username = ref(localStorage.getItem("user") || "")
  const role = ref(localStorage.getItem("role") || "")

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => role.value === "admin")

  async function login(user: string, password: string) {
    const res = await authAPI.login(user, password)
    if (res.data.code === 200) {
      token.value = res.data.token
      username.value = res.data.username
      role.value = res.data.role
      localStorage.setItem("token", res.data.token)
      localStorage.setItem("user", res.data.username)
      localStorage.setItem("role", res.data.role)
    }
    return res.data
  }

  async function register(user: string, password: string) {
    const res = await authAPI.register(user, password)
    return res.data
  }

  function logout() {
    token.value = ""
    username.value = ""
    role.value = ""
    localStorage.removeItem("token")
    localStorage.removeItem("user")
    localStorage.removeItem("role")
  }

  return { token, username, role, isLoggedIn, isAdmin, login, register, logout }
})
