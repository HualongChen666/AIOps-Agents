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
import { RefreshCw, Boxes, Server, Network, Route as RouteIcon, Activity } from 'lucide-react'

interface ShardNode {
  node_id: string
  host: string
  port: number
  role: string
}

interface Shard {
  shard_id: string
  name: string
  strategy: string
  range_start?: string | null
  range_end?: string | null
  values: string[]
  nodes: ShardNode[]
  created_at: string
}

interface ShardingStatus {
  configured: boolean
  namespace: string
  strategy: string
  shard_key: string
  table_name: string | null
  virtual_nodes: number
  shard_count: number
  node_count: number
  ring_size: number
  shards: Shard[]
  updated_at: string | null
}

interface RouteResult {
  key: string
  shard_id: string
  shard_name: string
  strategy: string
  node: ShardNode | null
  replicas: ShardNode[]
  ring_point: number | null
}

interface BatchResult {
  strategy: string
  total_keys: number
  shard_count: number
  distribution: Record<string, number>
}

interface RebalanceResult {
  strategy: string
  shard_count: number
  virtual_nodes: number
  ring_size: number
  points_moved: number
  keys_total: number
  keys_moved: number
  ideal_share_percent: number
  shard_share_percent: Record<string, number>
  max_deviation_percent: number
  balanced: boolean
}

interface HealthNode extends ShardNode {
  shard_id: string
  status: string
  latency_ms?: number
  error?: string
}

interface HealthResult {
  configured: boolean
  nodes_total: number
  nodes_up: number
  nodes_down: number
  nodes: HealthNode[]
}

