'use client'

import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { KpiCard } from '@/components/ui/KpiCard'
import api from '@/lib/api'
import { RefreshCw, FileCode2, Boxes, Hammer } from 'lucide-react'

interface Template {
  template_id: string
  template_name: string
  template_type: string
  description: string
}

interface TemplatesResponse {
  status: string
  data: { templates: Template[]; count: number }
  timestamp: string
}

interface SdkStatus {
  available_templates: number
  generated_plugins: number
  template_types: string[]
  generated_plugin_ids: string[]
}

export default function PluginTemplatePage() {
  const templatesQuery = useQuery<TemplatesResponse>({
    queryKey: ['plugin-sdk-templates'],
    queryFn: async () => (await api.get('/api/plugin-sdk/templates')).data,
  })

  const statusQuery = useQuery<{ status: string; data: SdkStatus; timestamp: string }>({
    queryKey: ['plugin-sdk-status'],
    queryFn: async () => (await api.get('/api/plugin-sdk/status')).data,
  })

  const templates = templatesQuery.data?.data?.templates ?? []
  const sdk = statusQuery.data?.data

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">插件模板</h1>
        <Button variant="outline" onClick={() => { templatesQuery.refetch(); statusQuery.refetch() }}>
          <RefreshCw className={`h-4 w-4 mr-2 ${templatesQuery.isFetching ? 'animate-spin' : ''}`} />
          刷新
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
        <KpiCard title="可用模板" value={sdk?.available_templates ?? templates.length} icon={FileCode2} />
        <KpiCard title="已生成插件" value={sdk?.generated_plugins ?? 0} icon={Hammer} />
        <KpiCard title="模板类型" value={sdk?.template_types?.length ?? 0} icon={Boxes} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>模板列表 ({templates.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {templatesQuery.isLoading ? (
            <p className="py-6 text-center text-gray-500">加载中...</p>
          ) : templatesQuery.isError ? (
            <p className="py-6 text-center text-red-600">加载模板失败</p>
          ) : templates.length === 0 ? (
            <p className="py-6 text-center text-gray-500">暂无可用模板</p>
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {templates.map((t) => (
                <div key={t.template_id} className="rounded-lg border p-4">
                  <div className="flex items-center justify-between">
                    <h3 className="font-semibold">{t.template_name}</h3>
                    <Badge variant="outline">{t.template_type}</Badge>
                  </div>
                  <p className="mt-2 text-sm text-gray-600">{t.description || '无描述'}</p>
                  <p className="mt-2 text-xs text-gray-400">ID: {t.template_id}</p>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {sdk && sdk.generated_plugin_ids?.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>已生成插件 ID</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {sdk.generated_plugin_ids.map((id) => (
              <Badge key={id} variant="secondary">
                {id}
              </Badge>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
