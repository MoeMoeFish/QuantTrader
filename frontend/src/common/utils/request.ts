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
  (response: AxiosResponse) => {
    const res = response.data
    if (res && typeof res === 'object' && 'success' in res) {
      if (res.success === false) {
        return Promise.reject(new Error(res.message || '请求失败'))
      }
      // 成功时，将 message 附加到 AxiosResponse 对象上
      // 这样 callApi 可以通过 response._message 访问
      ;(response as AxiosResponse & { _message: string })._message = res.message || ''
    }
    return response
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
  let response: AxiosResponse

  try {
    if (method === 'post') {
      response = await request.post(config as string, options?.data)
    } else if (method === 'put') {
      response = await request.put(config as string, options?.data)
    } else if (method === 'delete') {
      response = await request.delete(config as string)
    } else {
      response = await request.get(config as string)
    }

    // 尝试解包统一格式
    const res = response.data as ApiResponse<T>
    if (res && typeof res === 'object' && 'success' in res && 'data' in res) {
      return { data: res.data, message: res.message || '' }
    }

    // 非标准格式直接返回
    return { data: response.data as T, message: '' }
  } catch (error: unknown) {
    const err = error as { message?: string }
    throw new Error(err.message || '请求失败')
  }
}

export default request
