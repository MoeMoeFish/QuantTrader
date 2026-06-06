import axios, { type AxiosRequestConfig, type AxiosResponse } from 'axios'

// 统一响应格式
export interface ApiResponse<T = unknown> {
  success: boolean
  data: T
  message: string
}

const axiosInstance = axios.create({
  baseURL: '/api',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})

axiosInstance.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => Promise.reject(error)
)

axiosInstance.interceptors.response.use(
  (response: AxiosResponse<ApiResponse>) => {
    const res = response.data
    // 后端统一返回 { success, data, message }
    if (res && typeof res === 'object' && 'success' in res) {
      if (res.success === false) {
        return Promise.reject(new Error(res.message || '请求失败'))
      }
      // 成功时直接解包到内部 data，这样 request.get() 直接拿到业务数据
      return res.data as any
    }
    // 非标准格式直接返回
    return response.data as any
  },
  (error) => {
    console.error('API Error:', error?.response?.data || error.message)
    return Promise.reject(error)
  }
)

// 类型安全的请求封装：拦截器已解包，直接返回业务数据 T
interface SafeRequest {
  get<T = any>(url: string, config?: AxiosRequestConfig): Promise<T>
  post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T>
  put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T>
  delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<T>
  request<T = any>(config: AxiosRequestConfig): Promise<T>
}

const request: SafeRequest = {
  get: (url, config) => axiosInstance.get(url, config) as any,
  post: (url, data, config) => axiosInstance.post(url, data, config) as any,
  put: (url, data, config) => axiosInstance.put(url, data, config) as any,
  delete: (url, config) => axiosInstance.delete(url, config) as any,
  request: (config) => axiosInstance.request(config) as any,
}

export default request
