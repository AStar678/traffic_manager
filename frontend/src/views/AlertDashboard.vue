<template>
  <div class="alert-page">
    <!-- 顶行统计 -->
    <div class="stat-row">
      <div class="card stat-item" v-for="s in statCards" :key="s.label">
        <span>{{ s.label }}</span>
        <strong :class="s.css">{{ s.value }}</strong>
      </div>
    </div>

    <div class="content-grid">
      <!-- 告警列表 -->
      <div class="card alert-list-card">
        <h3 class="card-title">实时告警时间线</h3>
        <div class="alert-items">
          <div
            v-for="alert in alerts"
            :key="alert.id"
            class="alert-row"
            :class="alert.severity.toLowerCase()"
            @click="selectedAlert = alert"
          >
            <span class="status-dot" :class="alert.severity === 'CRITICAL' ? 'offline' : alert.severity === 'WARNING' ? 'warning' : 'online'"></span>
            <div class="alert-body">
              <div class="alert-head">
                <strong>{{ alert.title }}</strong>
                <span class="severity-tag" :class="alert.severity.toLowerCase()">{{ severityLabel(alert.severity) }}</span>
              </div>
              <p>{{ alert.summary }}</p>
              <small>{{ alert.occurredAt }} · {{ alert.module }}</small>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧面板 -->
      <div class="right-panel">
        <!-- 趋势图 -->
        <div class="card">
          <h3 class="card-title">近7天告警趋势</h3>
          <div ref="trendRef" class="chart"></div>
        </div>

        <!-- 级别分布 -->
        <div class="card">
          <h3 class="card-title">级别分布</h3>
          <div ref="pieRef" class="chart pie-chart"></div>
        </div>

        <!-- Agent 链路 -->
        <div class="card">
          <h3 class="card-title">Agent 感知-决策-执行 链路</h3>
          <div class="agent-steps">
            <span v-for="step in agentSteps" :key="step">{{ step }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 选中告警详情弹窗 -->
    <div v-if="selectedAlert" class="alert-detail-overlay" @click.self="selectedAlert = null">
      <div class="card alert-detail">
        <div class="detail-head">
          <span class="severity-tag" :class="selectedAlert.severity.toLowerCase()">{{ severityLabel(selectedAlert.severity) }}</span>
          <button class="close-btn" @click="selectedAlert = null">✕</button>
        </div>
        <h2>{{ selectedAlert.title }}</h2>
        <p>{{ selectedAlert.summary }}</p>
        <div class="detail-meta">
          <span>来源模块：{{ selectedAlert.module }}</span>
          <span>时间：{{ selectedAlert.occurredAt }}</span>
          <span>状态：{{ selectedAlert.status }}</span>
        </div>
        <div class="suggested-actions" v-if="selectedAlert.suggestedActions?.length">
          <strong>建议操作：</strong>
          <ul>
            <li v-for="action in selectedAlert.suggestedActions" :key="action">{{ action }}</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import * as echarts from 'echarts'
import { useAlertStore } from '@/stores/alert'

const alertStore = useAlertStore()
alertStore.fetchAlerts()

const alerts = computed(() => alertStore.alerts)
const stats = computed(() => alertStore.stats)
const selectedAlert = ref(null)

const statCards = computed(() => [
  { label: '今日告警', value: stats.value.totalToday || 0, css: '' },
  { label: '严重', value: stats.value.critical || 0, css: 'critical' },
  { label: '警告', value: stats.value.warning || 0, css: 'warning' },
  { label: '提示', value: stats.value.info || 0, css: 'info' },
])

const agentSteps = ['写入JSON日志', 'Agent监听异常', 'LLM生成摘要', '存储告警事件', 'WS/邮件推送']

function severityLabel(v) {
  const map = { CRITICAL: '严重', WARNING: '警告', INFO: '提示' }
  return map[v] || v
}

const trendRef = ref(null)
const pieRef = ref(null)
let trendChart, pieChart

onMounted(() => {
  if (trendRef.value) {
    trendChart = echarts.init(trendRef.value)
    trendChart.setOption({
      grid: { left: 28, right: 10, top: 12, bottom: 20 },
      xAxis: { type: 'category', data: ['7/2','7/3','7/4','7/5','7/6','7/7','7/8'], axisLabel: { color: '#92a0b8' } },
      yAxis: { type: 'value', splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } }, axisLabel: { color: '#92a0b8' } },
      series: [{
        type: 'line', smooth: true, data: stats.value.trend || [],
        areaStyle: { color: 'rgba(0,180,216,0.08)' },
        lineStyle: { color: '#00b4d8', width: 3 },
        itemStyle: { color: '#00b4d8' }
      }]
    })
  }

  if (pieRef.value) {
    pieChart = echarts.init(pieRef.value)
    pieChart.setOption({
      series: [{
        type: 'pie', radius: ['50%', '72%'],
        data: stats.value.severity || [],
        color: ['#448aff', '#ffab00', '#ff3d00'],
        label: { color: '#92a0b8', formatter: '{b}\n{c}' }
      }]
    })
  }

  window.addEventListener('resize', () => { trendChart?.resize(); pieChart?.resize() })
})

