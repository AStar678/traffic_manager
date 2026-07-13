import request from './request'

/** 获取音乐列表 */
export function getMusicList() {
  return request.get('/music')
}

/** 上传音乐文件 */
export function uploadMusic(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/music/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000
  })
}

/** 删除歌曲 */
export function deleteMusic(id) {
  return request.delete(`/music/${id}`)
}

/** 获取音频流URL */
export function getStreamUrl(id) {
  return `/api/v1/music/${id}/stream`
}