export default function ShardingPage() {
  const queryClient = useQueryClient()
  const [form, setForm] = useState({ strategy: 'hash', shard_count: 4, shard_key: 'id', virtual_nodes: 128 })
  const [routeKey, setRouteKey] = useState('')
  const [routeResult, setRouteResult] = useState<RouteResult | null>(null)
  const [batchKeys, setBatchKeys] = useState('')
  const [batchResult, setBatchResult] = useState<BatchResult | null>(null)
  const [rebalanceResult, setRebalanceResult] = useState<RebalanceResult | null>(null)
  const [healthResult, setHealthResult] = useState<HealthResult | null>(null)

  const statusQuery = useQuery<ShardingStatus>({
    queryKey: ['db-sharding-status'],
    queryFn: async () => (await api.get('/api/v1/database/sharding/status')).data,
  })

  const status = statusQuery.data

  const configureMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post('/api/v1/database/sharding/configure', {
        strategy: form.strategy,
        shard_count: Number(form.shard_count),
        shard_key: form.shard_key || 'id',
        virtual_nodes: Number(form.virtual_nodes),
      })
      return res.data as ShardingStatus
    },
    onSuccess: (data) => {
      toast.success(`已配置 ${data.shard_count} 个分片 (${data.strategy})`)
      queryClient.invalidateQueries({ queryKey: ['db-sharding-status'] })
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || '配置失败'),
  })

  const routeMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post('/api/v1/database/sharding/route', { key: routeKey })
      return res.data as RouteResult
    },
    onSuccess: (data) => setRouteResult(data),
    onError: (err: any) => toast.error(err?.response?.data?.detail || '路由失败'),
  })

  const batchMutation = useMutation({
    mutationFn: async () => {
      const keys = batchKeys
        .split(/[\s,]+/)
        .map((k) => k.trim())
        .filter(Boolean)
      if (keys.length === 0) throw new Error('请输入至少一个键')
      const res = await api.post('/api/v1/database/sharding/route/batch', { keys })
      return res.data as BatchResult
    },
    onSuccess: (data) => setBatchResult(data),
    onError: (err: any) => toast.error(err?.response?.data?.detail || err.message || '批量路由失败'),
  })

  const rebalanceMutation = useMutation({
    mutationFn: async () => {
      const keys = batchKeys
        .split(/[\s,]+/)
        .map((k) => k.trim())
        .filter(Boolean)
      const res = await api.post('/api/v1/database/sharding/rebalance', {
        keys,
        virtual_nodes: Number(form.virtual_nodes),
      })
      return res.data as RebalanceResult
    },
    onSuccess: (data) => {
      setRebalanceResult(data)
      toast.success(`重平衡完成，移动 ${data.points_moved} 个环点`)
      queryClient.invalidateQueries({ queryKey: ['db-sharding-status'] })
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || '重平衡失败'),
  })

  const healthMutation = useMutation({
    mutationFn: async () => (await api.get('/api/v1/database/sharding/health')).data as HealthResult,
    onSuccess: (data) => setHealthResult(data),
    onError: (err: any) => toast.error(err?.response?.data?.detail || '健康探测失败'),
  })

  const distMax = batchResult ? Math.max(1, ...Object.values(batchResult.distribution)) : 1

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">分片管理</h1>
        <Button variant="outline" onClick={() => statusQuery.refetch()}>
          <RefreshCw className={`h-4 w-4 mr-2 ${statusQuery.isFetching ? 'animate-spin' : ''}`} />
          刷新
        </Button>
      </div>

      {statusQuery.isError && (
        <div className="rounded border border-red-200 bg-red-50 p-3 text-red-700">无法获取分片拓扑</div>
      )}

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <KpiCard title="分片数" value={status?.shard_count ?? 0} icon={Boxes} />
        <KpiCard title="节点数" value={status?.node_count ?? 0} icon={Server} />
        <KpiCard title="环点数" value={status?.ring_size ?? 0} icon={Network} />
        <KpiCard title="策略" value={status?.strategy ?? '-'} icon={Activity} />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>配置拓扑</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1">
              <Label>分片策略</Label>
              <Select value={form.strategy} onChange={(e) => setForm({ ...form, strategy: e.target.value })}>
                <option value="hash">hash (一致性哈希)</option>
                <option value="modulo">modulo (取模)</option>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label>分片数量</Label>
                <Input type="number" min={1} value={form.shard_count} onChange={(e) => setForm({ ...form, shard_count: Number(e.target.value) })} />
              </div>
              <div className="space-y-1">
                <Label>虚拟节点</Label>
                <Input type="number" min={1} value={form.virtual_nodes} onChange={(e) => setForm({ ...form, virtual_nodes: Number(e.target.value) })} />
              </div>
            </div>
            <div className="space-y-1">
              <Label>分片键</Label>
              <Input value={form.shard_key} onChange={(e) => setForm({ ...form, shard_key: e.target.value })} placeholder="id" />
            </div>
            <Button disabled={configureMutation.isPending} onClick={() => configureMutation.mutate()}>
              应用配置
            </Button>
            {!status?.configured && <p className="text-xs text-amber-600">当前尚未配置分片拓扑，配置后路由/重平衡才可用。</p>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>键路由测试</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-2">
              <Input value={routeKey} onChange={(e) => setRouteKey(e.target.value)} placeholder="输入分片键 (如 user-123)" />
              <Button variant="outline" disabled={!routeKey || routeMutation.isPending} onClick={() => routeMutation.mutate()}>
                路由
              </Button>
            </div>
            {routeResult && (
              <div className="rounded border p-3 text-sm space-y-1">
                <div>键 <code className="font-mono">{routeResult.key}</code> → <Badge>{routeResult.shard_id}</Badge></div>
                <div className="text-gray-500">策略 {routeResult.strategy}{routeResult.ring_point !== null ? ` · 环点 ${routeResult.ring_point}` : ''}</div>
                <div className="text-gray-500">主节点 {routeResult.node ? `${routeResult.node.host}:${routeResult.node.port}` : '未配置节点'}</div>
              </div>
            )}
            <div className="space-y-1">
              <Label>批量键（逗号/换行分隔）</Label>
              <textarea
                className="w-full rounded-md border border-gray-300 p-2 text-sm font-mono"
                rows={3}
                value={batchKeys}
                onChange={(e) => setBatchKeys(e.target.value)}
                placeholder="user-1, user-2, user-3"
              />
            </div>
            <div className="flex gap-2">
              <Button variant="outline" disabled={batchMutation.isPending} onClick={() => batchMutation.mutate()}>
                计算分布
              </Button>
              <Button variant="outline" disabled={rebalanceMutation.isPending} onClick={() => rebalanceMutation.mutate()}>
                <RouteIcon className="h-4 w-4 mr-1" /> 重平衡
              </Button>
            </div>
            {batchResult && (
              <div className="space-y-2">
                <div className="text-sm text-gray-600">共 {batchResult.total_keys} 个键，分布于 {Object.keys(batchResult.distribution).length}/{batchResult.shard_count} 个分片</div>
                {Object.entries(batchResult.distribution).sort().map(([sid, count]) => (
                  <div key={sid} className="space-y-1">
                    <div className="flex justify-between text-sm">
                      <span>{sid}</span>
                      <span className="font-medium">{count}</span>
                    </div>
                    <div className="h-2 w-full rounded bg-gray-100">
                      <div className="h-2 rounded bg-blue-500" style={{ width: `${Math.round((count / distMax) * 100)}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            )}
            {rebalanceResult && (
              <div className="rounded border p-3 text-sm space-y-1">
                <div>虚拟节点 {rebalanceResult.virtual_nodes} · 环点 {rebalanceResult.ring_size}</div>
                <div>移动环点 {rebalanceResult.points_moved} · 移动键 {rebalanceResult.keys_moved}/{rebalanceResult.keys_total}</div>
                <div>最大偏差 {rebalanceResult.max_deviation_percent}%
                  <Badge className="ml-2" variant={rebalanceResult.balanced ? 'default' : 'destructive'}>
                    {rebalanceResult.balanced ? '均衡' : '待优化'}
                  </Badge>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>分片列表</CardTitle>
        </CardHeader>
        <CardContent>
          {status?.shards?.length ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-gray-500">
                    <th className="py-2">分片</th>
                    <th className="py-2">策略</th>
                    <th className="py-2">边界</th>
                    <th className="py-2">节点</th>
                  </tr>
                </thead>
                <tbody>
                  {status.shards.map((s) => (
                    <tr key={s.shard_id} className="border-b">
                      <td className="py-2 font-medium">{s.name}</td>
                      <td className="py-2">{s.strategy}</td>
                      <td className="py-2">{s.range_start != null || s.range_end != null ? `[${s.range_start ?? '-'}, ${s.range_end ?? '-'})` : s.values.length ? s.values.join(', ') : '-'}</td>
                      <td className="py-2">{s.nodes.length ? s.nodes.map((n) => `${n.host}:${n.port}`).join(', ') : '未绑定节点'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-gray-500">尚未配置分片</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>节点健康探测</CardTitle>
            <Button variant="outline" disabled={!status?.configured || healthMutation.isPending} onClick={() => healthMutation.mutate()}>
              探测
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {healthResult ? (
            <>
              <div className="mb-3 text-sm text-gray-600">在线 {healthResult.nodes_up} / {healthResult.nodes_total}</div>
              <div className="space-y-2">
                {healthResult.nodes.map((n, i) => (
                  <div key={`${n.node_id}-${i}`} className="flex items-center justify-between border-b pb-1 text-sm">
                    <span>{n.shard_id} · {n.host}:{n.port}</span>
                    <Badge variant={n.status === 'up' ? 'default' : 'destructive'}>
                      {n.status}{n.latency_ms != null ? ` · ${n.latency_ms}ms` : ''}
                    </Badge>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <p className="text-sm text-gray-500">点击“探测”对每个分片节点执行真实 TCP 连接检测。</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
