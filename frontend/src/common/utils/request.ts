import axios, { AxiosResponse } from 'axios'

// 统一响应格式
export interface ApiResponse<T = unknown> {
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
    return config
  },
  (error) => Promise.reject(error)
)

request.interceptors.response.use(
  (response: AxiosResponse<ApiResponse>) => {
    const res = response.data
    // 后端统一返回 { success, data, message }
    if (res && typeof res === 'object' && 'success' in res) {
      if (res.success === false) {
        return Promise.reject(new Error(res.message || '请求失败'))
      }
      // 成功时直接解包，返回 response.data（即 { success, data, message }）
      // 这样调用方 request.get().data 得到内部 data，request.get().message 得到 message
      return res as any
    }
    // 非标准格式直接返回
    return response.data as any
  },
  (error) => {
    console.error('API Error:', error?.response?.data || error.message)
    return Promise.reject(error)
  }
)

/**
 * 统一 API 调用方法
 * 自动解包统一响应格式 {success, data, message}
 */
export async function callApi<T>(
  config: Parameters<typeof request.get>[0] | Parameters<typeof request.post>[0],
  options?: { method?: 'get' | 'post' | 'put' | 'delete'; data?: unknown }
): Promise<{ data: T; message: string }> {
  const method = options?.method || 'get'
  let response: ApiResponse<T>

  try {
    if (method === 'post') {
      response = await request.post(config as string, options?.data) as unknown as ApiResponse<T>
    } else if (method === 'put') {
      response = await request.put(config as string, options?.data) as unknown as ApiResponse<T>
    } else if (method === 'delete') {
      response = await request.delete(config as string) as unknown as ApiResponse<T>
    } else {
      response = await request.get(config as string) as unknown as ApiResponse<T>
    }

    return { data: response.data, message: response.message || '' }
  } catch (error: unknown) {
    const err = error as { message?: string }
    throw new Error(err.message || '请求失败')
  }
}

export default request
