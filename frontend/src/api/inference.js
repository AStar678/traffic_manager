import request from './request'

// 统一图片推理接口
export function inferenceImage(taskType, imageUrl) {
  return request.post('/inference/image', {
    taskType,
    imageUrl
  })
}

export function inferenceCameras(taskType) {
  return request.post('/inference/cameras', { taskType }, { timeout: 45000 })
}

export function getInferenceData(response) {
  return response?.data?.data || response?.data || response
}
