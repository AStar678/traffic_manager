<template>
  <div class="history-page">
    <div class="page-top">
      <h1>历史识别记录</h1>
      <el-button type="primary">
        <el-icon><Download /></el-icon>
        导出 CSV
      </el-button>
    </div>

    <!-- 筛选器 -->
    <div class="card filter-card">
      <div class="filter-row">
        <el-select v-model="filters.taskType" placeholder="任务类型" clearable>
          <el-option label="车牌识别" value="license_plate" />
          <el-option label="交警手势" value="police_gesture" />
          <el-option label="车主手势" value="owner_gesture" />
        </el-select>
        <el-input v-model="filters.keyword" placeholder="搜索车牌号 / 手势 / 模块" clearable />
        <el-date-picker
          v-model="filters.dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
        />
      </div>
    </div>

    <!-- 记录表格 -->
    <div class="card" style="padding: 0; overflow: hidden;">
      <el-table :data="filteredRecords" style="width: 100%">
        <el-table-column prop="createdAt" label="时间" min-width="160" />
        <el-table-column prop="taskType" label="任务类型" min-width="120">
          <template #default="{ row }">
            <el-tag :type="tagType(row.taskType)" effect="dark" size="small">
              {{ taskLabel(row.taskType) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="target" label="识别结果" min-width="200" />
        <el-table-column prop="confidence" label="置信度" width="100">
          <template #default="{ row }">{{ Math.round(row.confidence * 100) }}%</template>
        </el-table-column>
        <el-table-column prop="duration" label="耗时" width="100">
          <template #default="{ row }">{{ row.duration }} ms</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <span class="status-chip" :class="row.status">
              {{ row.status === 'completed' ? '✓ 完成' : '⚠ 需复核' }}
            </span>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="pager-row">
      <el-pagination background layout="prev, pager, next" :total="filteredRecords.length" :page-size="20" />
    </div>
  </div>
</template>

<script setup>
import { computed, reactive } from 'vue'
import { mockHistoryRecords } from '@/utils/mockData'

const filters = reactive({ taskType: '', keyword: '', dateRange: [] })

const filteredRecords = computed(() => {
  return mockHistoryRecords.filter(item => {
    const typeOk = !filters.taskType || item.taskType === filters.taskType
    const kwOk = !filters.keyword || item.target.includes(filters.keyword)
    return typeOk && kwOk
  })
})

function taskLabel(v) {
  return { license_plate: '车牌识别', police_gesture: '交警手势', owner_gesture: '车主手势' }[v] || v
}

function tagType(v) {
  return { license_plate: '', police_gesture: 'danger', owner_gesture: 'success' }[v] || ''
}
</script>

<style scoped>
.history-page { display: flex; flex-direction: column; gap: 14px; }

.page-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.page-top h1 {
  font-size: 24px;
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: -0.3px;
}

.filter-card { padding: 18px; }
.filter-row {
  display: grid;
  grid-template-columns: 160px minmax(200px, 1fr) 320px;
  gap: 12px;
}

.pager-row {
  display: flex;
  justify-content: flex-end;
}

.status-chip {
  font-size: 12px;
  font-weight: 600;
}
.status-chip.completed { color: var(--success-color); }
.status-chip.warning { color: var(--warning-color); }
</style>
