import request from './request'

// 统一图片推理接口
export function inferenceImage(taskType, imageUrl) {
  return request.post('/inference/image', {
    task_type: taskType,
    image_url: imageUrl
  })
}
