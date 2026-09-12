'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Select } from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { DataTable } from '@/components/ui/DataTable'
import api from '@/lib/api'
import toast from 'react-hot-toast'
import { Play, RefreshCw } from 'lucide-react'

interface Plugin {
  id: string
  name: string
  version: string
  status: string
  plugin_type: string
}

interface Execution {
  id: string
  plugin_name: string
  execution_type: string
  trigger_type: string
  success: boolean
  duration_ms: number | null
  error_message: string | null
  started_at: string
  executed_by: string | null
}

export default function PluginRunPage() {
  const queryClient = useQueryClient()
  const [selectedName, setSelectedName] = useState('')
  const [inputText, setInputText] = useState('{}')
  const [lastResult, setLastResult] = useState<any>(null)

  const pluginsQuery = useQuery<{ plugins: Plugin[] }>({
    queryKey: ['plugins', 'run-select'],
    queryFn: async () => (await api.get('/api/plugins/', { params: { limit: 200 } })).data,
  })

  const selected = (pluginsQuery.data?.plugins ?? []).find((p) => p.name === selectedName)

  const execQuery = useQuery<{ total: number; executions: Execution[] }>({
    queryKey: ['plugin-executions', selected?.id],
    enabled: !!selected?.id,
    queryFn: async () => (await api.get(`/api/plugins/${selected!.id}/executions`, { params: { limit: 50 } })).data,
  })

  const runMutation = useMutation({
    mutationFn: async () => {
      if (!selectedName) throw new Error('请先选择插件')
      let parsed: Record<string, any> = {}
      if (inputText.trim()) {
        try {
          parsed = JSON.parse(inputText)
        } catch {
          throw new Error('输入数据必须是合法 JSON')
        }
      }
      const res = await api.post(`/api/plugins/${encodeURIComponent(selectedName)}/run`, { input_data: parsed })
      return res.data
    },
    onSuccess: (data) => {
      setLastResult(data)
      toast.success(data?.success ? '执行成功' : '执行完成（返回失败）')
      queryClient.invalidateQueries({ queryKey: ['plugin-executions'] })
    },
    onError: (e: any) => toast.error(e?.response?.data?.detail || e?.message || '执行失败'),
  })

  const columns = [
    {
      key: 'success' as const,
      label: '结果',
      render: (v: boolean) => <Badge variant={v ? 'default' : 'destructive'}>{v ? '成功' : '失败'}</Badge>,
    },
    { key: 'execution_type' as const, label: '类型', filterable: true },
    { key: 'trigger_type' as const, label: '触发', filterable: true },
    { key: 'duration_ms' as const, label: '耗时(ms)', render: (v: number | null) => (v == null ? '-' : Math.round(v)) },
    { key: 'executed_by' as const, label: '执行者', render: (v: string | null) => v || '-' },
    { key: 'started_at' as const, label: '开始时间', render: (v: string) => (v ? new Date(v).toLocaleString() : '-') },
    { key: 'error_message' as const, label: '错误', render: (v: string | null) => v || '-' },
  ]

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900">插件运行</h1>

      <Card>
        <CardHeader>
          <CardTitle>执行插件</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <Select label="选择插件" value={selectedName} onChange={(e) => setSelectedName(e.target.value)}>
              <option value="">-- 请选择 --</option>
              {(pluginsQuery.data?.plugins ?? []).map((p) => (
                <option key={p.id} value={p.name}>
                  {p.name} (v{p.version}, {p.status})
                </option>
              ))}
            </Select>
            <div>
              <Label htmlFor="run-input">输入数据 (JSON)</Label>
              <textarea
                id="run-input"
                className="mt-1 w-full rounded-md border border-gray-300 p-2 font-mono text-sm"
                rows={4}
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
              />
            </div>
          </div>
          <Button onClick={() => runMutation.mutate()} disabled={runMutation.isPending || !selectedName}>
            <Play className="h-4 w-4 mr-2" />
            {runMutation.isPending ? '执行中...' : '运行'}
          </Button>
          {lastResult && (
            <div>
              <div className="text-sm text-gray-500">执行结果</div>
              <pre className="max-h-60 overflow-auto rounded bg-gray-50 p-3 text-xs">{JSON.stringify(lastResult, null, 2)}</pre>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>执行记录 {selected ? `- ${selected.name}` : ''}</CardTitle>
          <Button variant="outline" size="sm" onClick={() => execQuery.refetch()} disabled={!selected}>
            <RefreshCw className={`h-4 w-4 ${execQuery.isFetching ? 'animate-spin' : ''}`} />
          </Button>
        </CardHeader>
        <CardContent>
          {!selected ? (
            <p className="py-6 text-center text-gray-500">请选择插件以查看执行记录</p>
          ) : execQuery.isLoading ? (
            <p className="py-6 text-center text-gray-500">加载中...</p>
          ) : (
            <DataTable data={execQuery.data?.executions ?? []} columns={columns} emptyMessage="暂无执行记录" filterable={false} />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
