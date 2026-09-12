'use client'

import { useEffect, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select } from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import api from '@/lib/api'
import toast from 'react-hot-toast'
import { Save, RefreshCw } from 'lucide-react'

interface Plugin {
  id: string
  name: string
  version: string
  status: string
}

interface PluginConfig {
  id: string
  plugin_id: string
  plugin_name: string
  config_data: Record<string, any>
  config_version: number
  is_active: boolean
  description: string | null
  updated_at: string
  updated_by: string | null
}

export default function PluginConfigurationPage() {
  const queryClient = useQueryClient()
  const [selected, setSelected] = useState('')
  const [configText, setConfigText] = useState('{}')
  const [description, setDescription] = useState('')
  const [isActive, setIsActive] = useState(true)

  const pluginsQuery = useQuery<{ plugins: Plugin[] }>({
    queryKey: ['plugins', 'config-select'],
    queryFn: async () => (await api.get('/api/plugins/', { params: { limit: 200 } })).data,
  })

  const configQuery = useQuery<PluginConfig>({
    queryKey: ['plugin-config', selected],
    enabled: !!selected,
    retry: false,
    queryFn: async () => (await api.get(`/api/plugins/${selected}/config`)).data,
  })

  useEffect(() => {
    if (configQuery.data) {
      setConfigText(JSON.stringify(configQuery.data.config_data ?? {}, null, 2))
      setDescription(configQuery.data.description ?? '')
      setIsActive(configQuery.data.is_active)
    }
  }, [configQuery.data])

  const saveMutation = useMutation({
    mutationFn: async () => {
      let parsed: Record<string, any>
      try {
        parsed = JSON.parse(configText)
      } catch {
        throw new Error('配置必须是合法 JSON')
      }
      const res = await api.put(`/api/plugins/${selected}/config`, {
        config_data: parsed,
        is_active: isActive,
        description: description || null,
      })
      return res.data
    },
    onSuccess: () => {
      toast.success('插件配置已保存')
      queryClient.invalidateQueries({ queryKey: ['plugin-config', selected] })
    },
    onError: (e: any) => toast.error(e?.response?.data?.detail || e?.message || '保存失败'),
  })

  const plugins = pluginsQuery.data?.plugins ?? []
  const config = configQuery.data

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">插件配置</h1>
        <Button variant="outline" onClick={() => configQuery.refetch()} disabled={!selected}>
          <RefreshCw className={`h-4 w-4 mr-2 ${configQuery.isFetching ? 'animate-spin' : ''}`} />
          重新加载
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>选择插件</CardTitle>
        </CardHeader>
        <CardContent>
          <Select value={selected} onChange={(e) => setSelected(e.target.value)} className="max-w-md" label="插件">
            <option value="">-- 请选择 --</option>
            {plugins.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} (v{p.version})
              </option>
            ))}
          </Select>
        </CardContent>
      </Card>

      {selected && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>配置内容</CardTitle>
            {config && (
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <Badge variant="outline">v{config.config_version}</Badge>
                {config.updated_by && <span>更新者: {config.updated_by}</span>}
              </div>
            )}
          </CardHeader>
          <CardContent className="space-y-4">
            {configQuery.isError ? (
              <div className="rounded border border-yellow-200 bg-yellow-50 p-3 text-yellow-800">
                该插件暂无配置记录（后端 GET /config 返回 404）。可先由插件执行/初始化流程创建配置。
              </div>
            ) : configQuery.isLoading ? (
              <div className="text-gray-500">加载配置中...</div>
            ) : (
              <>
                <div>
                  <Label htmlFor="cfg">config_data (JSON)</Label>
                  <textarea
                    id="cfg"
                    className="mt-1 w-full rounded-md border border-gray-300 p-2 font-mono text-sm"
                    rows={12}
                    value={configText}
                    onChange={(e) => setConfigText(e.target.value)}
                  />
                </div>
                <div>
                  <Label htmlFor="cfg-desc">描述</Label>
                  <textarea
                    id="cfg-desc"
                    className="mt-1 w-full rounded-md border border-gray-300 p-2 text-sm"
                    rows={2}
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                  />
                </div>
                <div className="flex items-center gap-3">
                  <Switch checked={isActive} onCheckedChange={setIsActive} />
                  <span className="text-sm text-gray-700">激活此配置</span>
                </div>
                <Button onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
                  <Save className="h-4 w-4 mr-2" />
                  {saveMutation.isPending ? '保存中...' : '保存配置'}
                </Button>
              </>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
