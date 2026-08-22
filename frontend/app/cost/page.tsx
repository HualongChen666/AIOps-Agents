'use client'

import { useEffect, useState } from 'react'
import api from '@/lib/api'

interface CostItem {
  date: string
  amount: number
}

interface BudgetStatus {
  budget?: number
  used?: number
  remaining?: number
  status?: string
}

export default function CostPage() {
  const [costs, setCosts] = useState<CostItem[]>([])
  const [budget, setBudget] = useState<BudgetStatus>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      api.get('/api/cost/collect').catch(() => ({ data: { costs: [] } })),
      api.get('/api/cost/budget').catch(() => ({ data: {} })),
    ])
      .then(([costRes, budgetRes]) => {
        setCosts(costRes.data?.costs || [])
        setBudget(budgetRes.data || {})
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  const total = costs.reduce((s, c) => s + (c.amount || 0), 0)
  const remaining = budget.remaining || 0
  const cap = budget.budget || 0

  if (loading) return <div className='p-6'>加载中...</div>
  if (error) return <div className='p-6 text-red-600'>错误: {error}</div>

  return (
    <main className='p-6 space-y-6 bg-gray-100 dark:bg-gray-900 min-h-screen'>
      <h1 className='text-2xl font-bold text-gray-900 dark:text-gray-100'>成本看板</h1>
      <div className='grid grid-cols-1 md:grid-cols-3 gap-4'>
        <div className='bg-white dark:bg-gray-800 p-4 rounded shadow'>
          <div className='text-sm text-gray-500'>累计成本</div>
          <div className='text-2xl font-bold'>${total.toFixed(2)}</div>
        </div>
        <div className='bg-white dark:bg-gray-800 p-4 rounded shadow'>
          <div className='text-sm text-gray-500'>预算</div>
          <div className='text-2xl font-bold'>${cap.toFixed(2)}</div>
        </div>
        <div className='bg-white dark:bg-gray-800 p-4 rounded shadow'>
          <div className='text-sm text-gray-500'>剩余</div>
          <div className='text-2xl font-bold'>${remaining.toFixed(2)}</div>
        </div>
      </div>
      <div className='bg-white dark:bg-gray-800 rounded shadow p-4'>
        <h2 className='text-lg font-semibold mb-2'>每日成本</h2>
        <table className='min-w-full'>
          <thead className='bg-gray-50 dark:bg-gray-900'>
            <tr>
              <th className='px-4 py-2 text-left'>日期</th>
              <th className='px-4 py-2 text-left'>金额</th>
            </tr>
          </thead>
          <tbody>
            {costs.map((c, i) => (
              <tr key={i}>
                <td className='px-4 py-2 text-sm'>{c.date}</td>
                <td className='px-4 py-2 text-sm'>${(c.amount || 0).toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className='bg-white dark:bg-gray-800 rounded shadow p-4'>
        <h2 className='text-lg font-semibold mb-2'>LLM Token / USD 成本</h2>
        <p className='text-sm text-gray-600'>
          实际金额来自 /api/cost/collect；Prometheus 指标 llm_cost_per_incident_usd 可按告警维度细分。
        </p>
      </div>
    </main>
  )
}
