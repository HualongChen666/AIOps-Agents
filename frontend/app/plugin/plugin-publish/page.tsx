'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import api from '@/lib/api'
import toast from 'react-hot-toast'
import { UploadCloud, RefreshCw } from 'lucide-react'

interface Listing {
  id: string
  plugin_id: string
  plugin_name: string
  version: string
  author: string
  category: string
  quality: string
  enabled: boolean
  rating: number
  download_count: number
  created_at: string | null
}

const CATEGORIES = ['general', 'monitoring', 'alerting', 'automation', 'analytics', 'security', 'performance', 'integration']
const QUALITIES = ['community', 'verified', 'official']

const EMPTY = {
  plugin_id: '',
  plugin_name: '',
  version: '1.0.0',
  description: '',
  author: '',
  category: 'general',
  quality: 'community',
  tags: '',
  download_url: '',
  repository_url: '',
}

export default function PluginPublishPage() {
  const queryClient = useQueryClient()
  const [form, setForm] = useState({ ...EMPTY })

  const listingsQuery = useQuery<{ data: { items: Listing[]; total: number } }>({
    queryKey: ['marketplace-listings'],
    queryFn: async () => (await api.get('/api/v1/plugin-marketplace/plugins', { params: { limit: 100 } })).data,
  })

  const publishMutation = useMutation({
    mutationFn: async () => {
      if (!form.plugin_id.trim() || !form.plugin_name.trim()) throw new Error('plugin_id 与名称必填')
      if (!form.download_url.trim()) throw new Error('download_url 必填')
      const tags = form.tags
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean)
      const res = await api.post('/api/v1/plugin-marketplace/plugins', {
        plugin_id: form.plugin_id.trim(),
        plugin_name: form.plugin_name.trim(),
        version: form.version.trim() || '1.0.0',
        description: form.description,
        author: form.author,
        category: form.category,
        quality: form.quality,
        tags: tags.length ? tags : null,
        download_url: form.download_url.trim(),
        repository_url: form.repository_url || null,
      })
      return res.data
    },
    onSuccess: (data) => {
      if (data?.success) {
        toast.success(data.message || '已发布，等待审核')
        setForm({ ...EMPTY })
      } else {
        toast.error(data?.message || '发布失败')
      }
      queryClient.invalidateQueries({ queryKey: ['marketplace-listings'] })
    },
    onError: (e: any) => toast.error(e?.response?.data?.detail || e?.message || '发布失败'),
  })

  const items = listingsQuery.data?.data?.items ?? []

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900">插件发布</h1>

      <Card>
        <CardHeader>
          <CardTitle>发布到插件市场</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            <div>
              <Label htmlFor="m-pid">Plugin ID *</Label>
              <Input id="m-pid" value={form.plugin_id} onChange={(e) => setForm({ ...form, plugin_id: e.target.value })} />
            </div>
            <div>
              <Label htmlFor="m-name">名称 *</Label>
              <Input id="m-name" value={form.plugin_name} onChange={(e) => setForm({ ...form, plugin_name: e.target.value })} />
            </div>
            <div>
              <Label htmlFor="m-version">版本</Label>
              <Input id="m-version" value={form.version} onChange={(e) => setForm({ ...form, version: e.target.value })} />
            </div>
            <div>
              <Label htmlFor="m-author">作者</Label>
              <Input id="m-author" value={form.author} onChange={(e) => setForm({ ...form, author: e.target.value })} />
            </div>
            <div>
              <Label htmlFor="m-cat">分类</Label>
              <Select id="m-cat" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <Label htmlFor="m-qual">质量标识</Label>
              <Select id="m-qual" value={form.quality} onChange={(e) => setForm({ ...form, quality: e.target.value })}>
                {QUALITIES.map((q) => (
                  <option key={q} value={q}>
                    {q}
                  </option>
                ))}
              </Select>
            </div>
            <div className="md:col-span-2">
              <Label htmlFor="m-url">下载 URL *</Label>
              <Input id="m-url" value={form.download_url} onChange={(e) => setForm({ ...form, download_url: e.target.value })} placeholder="https://..." />
            </div>
            <div>
              <Label htmlFor="m-repo">仓库 URL</Label>
              <Input id="m-repo" value={form.repository_url} onChange={(e) => setForm({ ...form, repository_url: e.target.value })} />
            </div>
          </div>
          <div>
            <Label htmlFor="m-tags">标签 (逗号分隔)</Label>
            <Input id="m-tags" value={form.tags} onChange={(e) => setForm({ ...form, tags: e.target.value })} />
          </div>
          <div>
            <Label htmlFor="m-desc">描述</Label>
            <textarea
              id="m-desc"
              className="mt-1 w-full rounded-md border border-gray-300 p-2 text-sm"
              rows={3}
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </div>
          <Button onClick={() => publishMutation.mutate()} disabled={publishMutation.isPending}>
            <UploadCloud className="h-4 w-4 mr-2" />
            {publishMutation.isPending ? '发布中...' : '发布插件'}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>市场插件 ({listingsQuery.data?.data?.total ?? 0})</CardTitle>
          <Button variant="outline" size="sm" onClick={() => listingsQuery.refetch()}>
            <RefreshCw className={`h-4 w-4 ${listingsQuery.isFetching ? 'animate-spin' : ''}`} />
          </Button>
        </CardHeader>
        <CardContent>
          {listingsQuery.isLoading ? (
            <p className="py-6 text-center text-gray-500">加载中...</p>
          ) : items.length === 0 ? (
            <p className="py-6 text-center text-gray-500">暂无市场插件</p>
          ) : (
            <div className="space-y-3">
              {items.map((it) => (
                <div key={it.id} className="flex items-center justify-between rounded border p-3">
                  <div>
                    <div className="font-medium">
                      {it.plugin_name} <span className="text-xs text-gray-500">v{it.version}</span>
                    </div>
                    <div className="text-xs text-gray-500">
                      {it.plugin_id} · {it.category} · {it.author || '-'} · 下载 {it.download_count} · 评分 {it.rating.toFixed(1)}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{it.quality}</Badge>
                    <Badge variant={it.enabled ? 'default' : 'secondary'}>{it.enabled ? '已上架' : '待审核'}</Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
