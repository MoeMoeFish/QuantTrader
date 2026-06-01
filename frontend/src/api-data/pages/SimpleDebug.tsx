import { useEffect, useState } from 'react'
import request from '@/common/utils/request'

export default function SimpleDebug() {
  const [stocks, setStocks] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [step, setStep] = useState('Initializing...')

  useEffect(() => {
    async function load() {
      try {
        setStep('Calling API...')
        const data = await request.get<any[]>('/api-data/stock/list')
        console.log('Received data:', data)
        console.log('Type:', typeof data)
        console.log('Is array:', Array.isArray(data))
        setStep(`Received data: ${JSON.stringify(data).substring(0, 100)}...`)
        setStocks(Array.isArray(data) ? data : [])
      } catch (err: any) {
        setStep(`Error: ${err.message}`)
        console.error('Error:', err)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  return (
    <div style={{ padding: '20px', fontFamily: 'monospace', background: '#0a0a0f', color: '#e5e7eb', minHeight: '100vh' }}>
      <h1 style={{ color: '#3b82f6', marginBottom: '20px' }}>Simple Debug (No AppLayout)</h1>

      <div style={{ background: '#16162a', padding: '15px', marginBottom: '20px', borderRadius: '8px' }}>
        <h2 style={{ color: '#9ca3af', marginBottom: '10px' }}>Status</h2>
        <p>Step: {step}</p>
        <p>Loading: {loading ? 'Yes' : 'No'}</p>
        <p>Stocks count: {stocks.length}</p>
      </div>

      <div style={{ background: '#16162a', padding: '15px', borderRadius: '8px' }}>
        <h2 style={{ color: '#9ca3af', marginBottom: '10px' }}>First 10 Stocks</h2>
        {stocks.length > 0 ? (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #2a2a3e' }}>
                <th style={{ padding: '8px', textAlign: 'left' }}>Code</th>
                <th style={{ padding: '8px', textAlign: 'left' }}>Name</th>
                <th style={{ padding: '8px', textAlign: 'left' }}>Market</th>
              </tr>
            </thead>
            <tbody>
              {stocks.slice(0, 10).map(stock => (
                <tr key={stock.symbol} style={{ borderBottom: '1px solid #2a2a3e' }}>
                  <td style={{ padding: '8px' }}>{stock.symbol}</td>
                  <td style={{ padding: '8px' }}>{stock.name}</td>
                  <td style={{ padding: '8px' }}>{stock.market}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p style={{ color: '#ef4444' }}>No stocks loaded</p>
        )}
      </div>
    </div>
  )
}
