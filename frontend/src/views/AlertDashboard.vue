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
        <div class="section-head">
          <h3 class="card-title">实时告警时间线</h3>
          <div class="section-actions">
            <button class="tool-button" type="button" @click="openLogTable">
              <el-icon><Document /></el-icon>
              <span>系统日志</span>
            </button>
            <button class="tool-button primary" type="button" :disabled="agentRunning" @click="runAgentOnce">
              <el-icon :class="{ spinning: agentRunning }"><Refresh /></el-icon>
              <span>立即检测</span>
            </button>
          </div>
        </div>
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
          <div v-if="!alerts.length" class="empty-state">
            暂无告警事件
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

    <!-- 系统日志表 -->
    <el-dialog
      v-model="logDialogVisible"
      title="系统监控日志"
      width="min(1120px, calc(100vw - 20px))"
      class="system-log-dialog"
      append-to-body
    >
      <div class="log-toolbar">
        <el-select v-model="logFilters.module" placeholder="全部模块" clearable @change="fetchSystemLogs">
          <el-option
            v-for="option in moduleOptions"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          />
        </el-select>
        <el-select v-model="logFilters.event" placeholder="全部事件" clearable @change="fetchSystemLogs">
          <el-option
            v-for="option in eventOptions"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          />
        </el-select>
        <el-select v-model="logFilters.level" placeholder="全部级别" clearable @change="fetchSystemLogs">
          <el-option label="INFO" value="INFO" />
          <el-option label="WARN" value="WARN" />
          <el-option label="ERROR" value="ERROR" />
        </el-select>
        <el-select v-model="logFilters.limit" placeholder="条数" @change="fetchSystemLogs">
          <el-option label="最近 50 条" :value="50" />
          <el-option label="最近 100 条" :value="100" />
          <el-option label="最近 200 条" :value="200" />
          <el-option label="最近 500 条" :value="500" />
        </el-select>
        <button class="tool-button primary refresh-log-button" type="button" :disabled="logsLoading" @click="fetchSystemLogs">
          <el-icon :class="{ spinning: logsLoading }"><Refresh /></el-icon>
          <span>刷新</span>
        </button>
      </div>

      <el-table
        :data="systemLogs"
        v-loading="logsLoading"
        class="system-log-table"
        height="520"
        empty-text="暂无系统日志"
      >
        <el-table-column type="expand" width="44">
          <template #default="{ row }">
            <div class="log-detail-block">
              <strong>日志详情</strong>
              <pre>{{ formatLogDetail(row.detail) }}</pre>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="时间" min-width="170" />
        <el-table-column label="级别" width="96">
          <template #default="{ row }">
            <span class="level-pill" :class="levelClass(row.level)">{{ row.level || 'INFO' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="模块" min-width="140">
          <template #default="{ row }">{{ moduleLabel(row.module) }}</template>
        </el-table-column>
        <el-table-column label="事件" min-width="150">
          <template #default="{ row }">{{ eventLabel(row.event) }}</template>
        </el-table-column>
        <el-table-column prop="traceId" label="Trace ID" min-width="190" show-overflow-tooltip />
        <el-table-column prop="userId" label="用户" width="86">
          <template #default="{ row }">{{ row.userId || '-' }}</template>
        </el-table-column>
        <el-table-column label="详情摘要" min-width="260" show-overflow-tooltip>
          <template #default="{ row }">{{ detailSnippet(row.detail) }}</template>
        </el-table-column>
      </el-table>
    </el-dialog>

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
import { computed, onMounted, onBeforeUnmount, reactive, ref, watch } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { useAlertStore } from '@/stores/alert'
import { getSystemLogs, runAlertAgent } from '@/api/alerts'

const alertStore = useAlertStore()
alertStore.fetchAlerts()

const alerts = computed(() => alertStore.alerts)
const stats = computed(() => alertStore.stats)
const selectedAlert = ref(null)
const agentRunning = ref(false)
const logDialogVisible = ref(false)
const logsLoading = ref(false)
const systemLogs = ref([])
const logFilters = reactive({
  module: '',
  event: '',
  level: '',
  limit: 100
})

const statCards = computed(() => [
  { label: '今日告警', value: stats.value.totalToday || 0, css: '' },
  { label: '严重', value: stats.value.critical || 0, css: 'critical' },
  { label: '警告', value: stats.value.warning || 0, css: 'warning' },
  { label: '提示', value: stats.value.info || 0, css: 'info' },
])

const agentSteps = ['写入JSON日志', 'Agent监听异常', 'LLM生成摘要', '存储告警事件', 'WS/邮件推送']

const moduleOptions = [
  { label: '车牌识别', value: 'license_plate' },
  { label: '车主手势', value: 'owner_gesture' },
  { label: '交警手势', value: 'police_gesture' },
  { label: '认证访问', value: 'auth' },
  { label: 'LLM 摘要', value: 'llm' },
  { label: '数据库', value: 'database' },
  { label: '用户操作', value: 'user_operation' },
  { label: '算法回调', value: 'algorithm_callback' },
  { label: '系统资源', value: 'system' }
]

const eventOptions = [
  { label: '成功', value: 'success' },
  { label: '失败', value: 'failure' },
  { label: '超时', value: 'timeout' },
  { label: '未授权', value: 'unauthorized' },
  { label: '连接异常', value: 'connection_error' },
  { label: '登录成功', value: 'login_success' },
  { label: 'Token 使用', value: 'token_usage' },
  { label: '任务完成', value: 'job_completed' },
  { label: '任务失败', value: 'job_failed' },
  { label: '未知事件', value: 'unknown_event' }
]

function severityLabel(v) {
  const map = { CRITICAL: '严重', WARNING: '警告', INFO: '提示' }
  return map[v] || v
}

function moduleLabel(value) {
  return moduleOptions.find(option => option.value === value)?.label || value || '-'
}

function eventLabel(value) {
  return eventOptions.find(option => option.value === value)?.label || value || '-'
}

function levelClass(level) {
  return String(level || 'info').toLowerCase()
}

function normalizeLog(raw) {
  return {
    ...raw,
    createdAt: raw.createdAt || raw.timestamp || '-',
    traceId: raw.traceId || '-'
  }
}

function detailSnippet(detail) {
  const formatted = formatLogDetail(detail).replace(/\s+/g, ' ').trim()
  if (!formatted || formatted === '暂无详情') {
    return '-'
  }
  return formatted.length > 120 ? `${formatted.slice(0, 120)}...` : formatted
}

function formatLogDetail(detail) {
  if (!detail) {
    return '暂无详情'
  }
  if (typeof detail !== 'string') {
    return JSON.stringify(detail, null, 2)
  }
  try {
    return JSON.stringify(JSON.parse(detail), null, 2)
  } catch (error) {
    return detail
  }
}

function logQueryParams() {
  const params = { limit: logFilters.limit }
  if (logFilters.module) params.module = logFilters.module
  if (logFilters.event) params.event = logFilters.event
  if (logFilters.level) params.level = logFilters.level
  return params
}

async function fetchSystemLogs() {
  logsLoading.value = true
  try {
    const response = await getSystemLogs(logQueryParams())
    systemLogs.value = (response.data || []).map(normalizeLog)
  } catch (error) {
    systemLogs.value = []
  } finally {
    logsLoading.value = false
  }
}

function openLogTable() {
  logDialogVisible.value = true
  fetchSystemLogs()
}

async function runAgentOnce() {
  agentRunning.value = true
  try {
    const response = await runAlertAgent()
    const events = response.data || []
    ElMessage.success(`检测完成：发现 ${events.length} 个异常事件`)
    await alertStore.fetchAlerts()
    if (logDialogVisible.value) {
      await fetchSystemLogs()
    }
  } finally {
    agentRunning.value = false
  }
}

const trendRef = ref(null)
const pieRef = ref(null)
let trendChart, pieChart

function renderCharts() {
  trendChart?.setOption({
    series: [{
      type: 'line',
      smooth: true,
      data: stats.value.trend || [],
      areaStyle: { color: 'rgba(0,180,216,0.08)' },
      lineStyle: { color: '#00b4d8', width: 3 },
      itemStyle: { color: '#00b4d8' }
    }]
  })
  pieChart?.setOption({
    series: [{
      type: 'pie',
      radius: ['50%', '72%'],
      data: stats.value.severity || [],
      color: ['#448aff', '#ffab00', '#ff3d00'],
      label: { color: '#92a0b8', formatter: '{b}\n{c}' }
    }]
  })
}

onMounted(() => {
  if (trendRef.value) {
    trendChart = echarts.init(trendRef.value)
    trendChart.setOption({
      grid: { left: 28, right: 10, top: 12, bottom: 20 },
      xAxis: { type: 'category', data: ['7/2','7/3','7/4','7/5','7/6','7/7','7/8'], axisLabel: { color: '#92a0b8' } },
      yAxis: { type: 'value', splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } }, axisLabel: { color: '#92a0b8' } }
    })
  }

  if (pieRef.value) {
    pieChart = echarts.init(pieRef.value)
  }

  renderCharts()
  window.addEventListener('resize', () => { trendChart?.resize(); pieChart?.resize() })
})

