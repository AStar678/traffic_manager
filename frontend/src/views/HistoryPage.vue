<template>
  <div class="history-page">
    <div class="page-top">
      <div>
        <h1>历史识别记录</h1>
        <p>查看当前账号的真实识别结果，数据来自云端 MySQL</p>
      </div>
      <el-button :disabled="!records.length" @click="exportCurrentPage">
        <el-icon><Download /></el-icon>
        导出当前页
      </el-button>
    </div>

    <div class="card filter-card">
      <div class="filter-grid">
        <el-select v-model="filters.taskType" placeholder="全部任务" clearable aria-label="按任务类型筛选">
          <el-option label="车牌识别" value="license_plate" />
          <el-option label="车辆类型" value="vehicle_type" />
          <el-option label="交警手势" value="police_gesture" />
          <el-option label="车主手势" value="owner_gesture" />
        </el-select>
        <el-select v-model="filters.success" placeholder="全部状态" clearable aria-label="按识别状态筛选">
          <el-option label="识别成功" :value="true" />
          <el-option label="识别失败" :value="false" />
        </el-select>
        <el-input
          v-model.trim="filters.keyword"
          placeholder="搜索车牌、手势或错误信息"
          clearable
          aria-label="搜索识别记录"
          @keyup.enter="applyFilters"
        />
        <el-date-picker
          v-model="filters.dateRange"
          type="daterange"
          value-format="YYYY-MM-DD"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          aria-label="按日期范围筛选"
        />
        <div class="filter-actions">
          <el-button type="primary" :loading="loading" @click="applyFilters">
            <el-icon><Search /></el-icon>
            查询
          </el-button>
          <el-button :disabled="loading" @click="resetFilters">重置</el-button>
        </div>
      </div>
    </div>

    <div class="card records-card">
      <div class="records-head">
        <div>
          <span class="section-kicker">RECOGNITION LOG</span>
          <strong>{{ total.toLocaleString() }} 条记录</strong>
        </div>
        <el-button text :loading="loading" aria-label="刷新历史记录" @click="loadRecords">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>

      <div class="table-shell">
        <el-table
          v-loading="loading"
          :data="records"
          row-key="id"
          empty-text="当前条件下暂无识别记录"
          style="width: 100%"
        >
          <el-table-column label="时间" min-width="178">
            <template #default="{ row }">{{ formatTime(row.createdAt) }}</template>
          </el-table-column>
          <el-table-column prop="taskType" label="任务类型" min-width="126">
            <template #default="{ row }">
              <el-tag :type="tagType(row.taskType)" effect="dark" size="small">
                {{ taskLabel(row.taskType) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="target" label="识别结果" min-width="230" show-overflow-tooltip />
          <el-table-column label="目标数" width="88" align="center">
            <template #default="{ row }">{{ row.detectionCount ?? '-' }}</template>
          </el-table-column>
          <el-table-column label="置信度" width="100" align="right">
            <template #default="{ row }">{{ confidenceText(row.confidence) }}</template>
          </el-table-column>
          <el-table-column label="耗时" width="108" align="right">
            <template #default="{ row }">{{ durationText(row.durationMs) }}</template>
          </el-table-column>
          <el-table-column label="状态" width="108" fixed="right">
            <template #default="{ row }">
              <span class="status-chip" :class="row.status">
                {{ statusLabel(row.status) }}
              </span>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="pager-row">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          background
          layout="total, sizes, prev, pager, next"
          :page-sizes="[20, 50, 100]"
          :total="total"
          @current-change="loadRecords"
          @size-change="handlePageSizeChange"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getRecords } from '@/api/records'

const filters = reactive({ taskType: '', success: '', keyword: '', dateRange: [] })
const records = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
let requestSequence = 0

onMounted(loadRecords)

async function loadRecords() {
  const currentRequest = ++requestSequence
  loading.value = true
  try {
    const params = {
      page: page.value - 1,
      size: pageSize.value
    }
    if (filters.taskType) params.taskType = filters.taskType
    if (filters.success !== '') params.success = filters.success
    if (filters.keyword) params.keyword = filters.keyword
    if (filters.dateRange?.length === 2) {
      params.startTime = `${filters.dateRange[0]}T00:00:00`
      params.endTime = `${filters.dateRange[1]}T23:59:59.999999`
    }

    const response = await getRecords(params)
    if (currentRequest !== requestSequence) return
    const data = response?.data || response || {}
    records.value = Array.isArray(data.content) ? data.content : []
    total.value = Number(data.totalElements || 0)
  } catch (error) {
    if (currentRequest !== requestSequence) return
    records.value = []
    total.value = 0
    if (!error.__visionDriveNotified) ElMessage.error('历史记录加载失败')
  } finally {
    if (currentRequest === requestSequence) loading.value = false
  }
}

function applyFilters() {
  page.value = 1
  loadRecords()
}

function resetFilters() {
  Object.assign(filters, { taskType: '', success: '', keyword: '', dateRange: [] })
  page.value = 1
  loadRecords()
}

function handlePageSizeChange() {
  page.value = 1
  loadRecords()
}

function taskLabel(value) {
  return {
    license_plate: '车牌识别',
    vehicle_type: '车辆类型',
    police_gesture: '交警手势',
    owner_gesture: '车主手势'
  }[value] || value || '未知任务'
}

function tagType(value) {
  return {
    license_plate: '',
    vehicle_type: 'info',
    police_gesture: 'danger',
    owner_gesture: 'success'
  }[value] || 'info'
}

function statusLabel(status) {
  return { completed: '✓ 完成', warning: '◇ 低置信', failed: '× 失败' }[status] || '未知'
}

function confidenceText(value) {
  return Number.isFinite(value) ? `${Math.round(value * 100)}%` : '-'
}

function durationText(value) {
  return Number.isFinite(value) ? `${value} ms` : '-'
}

function formatTime(value) {
  if (!value) return '-'
  return String(value).replace('T', ' ').slice(0, 19)
}

function exportCurrentPage() {
  if (!records.value.length) return
  const rows = [
    ['时间', '任务类型', '识别结果', '目标数', '置信度', '耗时(ms)', '状态'],
    ...records.value.map(row => [
      formatTime(row.createdAt),
      taskLabel(row.taskType),
      row.target || '',
      row.detectionCount ?? '',
      Number.isFinite(row.confidence) ? row.confidence : '',
      row.durationMs ?? '',
      statusLabel(row.status).replace(/^[✓◇×]\s*/, '')
    ])
  ]
  const csv = `\uFEFF${rows.map(row => row.map(escapeCsv).join(',')).join('\n')}`
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
  const link = document.createElement('a')
  link.href = url
  link.download = `visiondrive-history-${new Date().toISOString().slice(0, 10)}.csv`
  link.click()
  URL.revokeObjectURL(url)
}

function escapeCsv(value) {
  const text = String(value ?? '')
  return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text
}
</script>

<style scoped>
.history-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

.page-top,
.records-head,
.pager-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.page-top h1 {
  font-size: 24px;
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: -0.3px;
}

.page-top p {
  margin-top: 5px;
  color: var(--text-muted);
  font-size: 13px;
}

.filter-card {
  padding: 16px;
}

.filter-grid {
  display: grid;
  grid-template-columns: 150px 140px minmax(220px, 1fr) minmax(260px, 320px) auto;
  gap: 12px;
  align-items: center;
}

.filter-actions {
  display: flex;
  gap: 8px;
  white-space: nowrap;
}

.filter-grid :deep(.el-select__wrapper) {
  min-height: 34px;
  background: var(--bg-card);
  border-radius: 12px;
  box-shadow: 0 0 0 1px var(--border-card) inset;
}

.filter-grid :deep(.el-select__wrapper:hover),
.filter-grid :deep(.el-select__wrapper.is-focused) {
  box-shadow: 0 0 0 1px var(--border-active) inset;
}

.filter-grid :deep(.el-select__placeholder) {
  color: var(--text-muted);
}

.records-card {
  min-width: 0;
  padding: 0;
  overflow: hidden;
}

.records-head {
  min-height: 66px;
  padding: 13px 18px;
  border-bottom: 1px solid var(--border-subtle);
}

.records-head > div {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.section-kicker {
  color: var(--primary-color);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 1.4px;
}

.records-head strong {
  color: var(--text-primary);
  font-size: 17px;
}

.table-shell {
  min-width: 0;
  overflow-x: auto;
}

.table-shell :deep(.el-table) {
  min-width: 900px;
}

.status-chip {
  display: inline-flex;
  align-items: center;
  min-width: 72px;
  font-size: 12px;
  font-weight: 700;
}

.status-chip.completed { color: var(--success-color); }
.status-chip.warning { color: var(--warning-color); }
.status-chip.failed { color: var(--danger-color); }

.pager-row {
  min-height: 64px;
  padding: 12px 18px;
  border-top: 1px solid var(--border-subtle);
}

@media (max-width: 1180px) {
  .filter-grid {
    grid-template-columns: 150px 140px minmax(220px, 1fr);
  }

  .filter-grid :deep(.el-date-editor),
  .filter-actions {
    width: 100%;
  }
}

@media (max-width: 720px) {
  .page-top {
    align-items: flex-start;
  }

  .page-top p {
    max-width: 250px;
  }

  .filter-grid {
    grid-template-columns: 1fr;
  }

  .filter-grid :deep(.el-select),
  .filter-grid :deep(.el-date-editor),
  .filter-actions,
  .filter-actions .el-button {
    width: 100%;
  }

  .pager-row {
    justify-content: flex-start;
    overflow-x: auto;
  }

  .pager-row :deep(.el-pagination__sizes),
  .pager-row :deep(.el-pagination__total) {
    display: none;
  }
}
</style>
