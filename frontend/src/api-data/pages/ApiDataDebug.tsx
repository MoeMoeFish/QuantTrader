import { useEffect, useState } from 'react'
import request from '@/common/utils/request'

export default function ApiDataDebug() {
  const [rawResponse, setRawResponse] = useState<any>(null)
  const [unwrappedData, setUnwrappedData] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const [dataType, setDataType] = useState<string>('')

  useEffect(() => {
    // 直接使用 axios 获取解包后的数据
    request.get('/api-data/stock/list')
      .then(data => {
        console.log('Unwrapped data:', data)
        console.log('Type of data:', typeof data)
        console.log('Is array:', Array.isArray(data))
        setUnwrappedData(data)
        setDataType(`${typeof data} (${Array.isArray(data) ? 'array' : 'not array'})`)
      })
      .catch(err => {
        console.error('Error:', err)
        setError(err.message)
      })

    // 使用原生 fetch 获取原始响应
    fetch('/api/api-data/stock/list')
      .then(res => res.json())
      .then(data => {
        console.log('Raw response:', data)
        setRawResponse(data)
      })
      .catch(err => {
        console.error('Fetch error:', err)
      })
  }, [])

  return (
    <div style={{ padding: '20px', fontFamily: 'monospace', background: '#1a1a2e', color: '#e5e7eb', minHeight: '100vh' }}>
      <h1 style={{ color: '#3b82f6' }}>API Debug Page</h1>

      <div style={{ marginBottom: '20px', background: '#16162a', padding: '15px', borderRadius: '8px' }}>
        <h2 style={{ color: '#9ca3af' }}>Raw Response (fetch)</h2>
        <p>Success: {rawResponse?.success ? '✓' : '✗'}</p>
        <p>Data keys: {rawResponse?.data ? `Array with ${rawResponse.data.length} items` : 'N/A'}</p>
      </div>

      <div style={{ marginBottom: '20px', background: '#16162a', padding: '15px', borderRadius: '8px' }}>
        <h2 style={{ color: '#9ca3af' }}>Unwrapped Data (axios interceptor)</h2>
        <p>Type: {dataType}</p>
        <p>First item: {unwrappedData ? JSON.stringify(unwrappedData[0]) : 'N/A'}</p>
        <p>Count: {Array.isArray(unwrappedData) ? unwrappedData.length : 'Not an array'}</p>
      </div>

      {error && (
        <div style={{ color: '#ef4444', background: '#16162a', padding: '15px', borderRadius: '8px' }}>
          <h2>Error</h2>
          <pre>{error}</pre>
        </div>
      )}

      <div style={{ background: '#16162a', padding: '15px', borderRadius: '8px' }}>
        <h2 style={{ color: '#9ca3af' }}>First 5 stocks (unwrapped):</h2>
        {Array.isArray(unwrappedData) ? (
          <ul>
            {unwrappedData.slice(0, 5).map((stock: any) => (
              <li key={stock.symbol}>{stock.symbol} - {stock.name}</li>
            ))}
          </ul>
        ) : (
          <p style={{ color: '#ef4444' }}>Data is not an array!</p>
        )}
      </div>
    </div>
  )
}
