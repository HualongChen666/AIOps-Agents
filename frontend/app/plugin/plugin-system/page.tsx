'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { KpiCard } from '@/components/ui/KpiCard'
import { DataTable } from '@/components/ui/DataTable'
import api from '@/lib/api'
import toast from 'react-hot-toast'
import { RefreshCw, Power, PowerOff, Boxes, CheckCircle2, PlugZap, Layers } from 'lucide-react'

interface RegisteredPlugin {
  plugin_id: string
  name: string
  version: string
  plugin_type: string
  status: string
  author: string
  dependencies: string[]
}

interface SystemSummary {
  total_plugins_registered: number
  total_plugins_enabled: number
  total_interfaces_defined: number
  system_version: string
  plugins_by_type: Record<string, number>
  plugins_by_status: Record<string, number>
}

const STATUS_VARIANT: Record<string, 'default' | 'secondary' | 'destructive'> = {
  enabled: 'default',
  installed: 'secondary',
  disabled: 'secondary',
  unloaded: 'secondary',
  loading: 'default',
  error: 'destructive',
}

export default function PluginSystemPage() {
  const queryClient = useQueryClient()

  const statusQuery = useQuery<{ status: string; data: SystemSummary; timestamp: string }>({
    queryKey: ['plugin-system-status'],
    queryFn: async () => (await api.get('/api/plugin-system/status')).data,
  })

  const pluginsQuery = useQuery<{ data: { plugins: RegisteredPlugin[]; count: number } }>({
    queryKey: ['plugin-system-plugins'],
    queryFn: async () => (await api.get('/api/plugin-system/plugins')).data,
  })

  const toggleMutation = useMutation({
    mutationFn: async ({ id, enable }: { id: string; enable: boolean }) => {
      const action = enable ? 'enable' : 'disable'
      const res = await api.post(`/api/plugin-system/plugin/${id}/${action}`)
      return res.data
    },
    onSuccess: () => {
      toast.success('插件状态已更新')
      queryClient.invalidateQueries({ queryKey: ['plugin-system-plugins'] })
      queryClient.invalidateQueries({ queryKey: ['plugin-system-status'] })
    },
    onError: (e: any) => toast.error(e?.response?.data?.detail || '操作失败'),
  })

  const summary = statusQuery.data?.data
  const plugins = pluginsQuery.data?.data?.plugins ?? []

  const columns = [
    { key: 'plugin_id' as const, label: 'Plugin ID', sortable: true },
    { key: 'name' as const, label: '名称', sortable: true },
    { key: 'version' as const, label: '版本' },
    { key: 'plugin_type' as const, label: '类型', filterable: true, render: (v: string) => <Badge variant="outline">{v}</Badge> },
    {
      key: 'status' as const,
      label: '状态',
      filterable: true,
      render: (v: string) => <Badge variant={STATUS_VARIANT[v] ?? 'secondary'}>{v}</Badge>,
    },
    {
      key: 'dependencies' as const,
      label: '依赖',
      render: (v: string[]) => (v && v.length ? v.join(', ') : '-'),
    },
    {
      key: 'plugin_id' as const,
      label: '操作',
      render: (_v: string, row: RegisteredPlugin) => (
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={() => toggleMutation.mutate({ id: row.plugin_id, enable: true })}>
            <Power className="h-3 w-3 mr-1" /> 启用
          </Button>
          <Button size="sm" variant="ghost" onClick={() => toggleMutation.mutate({ id: row.plugin_id, enable: false })}>
            <PowerOff className="h-3 w-3 mr-1" /> 禁用
          </Button>
        </div>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">插件系统</h1>
        <Button variant="outline" onClick={() => { statusQuery.refetch(); pluginsQuery.refetch() }}>
          <RefreshCw className={`h-4 w-4 mr-2 ${statusQuery.isFetching ? 'animate-spin' : ''}`} />
          刷新
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <KpiCard title="已注册" value={summary?.total_plugins_registered ?? 0} icon={Boxes} />
        <KpiCard title="已启用" value={summary?.total_plugins_enabled ?? 0} icon={CheckCircle2} />
        <KpiCard title="接口数" value={summary?.total_interfaces_defined ?? 0} icon={PlugZap} />
        <KpiCard title="版本" value={summary?.system_version ?? '-'} icon={Layers} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>插件 ({pluginsQuery.data?.data?.count ?? 0})</CardTitle>
        </CardHeader>
        <CardContent>
          {pluginsQuery.isLoading ? (
            <p className="py-6 text-center text-gray-500">加载中...</p>
          ) : pluginsQuery.isError ? (
            <p className="py-6 text-center text-red-600">加载插件失败</p>
          ) : (
            <DataTable data={plugins} columns={columns} emptyMessage="暂无已注册插件" filterable={false} />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
