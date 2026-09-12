'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { DataTable } from '@/components/ui/DataTable'
import api from '@/lib/api'
import toast from 'react-hot-toast'
import { RefreshCw, UserPlus } from 'lucide-react'

interface RegisteredPlugin {
  plugin_id: string
  name: string
  version: string
  description: string
  author: string
  plugin_type: string
  status: string
  dependencies: string[]
  api_version: string
}

const TYPES = ['monitoring', 'integration', 'ai', 'custom']

const STATUS_VARIANT: Record<string, 'default' | 'secondary' | 'destructive'> = {
  enabled: 'default',
  installed: 'secondary',
  disabled: 'secondary',
  unloaded: 'secondary',
  loading: 'default',
  error: 'destructive',
}

const EMPTY = {
  plugin_id: '',
  name: '',
  version: '1.0.0',
  description: '',
  author: '',
  plugin_type: 'monitoring',
  dependencies: '',
}

export default function PluginRegistrationPage() {
  const queryClient = useQueryClient()
  const [form, setForm] = useState({ ...EMPTY })

  const pluginsQuery = useQuery<{ data: { plugins: RegisteredPlugin[]; count: number } }>({
    queryKey: ['plugin-system-plugins'],
    queryFn: async () => (await api.get('/api/plugin-system/plugins')).data,
  })

  const registerMutation = useMutation({
    mutationFn: async () => {
      if (!form.plugin_id.trim() || !form.name.trim()) throw new Error('plugin_id 与 name 必填')
      const deps = form.dependencies
        .split(',')
        .map((d) => d.trim())
        .filter(Boolean)
      const res = await api.post('/api/plugin-system/plugin/register', deps.length ? { dependencies: deps } : {}, {
        params: {
          plugin_id: form.plugin_id.trim(),
          name: form.name.trim(),
          version: form.version.trim() || '1.0.0',
          description: form.description || '',
          author: form.author || '',
          plugin_type: form.plugin_type,
        },
      })
      return res.data
    },
    onSuccess: (data) => {
      if (data?.data?.registered) {
        toast.success('插件注册成功')
        setForm({ ...EMPTY })
      } else {
        toast.error('注册未生效，请检查插件 ID 是否重复')
      }
      queryClient.invalidateQueries({ queryKey: ['plugin-system-plugins'] })
      queryClient.invalidateQueries({ queryKey: ['plugin-system-status'] })
    },
    onError: (e: any) => toast.error(e?.response?.data?.detail || e?.message || '注册失败'),
  })

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
    { key: 'author' as const, label: '作者', render: (v: string) => v || '-' },
  ]

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900">插件注册</h1>

      <Card>
        <CardHeader>
          <CardTitle>注册新插件</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            <div>
              <Label htmlFor="r-id">Plugin ID *</Label>
              <Input id="r-id" value={form.plugin_id} onChange={(e) => setForm({ ...form, plugin_id: e.target.value })} placeholder="cpu-analyzer" />
            </div>
            <div>
              <Label htmlFor="r-name">名称 *</Label>
              <Input id="r-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </div>
            <div>
              <Label htmlFor="r-version">版本</Label>
              <Input id="r-version" value={form.version} onChange={(e) => setForm({ ...form, version: e.target.value })} />
            </div>
            <div>
              <Label htmlFor="r-author">作者</Label>
              <Input id="r-author" value={form.author} onChange={(e) => setForm({ ...form, author: e.target.value })} />
            </div>
            <div>
              <Label htmlFor="r-type">类型</Label>
              <Select id="r-type" value={form.plugin_type} onChange={(e) => setForm({ ...form, plugin_type: e.target.value })}>
                {TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <Label htmlFor="r-deps">依赖 (逗号分隔)</Label>
              <Input id="r-deps" value={form.dependencies} onChange={(e) => setForm({ ...form, dependencies: e.target.value })} placeholder="plugin-a, plugin-b" />
            </div>
          </div>
          <div>
            <Label htmlFor="r-desc">描述</Label>
            <textarea
              id="r-desc"
              className="mt-1 w-full rounded-md border border-gray-300 p-2 text-sm"
              rows={2}
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </div>
          <Button onClick={() => registerMutation.mutate()} disabled={registerMutation.isPending}>
            <UserPlus className="h-4 w-4 mr-2" />
            {registerMutation.isPending ? '注册中...' : '注册插件'}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>已注册插件 ({pluginsQuery.data?.data?.count ?? 0})</CardTitle>
          <Button variant="outline" size="sm" onClick={() => pluginsQuery.refetch()}>
            <RefreshCw className={`h-4 w-4 ${pluginsQuery.isFetching ? 'animate-spin' : ''}`} />
          </Button>
        </CardHeader>
        <CardContent>
          {pluginsQuery.isLoading ? (
            <div className="py-8 text-center text-gray-500">加载中...</div>
          ) : (
            <DataTable data={plugins} columns={columns} emptyMessage="暂无已注册插件" filterable={false} />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
