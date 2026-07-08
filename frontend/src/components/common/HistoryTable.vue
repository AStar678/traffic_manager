<template>
  <el-table :data="records" class="history-table" stripe>
    <el-table-column prop="createdAt" label="时间" min-width="170" />
    <el-table-column prop="taskType" label="任务" min-width="130">
      <template #default="{ row }">
        <el-tag>{{ taskLabel(row.taskType) }}</el-tag>
      </template>
    </el-table-column>
    <el-table-column prop="target" label="结果摘要" min-width="180" />
    <el-table-column prop="confidence" label="置信度" width="110">
      <template #default="{ row }">{{ Math.round(row.confidence * 100) }}%</template>
    </el-table-column>
    <el-table-column prop="duration" label="耗时" width="100">
      <template #default="{ row }">{{ row.duration }} ms</template>
    </el-table-column>
    <el-table-column prop="status" label="状态" width="110">
      <template #default="{ row }">
        <el-tag :type="row.status === 'completed' ? 'success' : 'warning'">
          {{ row.status === 'completed' ? '完成' : '需复核' }}
        </el-tag>
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup>
defineProps({
  records: {
    type: Array,
    default: () => []
  }
})

function taskLabel(value) {
  const map = {
    license_plate: '车牌识别',
    police_gesture: '交警手势',
    owner_gesture: '车主手势'
  }
  return map[value] || value
}
</script>

<style scoped>
.history-table {
  width: 100%;
}
</style>