onBeforeUnmount(() => {
  trendChart?.dispose()
  pieChart?.dispose()
})
</script>

<style scoped>
.alert-page { display: flex; flex-direction: column; gap: 16px; }

/* 统计行 */
.stat-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.stat-item { padding: 18px; }
.stat-item span { font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
.stat-item strong { display: block; margin-top: 8px; font-size: 36px; font-weight: 800; color: var(--text-primary); line-height: 1; }
.stat-item strong.critical { color: var(--danger-color); }
.stat-item strong.warning { color: var(--warning-color); }
.stat-item strong.info { color: var(--info-color); }

/* 内容网格 */
.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 16px;
}

.card-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 14px;
}

/* 告警列表 */
.alert-list-card { }

.alert-items {
  display: flex;
  flex-direction: column;
}

.alert-row {
  display: flex;
  gap: 12px;
  padding: 14px 0;
  cursor: pointer;
  transition: opacity var(--duration-fast);
  border-bottom: 1px solid var(--border-subtle);
}

.alert-row:last-child { border-bottom: none; }
.alert-row:hover { opacity: 0.8; }

.alert-row .status-dot { margin-top: 6px; flex-shrink: 0; }

.alert-body { flex: 1; }

.alert-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.alert-head strong { font-size: 14px; font-weight: 600; color: var(--text-primary); }

.severity-tag {
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
}
.severity-tag.critical { background: rgba(255,61,0,0.15); color: var(--danger-color); }
.severity-tag.warning { background: rgba(255,171,0,0.15); color: var(--warning-color); }
.severity-tag.info { background: rgba(68,138,255,0.15); color: var(--info-color); }

.alert-body p {
  margin-top: 6px;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.alert-body small {
  display: block;
  margin-top: 6px;
  font-size: 11px;
  color: var(--text-muted);
}

/* 右侧面板 */
.right-panel { display: flex; flex-direction: column; gap: 14px; }

.chart { width: 100%; height: 200px; }
.pie-chart { height: 200px; }

.agent-steps {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
}

.agent-steps span {
  padding: 10px 6px;
  background: rgba(255,171,0,0.08);
  border: 1px solid rgba(255,171,0,0.15);
  border-radius: 8px;
  text-align: center;
  font-size: 12px;
  font-weight: 600;
  color: var(--warning-color);
  display: grid;
  place-items: center;
}

/* 详情弹窗 */
.alert-detail-overlay {
  position: fixed;
  inset: 0;
  display: grid;
  place-items: center;
  background: rgba(0,0,0,0.55);
  backdrop-filter: blur(6px);
  z-index: 300;
}

.alert-detail {
  width: 500px;
  max-width: 90vw;
  padding: 28px;
  border: 1px solid var(--border-card);
}

.detail-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.close-btn {
  width: 32px; height: 32px;
  border: none; border-radius: 50%;
  background: rgba(255,255,255,0.06);
  color: var(--text-secondary);
  font-size: 16px;
  cursor: pointer;
}

.detail-head h2 { font-size: 20px; }

.detail-meta {
  display: flex;
  gap: 16px;
  margin-top: 14px;
  font-size: 12px;
  color: var(--text-muted);
}

.suggested-actions {
  margin-top: 16px;
  padding: 14px;
  background: rgba(255,255,255,0.03);
  border-radius: var(--radius-sm);
}

.suggested-actions strong { font-size: 12px; color: var(--text-secondary); }
.suggested-actions ul { margin-top: 8px; padding-left: 18px; }
.suggested-actions li { font-size: 13px; color: var(--text-primary); line-height: 1.8; }
</style>