watch(stats, renderCharts, { deep: true })

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

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.section-head .card-title {
  margin-bottom: 0;
}

.section-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.tool-button {
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 0 12px;
  border: 1px solid var(--border-card);
  border-radius: 8px;
  background: rgba(255,255,255,0.04);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: color var(--duration-fast), border-color var(--duration-fast), background var(--duration-fast), transform var(--duration-fast);
}

.tool-button:hover {
  color: var(--text-primary);
  border-color: var(--border-active);
  background: rgba(0,180,216,0.08);
  transform: translateY(-1px);
}

.tool-button.primary {
  border-color: rgba(0,180,216,0.30);
  background: var(--primary-soft);
  color: var(--primary-color);
}

.tool-button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
  transform: none;
}

.spinning {
  animation: spin 900ms linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
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

.empty-state {
  min-height: 120px;
  display: grid;
  place-items: center;
  color: var(--text-muted);
  font-size: 13px;
  border: 1px dashed var(--border-card);
  border-radius: var(--radius-sm);
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

.log-toolbar {
  display: grid;
  grid-template-columns: repeat(4, minmax(130px, 1fr)) auto;
  gap: 10px;
  align-items: center;
  margin-bottom: 14px;
}

.refresh-log-button {
  min-height: 40px;
  padding: 0 14px;
}

.system-log-table {
  border: 1px solid var(--border-card);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.log-detail-block {
  padding: 14px 16px;
  background: rgba(255,255,255,0.03);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
}

.log-detail-block strong {
  display: block;
  margin-bottom: 8px;
  color: var(--text-secondary);
  font-size: 12px;
}

.log-detail-block pre {
  max-height: 260px;
  overflow: auto;
  color: var(--text-primary);
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  user-select: text;
}

.level-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 58px;
  height: 24px;
  padding: 0 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
}

.level-pill.info {
  background: rgba(68,138,255,0.14);
  color: var(--info-color);
}

.level-pill.warn {
  background: rgba(255,171,0,0.14);
  color: var(--warning-color);
}

.level-pill.error {
  background: rgba(255,61,0,0.14);
  color: var(--danger-color);
}

:deep(.system-log-dialog) {
  max-width: calc(100vw - 32px);
}

:deep(.system-log-dialog .el-dialog__body) {
  padding-top: 8px;
}

:deep(.system-log-table .el-table__inner-wrapper::before) {
  display: none;
}

@media (max-width: 1180px) {
  .content-grid {
    grid-template-columns: 1fr;
  }

  .right-panel {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .right-panel .card:last-child {
    grid-column: 1 / -1;
  }
}

@media (max-width: 760px) {
  .stat-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .stat-item {
    padding: 14px;
  }

  .stat-item strong {
    font-size: 28px;
  }

  .section-head,
  .alert-head,
  .detail-meta {
    align-items: flex-start;
    flex-direction: column;
  }

  .section-actions {
    width: 100%;
    justify-content: stretch;
  }

  .tool-button {
    flex: 1;
  }

  .right-panel,
  .agent-steps {
    grid-template-columns: 1fr;
  }

  .chart,
  .pie-chart {
    height: 180px;
  }

  .log-toolbar {
    grid-template-columns: 1fr;
  }

  :deep(.system-log-dialog) {
    width: calc(100vw - 20px) !important;
    max-width: calc(100vw - 20px);
    margin-top: 5vh;
  }
}
</style>
