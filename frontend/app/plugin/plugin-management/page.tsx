'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { DataTable } from '@/components/ui/DataTable'
import { KpiCard } from '@/components/ui/KpiCard'
import api from '@/lib/api'
import toast from 'react-hot-toast'
import { Plus, RefreshCw, Trash2, Power, Package, CheckCircle2, AlertTriangle, Activity } from 'lucide-react'

interface Plugin {
  id: string
  name: string
  version: string
  description: string | null
  author: string | null
  plugin_type: string
  status: string
  entry_point: string | null
  created_at: string
  updated_at: string
}

const PLUGIN_TYPES = ['collector', 'analyzer', 'executor', 'storage', 'notifier']
const STATUSES = ['active', 'inactive', 'loading', 'error']

const STATUS_VARIANT: Record<string, 'default' | 'secondary' | 'destructive'> = {
  active: 'default',
  inactive: 'secondary',
  loading: 'default',
  error: 'destructive',
}

const EMPTY_FORM = {
  name: '',
  version: '1.0.0',
  description: '',
  author: '',
  plugin_type: 'collector',
  entry_point: '',
}

export default function PluginManagementPage() {
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({ ...EMPTY_FORM })

  const pluginsQuery = useQuery<{ total: number; plugins: Plugin[] }>({
    queryKey: ['plugins', 'management'],
    queryFn: async () => (await api.get('/api/plugins/', { params: { limit: 200 } })).data,
  })

  const statsQuery = useQuery({
    queryKey: ['plugin-stats'],
    queryFn: async () => (await api.get('/api/plugins/stats')).data,
  })

  const createMutation = useMutation({
    mutationFn: async () => {
      if (!form.name.trim()) throw new Error('请填写插件名称')
      const res = await api.post('/api/plugins/', {
        name: form.name.trim(),
        version: form.version.trim() || '1.0.0',
        description: form.description || null,
        author: form.author || null,
        plugin_type: form.plugin_type,
        entry_point: form.entry_point || null,
      })
      return res.data
    },
    onSuccess: () => {
      toast.success('插件已创建')
      setOpen(false)
      setForm({ ...EMPTY_FORM })
      queryClient.invalidateQueries({ queryKey: ['plugins'] })
      queryClient.invalidateQueries({ queryKey: ['plugin-stats'] })
    },
    onError: (e: any) => toast.error(e?.response?.data?.detail || e?.message || '创建失败'),
  })

  const updateMutation = useMutation({
    mutationFn: async ({ id, patch }: { id: string; patch: Record<string, any> }) => {
      const res = await api.put(`/api/plugins/${id}`, patch)
      return res.data
    },
    onSuccess: () => {
      toast.success('插件已更新')
      queryClient.invalidateQueries({ queryKey: ['plugins'] })
      queryClient.invalidateQueries({ queryKey: ['plugin-stats'] })
    },
    onError: (e: any) => toast.error(e?.response?.data?.detail || '更新失败'),
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
    onError: (e: any) => toast.error(e?.response?.data?.detail || '删除失败（需要管理员）'),
  })

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
      render: (v: string, row: Plugin) => (
        <Select
          value={row.status}
          onChange={(e) => updateMutation.mutate({ id: row.id, patch: { status: e.target.value } })}
          className="h-8 w-32 text-xs"
        >
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </Select>
      ),
    },
    {
      key: 'updated_at' as const,
      label: '更新时间',
      render: (v: string) => (v ? new Date(v).toLocaleString() : '-'),
    },
    {
      key: 'id' as const,
      label: '操作',
      render: (_v: string, row: Plugin) => (
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() =>
              updateMutation.mutate({
                id: row.id,
                patch: { status: row.status === 'active' ? 'inactive' : 'active' },
              })
            }
          >
            <Power className="h-3 w-3 mr-1" />
            {row.status === 'active' ? '停用' : '启用'}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => {
              if (confirm(`确认删除 ${row.name}？`)) deleteMutation.mutate(row.id)
            }}
          >
            <Trash2 className="h-3 w-3 text-red-600" />
          </Button>
        </div>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">插件管理</h1>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => pluginsQuery.refetch()}>
            <RefreshCw className={`h-4 w-4 mr-2 ${pluginsQuery.isFetching ? 'animate-spin' : ''}`} />
            刷新
          </Button>
          <Button onClick={() => setOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            新建插件
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <KpiCard title="插件总数" value={stats?.total_plugins ?? 0} icon={Package} />
        <KpiCard title="活跃" value={stats?.active_plugins ?? 0} icon={CheckCircle2} />
        <KpiCard title="非活跃" value={stats?.inactive_plugins ?? 0} icon={AlertTriangle} />
        <KpiCard title="总执行" value={stats?.total_executions ?? 0} icon={Activity} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>插件清单</CardTitle>
        </CardHeader>
        <CardContent>
          {pluginsQuery.isLoading ? (
            <div className="py-8 text-center text-gray-500">加载中...</div>
          ) : pluginsQuery.isError ? (
            <div className="py-8 text-center text-red-600">加载失败</div>
          ) : (
            <DataTable data={plugins} columns={columns} emptyMessage="暂无插件" filterable={false} />
          )}
        </CardContent>
      </Card>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>新建插件</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <Label htmlFor="p-name">名称 *</Label>
              <Input id="p-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="p-version">版本</Label>
                <Input id="p-version" value={form.version} onChange={(e) => setForm({ ...form, version: e.target.value })} />
              </div>
              <div>
                <Label htmlFor="p-type">类型</Label>
                <Select id="p-type" value={form.plugin_type} onChange={(e) => setForm({ ...form, plugin_type: e.target.value })}>
                  {PLUGIN_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </Select>
              </div>
            </div>
            <div>
              <Label htmlFor="p-author">作者</Label>
              <Input id="p-author" value={form.author} onChange={(e) => setForm({ ...form, author: e.target.value })} />
            </div>
            <div>
              <Label htmlFor="p-entry">入口函数 (entry_point)</Label>
              <Input id="p-entry" value={form.entry_point} onChange={(e) => setForm({ ...form, entry_point: e.target.value })} placeholder="module:function" />
            </div>
            <div>
              <Label htmlFor="p-desc">描述</Label>
              <textarea
                id="p-desc"
                className="mt-1 w-full rounded-md border border-gray-300 p-2 text-sm"
                rows={3}
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>
              取消
            </Button>
            <Button onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>
              {createMutation.isPending ? '提交中...' : '创建'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
