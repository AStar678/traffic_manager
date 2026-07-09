import axios from 'axios'

export async function uploadImage(file) {
  const form = new FormData()
  form.append('file', file)
  const response = await axios.post('/api/files/upload/image', form, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return response.data
}
