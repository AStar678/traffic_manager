import request from './request'

// 统一图片推理接口
export function inferenceImage(taskType, imageUrl) {
  return request.post('/inference/image', {
    taskType,
    imageUrl
  })
}

export function inferenceCameras(taskType, includeVisuals = false) {
  return request.post('/inference/cameras', { taskType, includeVisuals }, {
    timeout: 45000,
    silent: true
  })
}

export function getInferenceData(response) {
  return response?.data?.data || response?.data || response
}
