'use client'

import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import api from '@/lib/api'
import toast from 'react-hot-toast'
import { PlusCircle, Search } from 'lucide-react'

const SPEC_TYPES = ['monitoring', 'integration', 'ai']

export default function PluginInterfacePage() {
  const [interfaceId, setInterfaceId] = useState('')
  const [interfaceName, setInterfaceName] = useState('')
  const [methodsText, setMethodsText] = useState('[\n  {"name": "initialize", "parameters": [{"name": "config", "type": "dict"}], "returns": "bool"}\n]')
  const [eventsText, setEventsText] = useState('[\n  {"name": "on_ready", "data": "metadata"}\n]')
  const [specType, setSpecType] = useState('monitoring')

  const defineMutation = useMutation({
    mutationFn: async () => {
      if (!interfaceId.trim() || !interfaceName.trim()) throw new Error('接口 ID 与名称必填')
      let methods: any[]
      let events: any[]
      try {
        methods = JSON.parse(methodsText)
        events = JSON.parse(eventsText)
      } catch {
        throw new Error('methods / events 必须是合法 JSON 数组')
      }
      const res = await api.post(
        '/api/plugin-system/interface/define',
        { methods, events },
        { params: { interface_id: interfaceId.trim(), interface_name: interfaceName.trim() } }
      )
      return res.data
    },
    onSuccess: (data) => {
      toast.success(`接口已定义: ${data?.data?.interface_id} (${data?.data?.method_count} 方法)`)
      setInterfaceId('')
      setInterfaceName('')
    },
    onError: (e: any) => toast.error(e?.response?.data?.detail || e?.message || '定义失败'),
  })

  const specMutation = useMutation({
    mutationFn: async (type: string) => (await api.get(`/api/plugin-system/interface/spec/${type}`)).data,
    onError: () => toast.error('获取接口规范失败'),
  })

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900">插件接口</h1>

      <Tabs defaultValue="define">
        <TabsList>
          <TabsTrigger value="define">定义接口</TabsTrigger>
          <TabsTrigger value="spec">接口规范</TabsTrigger>
        </TabsList>

        <TabsContent value="define">
          <Card>
            <CardHeader>
              <CardTitle>定义插件接口</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                <div>
                  <Label htmlFor="i-id">接口 ID *</Label>
                  <Input id="i-id" value={interfaceId} onChange={(e) => setInterfaceId(e.target.value)} placeholder="data-collector" />
                </div>
                <div>
                  <Label htmlFor="i-name">接口名称 *</Label>
                  <Input id="i-name" value={interfaceName} onChange={(e) => setInterfaceName(e.target.value)} placeholder="Data Collector" />
                </div>
              </div>
              <div>
                <Label htmlFor="i-methods">methods (JSON 数组)</Label>
                <textarea
                  id="i-methods"
                  className="mt-1 w-full rounded-md border border-gray-300 p-2 font-mono text-sm"
                  rows={6}
                  value={methodsText}
                  onChange={(e) => setMethodsText(e.target.value)}
                />
              </div>
              <div>
                <Label htmlFor="i-events">events (JSON 数组)</Label>
                <textarea
                  id="i-events"
                  className="mt-1 w-full rounded-md border border-gray-300 p-2 font-mono text-sm"
                  rows={4}
                  value={eventsText}
                  onChange={(e) => setEventsText(e.target.value)}
                />
              </div>
              <Button onClick={() => defineMutation.mutate()} disabled={defineMutation.isPending}>
                <PlusCircle className="h-4 w-4 mr-2" />
                {defineMutation.isPending ? '提交中...' : '定义接口'}
              </Button>
              {defineMutation.data && (
                <pre className="rounded bg-gray-50 p-3 text-xs">{JSON.stringify(defineMutation.data, null, 2)}</pre>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="spec">
          <Card>
            <CardHeader>
              <CardTitle>接口规范模板</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-end gap-2">
                <div className="w-48">
                  <Label htmlFor="spec-type">接口类型</Label>
                  <Input id="spec-type" value={specType} onChange={(e) => setSpecType(e.target.value)} list="spec-types" />
                  <datalist id="spec-types">
                    {SPEC_TYPES.map((t) => (
                      <option key={t} value={t} />
                    ))}
                  </datalist>
                </div>
                <Button onClick={() => specMutation.mutate(specType)} disabled={specMutation.isPending}>
                  <Search className="h-4 w-4 mr-2" /> 查询规范
                </Button>
              </div>
              {specMutation.data ? (
                <pre className="max-h-96 overflow-auto rounded bg-gray-50 p-3 text-xs">
                  {JSON.stringify(specMutation.data?.data ?? specMutation.data, null, 2)}
                </pre>
              ) : (
                <p className="text-sm text-gray-500">选择类型后点击“查询规范”，可查看该类型插件必须实现的方法与事件。</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
