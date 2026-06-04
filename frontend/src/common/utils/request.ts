import axios from 'axios'

interface ApiResponse<T> {
  success: boolean
  data: T
  message: string
}

const request = axios.create({
  baseURL: '/api',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})

request.interceptors.request.use(
  (config) => {
    // 可在此添加 token 等认证信息
    return config
  },
  (error) => Promise.reject(error)
)

request.interceptors.response.use(
  (response) => {
    // 解包统一响应格式 {success: True, data: ..., message: ...}
    const res = response.data
    console.log('Response interceptor:', res)
    if (res && typeof res === 'object' && 'success' in res && 'data' in res) {
      if (res.success === true) {
        // 返回完整响应对象，供 callApi 访问 message
        return res as ApiResponse<unknown>
      } else {
        // 服务器返回的错误
        return Promise.reject(new Error(res.message || '请求失败'))
      }
    }
    // 非统一格式包装成 ApiResponse 格式
    return { success: true, data: res, message: '' } as ApiResponse<unknown>
  },
  (error) => {
    console.error('API Error:', error?.response?.data || error.message)
    return Promise.reject(error)
  }
)

export default request