<template>
  <div class="file-uploader">
    <label
      class="drop-zone"
      :class="{ dragging: isDragging }"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="handleDrop"
    >
      <input type="file" :accept="accept" @change="handleChange">
      <el-icon><UploadFilled /></el-icon>
      <strong>{{ title }}</strong>
      <span>{{ hint }}</span>
      <small v-if="fileName">{{ fileName }}</small>
    </label>

    <div v-if="showVideoUrl" class="url-input">
      <span>摄像头微服务截图 / 视频地址</span>
      <el-input
        v-model="localUrl"
        placeholder="http://127.0.0.1:8010/api/v1/cameras/snapshot.png?sourceId=..."
        clearable
        @input="$emit('update:url', localUrl)"
      />
    </div>

    <div class="mode-note">
      <strong>业务链路</strong>
      <p>主服务的视频输入统一来自摄像头微服务；抓拍地址再交给 Java 后端调用算法服务。</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

defineProps({
  title: {
    type: String,
    default: '上传图片 / 视频'
  },
  hint: {
    type: String,
    default: '支持 jpg/png/bmp/mp4/avi/mov；视频输入默认走摄像头微服务'
  },
  accept: {
    type: String,
    default: '.jpg,.jpeg,.png,.bmp,.mp4,.avi,.mov'
  },
  showVideoUrl: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['selected', 'update:url'])
const isDragging = ref(false)
const fileName = ref('')
const localUrl = ref('')

function validateFile(file) {
  const ext = file.name.split('.').pop()?.toLowerCase()
  const imageTypes = ['jpg', 'jpeg', 'png', 'bmp']
  const videoTypes = ['mp4', 'avi', 'mov']
  if (![...imageTypes, ...videoTypes].includes(ext)) {
    ElMessage.error('仅支持 jpg/png/bmp/mp4/avi/mov 文件')
    return false
  }
  const maxSize = imageTypes.includes(ext) ? 10 * 1024 * 1024 : 200 * 1024 * 1024
  if (file.size > maxSize) {
    ElMessage.error(`文件大小不能超过 ${Math.round(maxSize / 1024 / 1024)}MB`)
    return false
  }
  return true
}

function selectFile(file) {
  if (!file || !validateFile(file)) return
  fileName.value = file.name
  emit('selected', file)
}

function handleChange(event) {
  selectFile(event.target.files?.[0])
}

function handleDrop(event) {
  isDragging.value = false
  selectFile(event.dataTransfer.files?.[0])
}
</script>

<style scoped>
.file-uploader {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.drop-zone {
  min-height: 178px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 9px;
  padding: 22px;
  border: 1px dashed #9bbcf0;
  border-radius: 8px;
  background: #f7fbff;
  color: var(--primary-color);
  cursor: pointer;
  transition: border 0.2s, background 0.2s, transform 0.2s;
}

.drop-zone.dragging,
.drop-zone:hover {
  border-color: var(--primary-color);
  background: #eef6ff;
  transform: translateY(-1px);
}

input[type="file"] {
  display: none;
}

.drop-zone .el-icon {
  font-size: 36px;
}

.drop-zone strong {
  font-size: 20px;
}

.drop-zone span,
.drop-zone small {
  color: var(--text-muted);
  font-size: 13px;
  text-align: center;
}

.drop-zone small {
  color: #1f4b93;
  font-weight: 700;
}

.url-input span {
  display: block;
  margin-bottom: 8px;
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 700;
}

.mode-note {
  padding: 12px;
  border-radius: 8px;
  background: #f8fafc;
  color: var(--text-muted);
}

.mode-note strong {
  color: #172033;
}

.mode-note p {
  margin-top: 4px;
  font-size: 13px;
  line-height: 1.6;
}
</style>
