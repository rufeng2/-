<template>
  <section class="page-surface">
    <div class="page-heading">
      <div>
        <h1>运营 Agent</h1>
        <p>输入经营问题，查看意图识别、工具调用轨迹、数据证据和建议动作。</p>
      </div>
    </div>

    <div class="panel agent-layout">
      <div class="question-bar">
        <el-input v-model="question" size="large" placeholder="例如：昨天 GMV 为什么下降？" @keyup.enter="analyze" />
        <el-button type="primary" size="large" :loading="loading" @click="analyze">分析</el-button>
      </div>
      <div class="quick-prompts">
        <el-button v-for="item in prompts" :key="item" @click="question = item; analyze()">{{ item }}</el-button>
      </div>

      <el-empty v-if="!analysis" description="选择一个问题开始分析" />
      <template v-else>
        <h2>{{ analysis.summary }}</h2>
        <el-descriptions :column="3" border>
          <el-descriptions-item label="意图">{{ analysis.intent }}</el-descriptions-item>
          <el-descriptions-item label="风险">{{ analysis.risk_level }}</el-descriptions-item>
          <el-descriptions-item label="置信度">{{ analysis.confidence }}</el-descriptions-item>
        </el-descriptions>

        <h3>工具调用轨迹</h3>
        <el-timeline>
          <el-timeline-item v-for="step in analysis.tool_trace" :key="step.tool_name" :timestamp="step.tool_name">
            {{ step.output_summary }}
          </el-timeline-item>
        </el-timeline>

        <h3>数据证据</h3>
        <el-table :data="analysis.evidence">
          <el-table-column prop="label" label="指标" />
          <el-table-column prop="value" label="当前值" />
          <el-table-column prop="baseline" label="基准" />
          <el-table-column prop="rule" label="触发规则" />
        </el-table>

        <h3>建议动作</h3>
        <el-table :data="analysis.recommendations">
          <el-table-column prop="title" label="建议" min-width="180" />
          <el-table-column prop="risk_level" label="风险" width="100" />
          <el-table-column prop="expected_impact" label="预期影响" />
        </el-table>
      </template>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from "vue"
import { ElMessage } from "element-plus"
import { ecommerceAPI } from "@/api/client"

const prompts = ["昨天 GMV 为什么下降？", "哪些商品适合参加大促？", "哪些广告计划 ROI 太低？", "哪些商品存在库存风险？"]
const question = ref(prompts[0])
const loading = ref(false)
const analysis = ref<any>(null)

async function analyze() {
  if (!question.value.trim()) return
  loading.value = true
  try {
    analysis.value = (await ecommerceAPI.analyze(question.value)).data.data
  } catch {
    ElMessage.error("Agent 分析失败")
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.agent-layout{padding:18px}.question-bar{display:grid;grid-template-columns:1fr auto;gap:10px}.quick-prompts{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0 18px}.agent-layout h2{font-size:18px;line-height:1.5}.agent-layout h3{margin:22px 0 10px;font-size:15px}
</style>
