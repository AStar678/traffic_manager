import request from './request'

export function createJob(taskType, videoUrl, options) {
  return request.post('/jobs', { task_type: taskType, input: { type: 'video_file', url: videoUrl }, options })
}

export function getJobStatus(jobId) {
  return request.get(`/jobs/${jobId}`)
}

export function cancelJob(jobId) {
  return request.post(`/jobs/${jobId}/cancel`)
}
