'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import api from '@/lib/api'
import toast from 'react-hot-toast'
import { RefreshCw, PlayCircle, PauseCircle } from 'lucide-react'

interface Plugin {
  id: string
  name: string
  version: string
  plugin_type: string
  status: string
}

export default function PluginBatchOperationsPage() {
  const queryClient = useQueryClient()
  const [selected, setSelected] = useState<Set<string>>(new Set())

  const pluginsQuery = useQuery<{ plugins: Plugin[] }>({
    queryKey: ['plugins', 'batch'],
    queryFn: async () => (await api.get('/api/plugins/', { params: { limit: 200 } })).data,
  })

  const bulkMutation = useMutation({
    mutationFn: async (status: 'active' | 'inactive') => {
      const ids = Array.from(selected)
      const results = await Promise.allSettled(ids.map((id) => api.put(`/api/plugins/${id}`, { status })))
      const failed = results.filter((r) => r.status === 'rejected').length
      return { total: ids.length, failed }
    },
    onSuccess: ({ total, failed }) => {
      if (failed === 0) toast.success(`批量操作成功：${total} 个插件`)
      else toast.error(`批量操作完成：成功 ${total - failed}，失败 ${failed}`)
      setSelected(new Set())
      queryClient.invalidateQueries({ queryKey: ['plugins'] })
      queryClient.invalidateQueries({ queryKey: ['plugin-stats'] })
    },
    onError: () => toast.error('批量操作失败'),
  })

  const plugins = pluginsQuery.data?.plugins ?? []
  const allSelected = plugins.length > 0 && selected.size === plugins.length

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleAll = () => {
    setSelected(allSelected ? new Set() : new Set(plugins.map((p) => p.id)))
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">批量操作</h1>
        <Button variant="outline" onClick={() => pluginsQuery.refetch()}>
          <RefreshCw className={`h-4 w-4 mr-2 ${pluginsQuery.isFetching ? 'animate-spin' : ''}`} />
          刷新
        </Button>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>批量启用 / 停用插件 ({selected.size}/{plugins.length} 已选)</CardTitle>
          <div className="flex gap-2">
            <Button
              size="sm"
              onClick={() => bulkMutation.mutate('active')}
              disabled={selected.size === 0 || bulkMutation.isPending}
            >
              <PlayCircle className="h-4 w-4 mr-1" /> 批量启用
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => bulkMutation.mutate('inactive')}
              disabled={selected.size === 0 || bulkMutation.isPending}
            >
              <PauseCircle className="h-4 w-4 mr-1" /> 批量停用
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {pluginsQuery.isLoading ? (
            <p className="py-6 text-center text-gray-500">加载中...</p>
          ) : plugins.length === 0 ? (
            <p className="py-6 text-center text-gray-500">暂无插件</p>
          ) : (
            <div className="space-y-2">
              <label className="flex items-center gap-2 border-b pb-2 text-sm font-medium">
                <input type="checkbox" checked={allSelected} onChange={toggleAll} aria-label="全选" className="h-4 w-4" />
                全选
              </label>
              {plugins.map((p) => (
                <label key={p.id} className="flex items-center justify-between rounded border p-3">
                  <span className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={selected.has(p.id)}
                      onChange={() => toggle(p.id)}
                      aria-label={`选择 ${p.name}`}
                      className="h-4 w-4"
                    />
                    <span>
                      <span className="font-medium">{p.name}</span>
                      <span className="ml-2 text-xs text-gray-500">v{p.version} · {p.plugin_type}</span>
                    </span>
                  </span>
                  <Badge variant={p.status === 'active' ? 'default' : 'secondary'}>{p.status}</Badge>
                </label>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
