'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Select } from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { DataTable } from '@/components/ui/DataTable'
import { KpiCard } from '@/components/ui/KpiCard'
import api from '@/lib/api'
import toast from 'react-hot-toast'
import { RefreshCw, Play, Trash2, Package, CheckCircle2, AlertTriangle, Activity } from 'lucide-react'

interface Plugin {
  id: string
  name: string
  version: string
  description: string | null
  author: string | null
  plugin_type: string
  status: string
  created_at: string
  updated_at: string
  created_by: string | null
}

interface PluginListResponse {
  total: number
  plugins: Plugin[]
}

interface PluginStats {
  total_plugins: number
  active_plugins: number
  inactive_plugins: number
  error_plugins: number
  total_executions: number
  successful_executions: number
  failed_executions: number
}

const STATUS_VARIANT: Record<string, 'default' | 'secondary' | 'destructive'> = {
  active: 'default',
  inactive: 'secondary',
  loading: 'default',
  error: 'destructive',
}

export default function PluginListPage() {
  const queryClient = useQueryClient()
  const [statusFilter, setStatusFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [runTarget, setRunTarget] = useState<Plugin | null>(null)
  const [runInput, setRunInput] = useState('')

  const pluginsQuery = useQuery<PluginListResponse>({
    queryKey: ['plugins', statusFilter, typeFilter],
    queryFn: async () => {
      const params: Record<string, string> = { limit: '200' }
      if (statusFilter) params.status = statusFilter
      if (typeFilter) params.plugin_type = typeFilter
      const res = await api.get('/api/plugins/', { params })
      return res.data
    },
  })

  const statsQuery = useQuery<PluginStats>({
    queryKey: ['plugin-stats'],
    queryFn: async () => {
      const res = await api.get('/api/plugins/stats')
      return res.data
    },
  })

  const runMutation = useMutation({
    mutationFn: async ({ name, input }: { name: string; input: Record<string, any> }) => {
      const res = await api.post(`/api/plugins/${encodeURIComponent(name)}/run`, { input_data: input })
      return res.data
    },
    onSuccess: (data) => {
      toast.success(data?.success ? `插件执行成功 (${data.duration_ms ?? 0} ms)` : '插件执行完成但返回失败')
      setRunTarget(null)
      setRunInput('')
      queryClient.invalidateQueries({ queryKey: ['plugin-stats'] })
    },
    onError: () => toast.error('插件执行失败'),
  })

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/plugins/${id}`)
    },
    onSuccess: () => {
      toast.success('插件已删除')
      queryClient.invalidateQueries({ queryKey: ['plugins'] })
      queryClient.invalidateQueries({ queryKey: ['plugin-stats'] })
    },
    onError: () => toast.error('删除失败（需要管理员角色）'),
  })

  const submitRun = () => {
    if (!runTarget) return
    let parsed: Record<string, any> = {}
    if (runInput.trim()) {
      try {
        parsed = JSON.parse(runInput)
      } catch {
        toast.error('输入数据必须是合法 JSON')
        return
      }
    }
    runMutation.mutate({ name: runTarget.name, input: parsed })
  }

  const plugins = pluginsQuery.data?.plugins ?? []
  const stats = statsQuery.data

  const columns = [
    { key: 'name' as const, label: '名称', sortable: true },
    { key: 'version' as const, label: '版本' },
    {
      key: 'plugin_type' as const,
      label: '类型',
      filterable: true,
      render: (v: string) => <Badge variant="outline">{v}</Badge>,
    },
    {
      key: 'status' as const,
      label: '状态',
      filterable: true,
      render: (v: string) => <Badge variant={STATUS_VARIANT[v] ?? 'secondary'}>{v}</Badge>,
    },
    { key: 'author' as const, label: '作者', render: (v: string | null) => v || '-' },
    {
      key: 'created_at' as const,
      label: '创建时间',
      render: (v: string) => (v ? new Date(v).toLocaleString() : '-'),
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">插件列表</h1>
        <Button onClick={() => pluginsQuery.refetch()} variant="outline">
          <RefreshCw className={`h-4 w-4 mr-2 ${pluginsQuery.isFetching ? 'animate-spin' : ''}`} />
          刷新
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <KpiCard title="插件总数" value={stats?.total_plugins ?? 0} icon={Package} />
        <KpiCard title="活跃插件" value={stats?.active_plugins ?? 0} icon={CheckCircle2} />
        <KpiCard title="执行次数" value={stats?.total_executions ?? 0} icon={Activity} />
        <KpiCard title="失败次数" value={stats?.failed_executions ?? 0} icon={AlertTriangle} />
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>已注册插件 ({pluginsQuery.data?.total ?? 0})</CardTitle>
          <div className="flex gap-2">
            <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="w-36">
              <option value="">全部状态</option>
              <option value="active">active</option>
              <option value="inactive">inactive</option>
              <option value="loading">loading</option>
              <option value="error">error</option>
            </Select>
            <Select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} className="w-36">
              <option value="">全部类型</option>
              <option value="collector">collector</option>
              <option value="analyzer">analyzer</option>
              <option value="executor">executor</option>
              <option value="storage">storage</option>
              <option value="notifier">notifier</option>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          {pluginsQuery.isLoading ? (
            <div className="py-8 text-center text-gray-500">加载中...</div>
          ) : pluginsQuery.isError ? (
            <div className="py-8 text-center text-red-600">加载插件列表失败</div>
          ) : (
            <DataTable
              data={plugins}
              columns={columns}
              emptyMessage="暂无插件"
              onRowClick={(row) => setRunTarget(row)}
              filterable={false}
            />
          )}
          {plugins.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-2">
              {plugins.slice(0, 12).map((p) => (
                <span key={p.id} className="inline-flex items-center gap-1">
                  <Button size="sm" variant="outline" onClick={() => setRunTarget(p)}>
                    <Play className="h-3 w-3 mr-1" /> {p.name}
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    aria-label={`删除插件 ${p.name}`}
                    onClick={() => {
                      if (confirm(`确认删除插件 ${p.name}？`)) deleteMutation.mutate(p.id)
                    }}
                  >
                    <Trash2 className="h-3 w-3 text-red-600" />
                  </Button>
                </span>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={!!runTarget} onOpenChange={(open) => !open && setRunTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>运行插件: {runTarget?.name}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <Label htmlFor="run-input">输入数据 (JSON，可选)</Label>
              <textarea
                id="run-input"
                className="mt-1 w-full rounded-md border border-gray-300 p-2 font-mono text-sm"
                rows={5}
                value={runInput}
                onChange={(e) => setRunInput(e.target.value)}
                placeholder='{"target": "host-1"}'
              />
            </div>
            {runMutation.data && (
              <pre className="max-h-40 overflow-auto rounded bg-gray-50 p-2 text-xs">
                {JSON.stringify(runMutation.data, null, 2)}
              </pre>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRunTarget(null)}>
              取消
            </Button>
            <Button onClick={submitRun} disabled={runMutation.isPending}>
              {runMutation.isPending ? '执行中...' : '执行'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
