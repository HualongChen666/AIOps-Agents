'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { KpiCard } from '@/components/ui/KpiCard'
import api from '@/lib/api'
import toast from 'react-hot-toast'
import { RefreshCw, Database, Layers, Table2, Code2, Play } from 'lucide-react'

interface Partition {
  name: string
  kind: string
  modulus: number | null
  remainder: number | null
  range_from: string | null
  range_to: string | null
  values: string[]
}

interface Plan {
  configured: boolean
  schema: string
  table: string | null
  column: string | null
  column_type: string
  strategy: string | null
  columns: { name: string; type: string }[]
  partitions: Partition[]
  partition_count: number
  updated_at: string | null
}

const EXAMPLE_PARTITIONS = `[
  {"name": "orders_2024", "range_from": "2024-01-01", "range_to": "2025-01-01"},
  {"name": "orders_2025", "range_from": "2025-01-01", "range_to": "2026-01-01"}
]`

export default function PostgresqlShardPage() {
  const queryClient = useQueryClient()
  const [form, setForm] = useState({
    table: 'orders',
    strategy: 'hash',
    column: 'customer_id',
    column_type: 'BIGINT',
    schema: 'public',
    partition_count: 4,
  })
  const [partitionsJson, setPartitionsJson] = useState(EXAMPLE_PARTITIONS)
  const [ddl, setDdl] = useState<string | null>(null)

  const planQuery = useQuery<Plan>({
    queryKey: ['pg-shard-plan'],
    queryFn: async () => (await api.get('/api/v1/database/postgresql-shard/plan')).data,
  })
  const plan = planQuery.data

  const configureMutation = useMutation({
    mutationFn: async () => {
      const payload: Record<string, unknown> = {
        table: form.table.trim(),
        strategy: form.strategy,
        column: form.column.trim(),
        column_type: form.column_type.trim() || 'BIGINT',
        schema: form.schema.trim() || 'public',
      }
      if (form.strategy === 'hash') {
        payload.partition_count = Number(form.partition_count)
      } else {
        payload.partitions = JSON.parse(partitionsJson)
      }
      const res = await api.post('/api/v1/database/postgresql-shard/plan', payload)
      return res.data as Plan
    },
    onSuccess: (data) => {
      toast.success(`已生成 ${data.partition_count} 个分区定义`)
      setDdl(null)
      queryClient.invalidateQueries({ queryKey: ['pg-shard-plan'] })
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || err.message || '配置失败'),
  })

  const ddlMutation = useMutation({
    mutationFn: async () => (await api.get('/api/v1/database/postgresql-shard/ddl')).data,
    onSuccess: (data) => setDdl(data.ddl),
    onError: (err: any) => toast.error(err?.response?.data?.detail || '生成 DDL 失败'),
  })

  const applyMutation = useMutation({
    mutationFn: async () => (await api.post('/api/v1/database/postgresql-shard/apply', {})).data,
    onSuccess: (data) => toast.success(`已执行 ${data.statements_executed} 条语句`),
    onError: (err: any) => {
      const detail = err?.response?.data?.detail
      toast.error(typeof detail === 'string' ? detail : detail?.reason || '执行失败')
    },
  })

  const resetMutation = useMutation({
    mutationFn: async () => (await api.delete('/api/v1/database/postgresql-shard/plan')).data,
    onSuccess: () => {
      toast.success('已重置分区方案')
      setDdl(null)
      queryClient.invalidateQueries({ queryKey: ['pg-shard-plan'] })
    },
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">PostgreSQL 分区</h1>
        <Button variant="outline" onClick={() => planQuery.refetch()}>
          <RefreshCw className={`h-4 w-4 mr-2 ${planQuery.isFetching ? 'animate-spin' : ''}`} />
          刷新
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <KpiCard title="目标表" value={plan?.table ?? '-'} icon={Table2} />
        <KpiCard title="分区策略" value={plan?.strategy ?? '-'} icon={Database} />
        <KpiCard title="分区数" value={plan?.partition_count ?? 0} icon={Layers} />
        <KpiCard title="分区键" value={plan?.column ?? '-'} icon={Code2} />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>声明式分区方案</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label>表名</Label>
                <Input value={form.table} onChange={(e) => setForm({ ...form, table: e.target.value })} />
              </div>
              <div className="space-y-1">
                <Label>Schema</Label>
                <Input value={form.schema} onChange={(e) => setForm({ ...form, schema: e.target.value })} />
              </div>
            </div>
            <div className="space-y-1">
              <Label>分区策略</Label>
              <Select value={form.strategy} onChange={(e) => setForm({ ...form, strategy: e.target.value })}>
                <option value="hash">HASH</option>
                <option value="range">RANGE</option>
                <option value="list">LIST</option>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label>分区键列</Label>
                <Input value={form.column} onChange={(e) => setForm({ ...form, column: e.target.value })} />
              </div>
              <div className="space-y-1">
                <Label>列类型</Label>
                <Input value={form.column_type} onChange={(e) => setForm({ ...form, column_type: e.target.value })} />
              </div>
            </div>
            {form.strategy === 'hash' ? (
              <div className="space-y-1">
                <Label>分区数量（MODULUS）</Label>
                <Input type="number" min={1} value={form.partition_count} onChange={(e) => setForm({ ...form, partition_count: Number(e.target.value) })} />
              </div>
            ) : (
              <div className="space-y-1">
                <Label>分区定义 (JSON)</Label>
                <textarea
                  className="w-full rounded-md border border-gray-300 p-2 text-xs font-mono"
                  rows={6}
                  value={partitionsJson}
                  onChange={(e) => setPartitionsJson(e.target.value)}
                />
              </div>
            )}
            <div className="flex gap-2">
              <Button disabled={configureMutation.isPending} onClick={() => configureMutation.mutate()}>
                生成方案
              </Button>
              <Button variant="outline" onClick={() => resetMutation.mutate()}>重置</Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>DDL 预览</CardTitle>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" disabled={!plan?.configured || ddlMutation.isPending} onClick={() => ddlMutation.mutate()}>
                  生成
                </Button>
                <Button size="sm" disabled={!plan?.configured || applyMutation.isPending} onClick={() => applyMutation.mutate()}>
                  <Play className="h-4 w-4 mr-1" /> 执行
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {ddl ? (
              <pre className="max-h-80 overflow-auto rounded bg-gray-900 p-3 text-xs text-gray-100">{ddl}</pre>
            ) : (
              <p className="text-sm text-gray-500">点击“生成”查看可执行的 PostgreSQL 分区 DDL。</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>分区明细</CardTitle>
        </CardHeader>
        <CardContent>
          {plan?.partitions?.length ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-gray-500">
                    <th className="py-2">分区</th>
                    <th className="py-2">类型</th>
                    <th className="py-2">定义</th>
                  </tr>
                </thead>
                <tbody>
                  {plan.partitions.map((p) => (
                    <tr key={p.name} className="border-b">
                      <td className="py-2 font-medium">{p.name}</td>
                      <td className="py-2"><Badge variant="secondary">{p.kind}</Badge></td>
                      <td className="py-2">
                        {p.kind === 'hash'
                          ? `MODULUS ${p.modulus}, REMAINDER ${p.remainder}`
                          : p.kind === 'range'
                            ? `[${p.range_from}, ${p.range_to})`
                            : p.values.join(', ')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-gray-500">尚未定义分区</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
