import request from './request'

// 统一图片推理接口
export function inferenceImage(taskType, imageUrl) {
  return request.post('/inference/image', {
    taskType,
    imageUrl
  })
}

export function getInferenceData(response) {
  return response?.data?.data || response?.data || response
}
