'use client'

import { useEffect, useState } from 'react'
import api from '@/lib/api'

interface RepairEvent {
  timestamp: string
  action: string
  alert_id?: string
  status?: string
  details?: any
}

export default function HistoryPage() {
  const [events, setEvents] = useState<RepairEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get('/api/v1/audit', { params: { limit: 200 } })
      .then((res) => {
        const data = Array.isArray(res.data) ? res.data : []
        const filtered = data.filter((e: RepairEvent) => {
          const action = (e.action || '').toUpperCase()
          return (
            action.includes('HEALING') ||
            action.includes('REPAIR') ||
            action.includes('EXECUTED') ||
            action.includes('VERIFY')
          )
        })
        setEvents(filtered)
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className='p-6'>加载中...</div>
  if (error) return <div className='p-6 text-red-600'>错误: {error}</div>

  return (
    <main className='p-6 space-y-6 bg-gray-100 dark:bg-gray-900 min-h-screen'>
      <h1 className='text-2xl font-bold text-gray-900 dark:text-gray-100'>修复历史 / 验证结果</h1>
      <div className='bg-white dark:bg-gray-800 rounded shadow overflow-hidden'>
        <table className='min-w-full divide-y divide-gray-200 dark:divide-gray-700'>
          <thead className='bg-gray-50 dark:bg-gray-900'>
            <tr>
              <th className='px-4 py-2 text-left'>时间</th>
              <th className='px-4 py-2 text-left'>动作</th>
              <th className='px-4 py-2 text-left'>告警</th>
              <th className='px-4 py-2 text-left'>状态</th>
              <th className='px-4 py-2 text-left'>详情</th>
            </tr>
          </thead>
          <tbody className='divide-y divide-gray-200 dark:divide-gray-700'>
            {events.map((e, idx) => (
              <tr key={idx}>
                <td className='px-4 py-2 text-sm'>{new Date(e.timestamp).toLocaleString()}</td>
                <td className='px-4 py-2 text-sm font-medium'>{e.action}</td>
                <td className='px-4 py-2 text-sm'>{e.alert_id || '-'}</td>
                <td className='px-4 py-2 text-sm'>{e.status || '-'}</td>
                <td className='px-4 py-2 text-sm'>{JSON.stringify(e.details || {}).slice(0, 80)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  )
}
