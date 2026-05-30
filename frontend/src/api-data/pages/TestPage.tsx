import { useEffect, useState } from 'react'
import request from '@/common/utils/request'
import { AppLayout } from '@/common/components'

export default function TestPage() {
  const [stocks, setStocks] = useState<any[]>([])
  const [message, setMessage] = useState('Loading...')

  useEffect(() => {
    request.get<any[]>('/api-data/stock/list')
      .then(data => {
        setMessage(`Got ${data.length} stocks`)
        setStocks(data)
      })
      .catch(err => {
        setMessage(`Error: ${err.message}`)
      })
  }, [])

  return (
    <AppLayout>
      <div style={{ padding: '20px' }}>
        <h1>Test Page with AppLayout</h1>
        <p>{message}</p>
        {stocks.length > 0 && (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #333' }}>
                <th style={{ padding: '10px', textAlign: 'left' }}>Code</th>
                <th style={{ padding: '10px', textAlign: 'left' }}>Name</th>
              </tr>
            </thead>
            <tbody>
              {stocks.slice(0, 10).map(stock => (
                <tr key={stock.symbol} style={{ borderBottom: '1px solid #222' }}>
                  <td style={{ padding: '10px' }}>{stock.symbol}</td>
                  <td style={{ padding: '10px' }}>{stock.name}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </AppLayout>
  )
}
