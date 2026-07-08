<template>
  <div ref="chartRef" class="confidence-chart"></div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, watch, ref } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  data: {
    type: Array,
    default: () => []
  },
  color: {
    type: String,
    default: '#1a73e8'
  }
})

const chartRef = ref(null)
let chart

function renderChart() {
  if (!chartRef.value) return
  chart ||= echarts.init(chartRef.value)
  chart.setOption({
    grid: { left: 0, right: 12, top: 8, bottom: 0, containLabel: true },
    xAxis: {
      type: 'value',
      max: 100,
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#edf2f7' } }
    },
    yAxis: {
      type: 'category',
      inverse: true,
      data: props.data.map(item => item.name),
      axisLine: { show: false },
      axisTick: { show: false }
    },
    series: [
      {
        type: 'bar',
        data: props.data.map(item => item.value),
        barWidth: 14,
        itemStyle: { color: props.color, borderRadius: [0, 7, 7, 0] },
        label: { show: true, position: 'right', formatter: '{c}%' }
      }
    ]
  })
}

onMounted(() => {
  renderChart()
  window.addEventListener('resize', renderChart)
})

watch(() => props.data, renderChart, { deep: true })

onBeforeUnmount(() => {
  window.removeEventListener('resize', renderChart)
  chart?.dispose()
})
</script>

<style scoped>
.confidence-chart {
  width: 100%;
  height: 240px;
}
</style>
