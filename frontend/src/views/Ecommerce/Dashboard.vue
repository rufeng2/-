<template>
  <section class="page-surface">
    <div class="page-heading">
      <div>
        <h1>运营驾驶舱</h1>
        <p>实时查看 GMV、转化、广告 ROI、库存和评价异常。</p>
      </div>
      <el-button type="primary" :loading="loading" @click="load">刷新数据</el-button>
    </div>

    <div class="metric-grid">
      <article v-for="(item, key) in dashboard?.kpis" :key="key" class="metric-card">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}{{ item.unit }}</strong>
        <em :class="item.trend">环比 {{ item.delta_pct }}%</em>
      </article>
    </div>

    <el-row :gutter="16" class="section-row">
      <el-col :xs="24" :lg="14">
        <div class="panel section-panel">
          <h2>经营趋势</h2>
          <el-table :data="dashboard?.trend || []">
            <el-table-column prop="date" label="日期" />
            <el-table-column prop="gmv" label="GMV" />
            <el-table-column prop="orders" label="订单数" />
          </el-table>
        </div>
      </el-col>
      <el-col :xs="24" :lg="10">
        <div class="panel section-panel">
          <h2>异常提醒</h2>
          <el-empty v-if="!dashboard?.anomalies?.length" description="暂无异常" />
          <div v-for="item in dashboard?.anomalies || []" :key="item.id" class="alert-item">
            <el-tag :type="item.severity === 'high' ? 'danger' : 'warning'">{{ item.severity }}</el-tag>
            <strong>{{ item.title }}</strong>
            <p>{{ item.summary }}</p>
          </div>
        </div>
      </el-col>
    </el-row>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue"
import { ElMessage } from "element-plus"
import { ecommerceAPI } from "@/api/client"

const loading = ref(false)
const dashboard = ref<any>(null)

async function load() {
  loading.value = true
  try {
    dashboard.value = (await ecommerceAPI.dashboard()).data.data
  } catch {
    ElMessage.error("运营数据加载失败")
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.metric-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px}.metric-card{background:#fff;border:1px solid var(--border);border-radius:6px;padding:16px}.metric-card span{display:block;color:var(--ink-muted);font-size:12px}.metric-card strong{display:block;margin-top:8px;font-size:24px}.metric-card em{font-style:normal;font-size:12px}.metric-card em.down{color:var(--danger)}.metric-card em.up{color:var(--success)}.section-row{margin-top:16px}.section-panel{padding:16px}.section-panel h2{margin:0 0 12px;font-size:16px}.alert-item{border-top:1px solid var(--border);padding:12px 0}.alert-item:first-of-type{border-top:0}.alert-item strong{display:block;margin:6px 0}.alert-item p{margin:0;color:var(--ink-muted);line-height:1.6}
</style>
