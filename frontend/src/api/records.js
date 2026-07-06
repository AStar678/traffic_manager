import request from './request'

export function getRecords(params) {
  return request.get('/records', { params })
}

export function getRecordDetail(id) {
  return request.get(`/records/${id}`)
}
