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
import { Code2, Package, FileCog } from 'lucide-react'

const INITIAL = { template_type: 'monitoring', plugin_name: '', class_name: '', version: '1.0.0', author: '' }

export default function PluginCodeGenerationPage() {
  const [form, setForm] = useState({ ...INITIAL })
  const [output, setOutput] = useState<string>('')

  const params = () => ({
    template_type: form.template_type,
    plugin_name: form.plugin_name.trim(),
    class_name: form.class_name.trim(),
    version: form.version.trim() || '1.0.0',
    author: form.author.trim() || 'Unknown',
  })

  const validate = () => {
    if (!form.plugin_name.trim() || !form.class_name.trim()) {
      toast.error('plugin_name 与 class_name 必填')
      return false
    }
    return true
  }

  const codeMutation = useMutation({
    mutationFn: async () => (await api.get('/api/plugin-sdk/generate/code', { params: params() })).data,
    onSuccess: (data) => {
      setOutput(data?.data?.code ?? JSON.stringify(data, null, 2))
      toast.success(`代码已生成 (${data?.data?.line_count ?? 0} 行)`)
    },
    onError: (e: any) => toast.error(e?.response?.data?.detail || '生成代码失败'),
  })

  const configMutation = useMutation({
    mutationFn: async () => (await api.get('/api/plugin-sdk/generate/config', { params: { template_type: form.template_type } })).data,
    onSuccess: (data) => {
      setOutput(JSON.stringify(data?.data ?? data, null, 2))
      toast.success('配置已生成')
    },
    onError: (e: any) => toast.error(e?.response?.data?.detail || '生成配置失败'),
  })

  const packageMutation = useMutation({
    mutationFn: async () =>
      (await api.post('/api/plugin-sdk/generate', {}, { params: params() })).data,
    onSuccess: (data) => {
      setOutput(JSON.stringify(data?.data ?? data, null, 2))
      toast.success('插件包已生成')
    },
    onError: (e: any) => toast.error(e?.response?.data?.detail || '生成插件包失败'),
  })

  const run = (kind: 'code' | 'config' | 'package') => {
    if (kind !== 'config' && !validate()) return
    if (kind === 'code') codeMutation.mutate()
    else if (kind === 'config') configMutation.mutate()
    else packageMutation.mutate()
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900">代码生成</h1>

      <Card>
        <CardHeader>
          <CardTitle>生成参数</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <div>
            <Label htmlFor="g-tpl">模板类型</Label>
            <Input id="g-tpl" value={form.template_type} onChange={(e) => setForm({ ...form, template_type: e.target.value })} />
          </div>
          <div>
            <Label htmlFor="g-name">插件名称 *</Label>
            <Input id="g-name" value={form.plugin_name} onChange={(e) => setForm({ ...form, plugin_name: e.target.value })} placeholder="CPU Monitor" />
          </div>
          <div>
            <Label htmlFor="g-class">类名 *</Label>
            <Input id="g-class" value={form.class_name} onChange={(e) => setForm({ ...form, class_name: e.target.value })} placeholder="CpuMonitorPlugin" />
          </div>
          <div>
            <Label htmlFor="g-version">版本</Label>
            <Input id="g-version" value={form.version} onChange={(e) => setForm({ ...form, version: e.target.value })} />
          </div>
          <div>
            <Label htmlFor="g-author">作者</Label>
            <Input id="g-author" value={form.author} onChange={(e) => setForm({ ...form, author: e.target.value })} />
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="code">
        <TabsList>
          <TabsTrigger value="code">生成代码</TabsTrigger>
          <TabsTrigger value="config">生成配置</TabsTrigger>
          <TabsTrigger value="package">生成插件包</TabsTrigger>
        </TabsList>

        <TabsContent value="code">
          <Button onClick={() => run('code')} disabled={codeMutation.isPending}>
            <Code2 className="h-4 w-4 mr-2" /> {codeMutation.isPending ? '生成中...' : '生成插件代码'}
          </Button>
        </TabsContent>

        <TabsContent value="config">
          <Button onClick={() => run('config')} disabled={configMutation.isPending}>
            <FileCog className="h-4 w-4 mr-2" /> {configMutation.isPending ? '生成中...' : '生成插件配置'}
          </Button>
        </TabsContent>

        <TabsContent value="package">
          <Button onClick={() => run('package')} disabled={packageMutation.isPending}>
            <Package className="h-4 w-4 mr-2" /> {packageMutation.isPending ? '生成中...' : '生成插件包'}
          </Button>
        </TabsContent>
      </Tabs>

      {output && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>生成结果</CardTitle>
            <Button size="sm" variant="outline" onClick={() => { navigator.clipboard?.writeText(output); toast.success('已复制') }}>
              复制
            </Button>
          </CardHeader>
          <CardContent>
            <pre className="max-h-[32rem] overflow-auto rounded bg-gray-900 p-4 text-xs text-gray-100">{output}</pre>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
