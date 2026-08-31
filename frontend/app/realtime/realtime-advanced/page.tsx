'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import api from '@/lib/api'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { RefreshCw, Plus, Activity, Radio, Webhook, Users, Zap, Play, Pause } from 'lucide-react'
import toast from 'react-hot-toast'

interface RealtimeStream {
  id: string
  name: string
  description: string | null
  stream_type: string
  source: string | null
  config: Record<string, any>
  status: string
  created_at: string
  updated_at: string
  created_by: string | null
  meta_data: Record<string, any> | null
}

interface RealtimeEvent {
  id: number
  stream_id: string | null
  event_type: string
  event_data: Record<string, any>
  timestamp: string
  meta_data: Record<string, any> | null
}

interface RealtimeSubscription {
  id: string
  stream_id: string
  subscriber_id: string
  subscription_type: string
  filters: Record<string, any> | null
  status: string
  created_at: string
  updated_at: string
  meta_data: Record<string, any> | null
}

export default function RealtimeAdvancedPage() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState('streams')
  const [isCreating, setIsCreating] = useState(false)
  const [editingStream, setEditingStream] = useState<RealtimeStream | null>(null)
  const [newStream, setNewStream] = useState({
    name: '',
    description: '',
    stream_type: 'sse',
    source: '',
    config: '{}'
  })
  const [selectedStream, setSelectedStream] = useState<string>('')
  const [isSubscribing, setIsSubscribing] = useState(false)
  const [subscriptionData, setSubscriptionData] = useState({
    stream_id: '',
    subscriber_id: '',
    subscription_type: 'sse',
    filters: '{}'
  })

  // 获取实时流列表
  const { data: streams, isLoading: streamsLoading, refetch: refetchStreams } = useQuery({
    queryKey: ['realtime-streams'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/realtime/streams')
      return resp.data as RealtimeStream[]
    }
  })

  // 获取实时事件
  const { data: events, isLoading: eventsLoading, refetch: refetchEvents } = useQuery({
    queryKey: ['realtime-events', selectedStream],
    queryFn: async () => {
      const params: Record<string, any> = {}
      if (selectedStream) params.stream_id = selectedStream
      const resp = await api.get('/api/v1/realtime/events', { params })
      return resp.data as RealtimeEvent[]
    },
    refetchInterval: 5000,
    enabled: activeTab === 'events'
  })

  // 获取订阅列表
  const { data: subscriptions, isLoading: subscriptionsLoading, refetch: refetchSubscriptions } = useQuery({
    queryKey: ['realtime-subscriptions'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/realtime/subscriptions')
      return resp.data as RealtimeSubscription[]
    }
  })

  // 创建流
  const createStreamMutation = useMutation({
    mutationFn: async (stream: any) => {
      const resp = await api.post('/api/v1/realtime/streams', stream)
      return resp.data
    },
    onSuccess: () => {
      toast.success('流创建成功')
      setIsCreating(false)
      setNewStream({ name: '', description: '', stream_type: 'sse', source: '', config: '{}' })
      refetchStreams()
    },
    onError: (error: any) => {
      toast.error(`创建失败: ${error.response?.data?.detail || error.message}`)
    }
  })

  // 更新流
  const updateStreamMutation = useMutation({
    mutationFn: async ({ streamId, data }: { streamId: string; data: any }) => {
      const resp = await api.patch(`/api/v1/realtime/streams/${streamId}`, data)
      return resp.data
    },
    onSuccess: () => {
      toast.success('流更新成功')
      setEditingStream(null)
      refetchStreams()
    },
    onError: (error: any) => {
      toast.error(`更新失败: ${error.response?.data?.detail || error.message}`)
    }
  })

  // 删除流
  const deleteStreamMutation = useMutation({
    mutationFn: async (streamId: string) => {
      const resp = await api.delete(`/api/v1/realtime/streams/${streamId}`)
      return resp.data
    },
    onSuccess: () => {
      toast.success('流删除成功')
      refetchStreams()
    },
    onError: (error: any) => {
      toast.error(`删除失败: ${error.response?.data?.detail || error.message}`)
    }
  })

  // 创建订阅
  const createSubscriptionMutation = useMutation({
    mutationFn: async (subscription: any) => {
      const resp = await api.post('/api/v1/realtime/subscriptions', subscription)
      return resp.data
    },
    onSuccess: () => {
      toast.success('订阅创建成功')
      setIsSubscribing(false)
      setSubscriptionData({ stream_id: '', subscriber_id: '', subscription_type: 'sse', filters: '{}' })
      refetchSubscriptions()
    },
    onError: (error: any) => {
      toast.error(`创建失败: ${error.response?.data?.detail || error.message}`)
    }
  })

  // 删除订阅
  const deleteSubscriptionMutation = useMutation({
    mutationFn: async (subscriptionId: string) => {
      const resp = await api.delete(`/api/v1/realtime/subscriptions/${subscriptionId}`)
      return resp.data
    },
    onSuccess: () => {
      toast.success('订阅删除成功')
      refetchSubscriptions()
    },
    onError: (error: any) => {
      toast.error(`删除失败: ${error.response?.data?.detail || error.message}`)
    }
  })

  const handleRefreshAll = () => {
    refetchStreams()
    refetchEvents()
    refetchSubscriptions()
  }

  const handleCreateStream = () => {
    try {
      const config = JSON.parse(newStream.config)
      createStreamMutation.mutate({
        name: newStream.name,
        description: newStream.description,
        stream_type: newStream.stream_type,
        source: newStream.source,
        config
      })
    } catch (e) {
      toast.error('配置JSON格式错误')
    }
  }

  const handleUpdateStream = () => {
    if (!editingStream) return
    try {
      const config = JSON.parse(editingStream.config as any)
      updateStreamMutation.mutate({
        streamId: editingStream.id,
        data: {
          name: editingStream.name,
          description: editingStream.description,
          stream_type: editingStream.stream_type,
          source: editingStream.source,
          config,
          status: editingStream.status
        }
      })
    } catch (e) {
      toast.error('配置JSON格式错误')
    }
  }

  const handleCreateSubscription = () => {
    try {
      const filters = JSON.parse(subscriptionData.filters)
      createSubscriptionMutation.mutate({
        stream_id: subscriptionData.stream_id,
        subscriber_id: subscriptionData.subscriber_id,
        subscription_type: subscriptionData.subscription_type,
        filters
      })
    } catch (e) {
      toast.error('过滤器JSON格式错误')
    }
  }

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'active':
      case 'running':
        return 'text-green-600 bg-green-50'
      case 'inactive':
      case 'stopped':
        return 'text-gray-600 bg-gray-50'
      case 'error':
        return 'text-red-600 bg-red-50'
      default:
        return 'text-gray-600 bg-gray-50'
    }
  }

  const getStreamTypeIcon = (type: string) => {
    switch (type?.toLowerCase()) {
      case 'sse':
        return <Radio className="h-4 w-4" />
      case 'websocket':
        return <Activity className="h-4 w-4" />
      case 'kafka':
        return <Zap className="h-4 w-4" />
      default:
        return <Activity className="h-4 w-4" />
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">高级实时通信</h1>
          <p className="text-sm text-gray-500 mt-1">实时流管理与事件订阅</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={handleRefreshAll} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新全部
          </Button>
        </div>
      </div>

      {/* Tab 导航 */}
      <div className="flex gap-2 border-b">
        {[
          { id: 'streams', label: '实时流', icon: Activity },
          { id: 'events', label: '实时事件', icon: Zap },
          { id: 'subscriptions', label: '订阅管理', icon: Users }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 border-b-2 transition-colors ${
              activeTab === tab.id
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            <tab.icon className="h-4 w-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* 实时流 */}
      {activeTab === 'streams' && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>实时流列表</span>
                <Button onClick={() => setIsCreating(true)} size="sm">
                  <Plus className="h-4 w-4 mr-2" />
                  新建流
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {streamsLoading ? (
                <div className="text-center text-gray-500 py-8">加载中...</div>
              ) : (
                <div className="space-y-3">
                  {streams?.map((stream) => (
                    <div key={stream.id} className="p-4 border rounded-lg">
                      {editingStream?.id === stream.id ? (
                        <div className="space-y-3">
                          <Input
                            value={editingStream.name}
                            onChange={(e) => setEditingStream({ ...editingStream, name: e.target.value })}
                          />
                          <Input
                            value={editingStream.description || ''}
                            onChange={(e) => setEditingStream({ ...editingStream, description: e.target.value })}
                          />
                          <Select
                            value={editingStream.stream_type}
                            onChange={(e) => setEditingStream({ ...editingStream, stream_type: e.target.value })}
                            className="w-full"
                          >
                            <option value="sse">SSE</option>
                            <option value="websocket">WebSocket</option>
                            <option value="kafka">Kafka</option>
                          </Select>
                          <Input
                            value={editingStream.source || ''}
                            onChange={(e) => setEditingStream({ ...editingStream, source: e.target.value })}
                            placeholder="数据源"
                          />
                          <textarea
                            value={editingStream.config as any}
                            onChange={(e) => setEditingStream({ ...editingStream, config: e.target.value })}
                            className="w-full px-3 py-2 border rounded-md"
                            rows={3}
                          />
                          <div className="flex gap-2">
                            <Button onClick={handleUpdateStream} size="sm">
                              保存
                            </Button>
                            <Button onClick={() => setEditingStream(null)} variant="outline" size="sm">
                              取消
                            </Button>
                          </div>
                        </div>
                      ) : (
                        <div>
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                              {getStreamTypeIcon(stream.stream_type)}
                              <span className="font-medium">{stream.name}</span>
                              <span className={`px-2 py-1 rounded text-xs ${getStatusColor(stream.status)}`}>
                                {stream.status}
                              </span>
                            </div>
                            <div className="flex gap-2">
                              <Button onClick={() => setEditingStream(stream)} variant="ghost" size="sm">
                                编辑
                              </Button>
                              <Button
                                onClick={() => deleteStreamMutation.mutate(stream.id)}
                                variant="ghost"
                                size="sm"
                              >
                                删除
                              </Button>
                            </div>
                          </div>
                          {stream.description && (
                            <p className="text-sm text-gray-600 mb-2">{stream.description}</p>
                          )}
                          <div className="text-sm text-gray-500">
                            <span>类型: {stream.stream_type}</span>
                            {stream.source && <span className="ml-4">源: {stream.source}</span>}
                            <span className="ml-4">创建: {new Date(stream.created_at).toLocaleString()}</span>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* 创建流表单 */}
          {isCreating && (
            <Card>
              <CardHeader>
                <CardTitle>创建实时流</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">流名称</label>
                    <Input
                      value={newStream.name}
                      onChange={(e) => setNewStream({ ...newStream, name: e.target.value })}
                      placeholder="流名称"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">描述</label>
                    <Input
                      value={newStream.description}
                      onChange={(e) => setNewStream({ ...newStream, description: e.target.value })}
                      placeholder="流描述"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">流类型</label>
                    <Select
                      value={newStream.stream_type}
                      onChange={(e) => setNewStream({ ...newStream, stream_type: e.target.value })}
                      className="w-full"
                    >
                      <option value="sse">SSE (Server-Sent Events)</option>
                      <option value="websocket">WebSocket</option>
                      <option value="kafka">Kafka</option>
                    </Select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">数据源</label>
                    <Input
                      value={newStream.source}
                      onChange={(e) => setNewStream({ ...newStream, source: e.target.value })}
                      placeholder="数据源标识"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">配置（JSON）</label>
                    <textarea
                      value={newStream.config}
                      onChange={(e) => setNewStream({ ...newStream, config: e.target.value })}
                      className="w-full px-3 py-2 border rounded-md"
                      rows={4}
                      placeholder='{"batch_size": 100, "interval": 5}'
                    />
                  </div>
                  <div className="flex gap-2">
                    <Button onClick={handleCreateStream} disabled={createStreamMutation.isPending}>
                      {createStreamMutation.isPending ? '创建中...' : '创建'}
                    </Button>
                    <Button onClick={() => setIsCreating(false)} variant="outline">
                      取消
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* 实时事件 */}
      {activeTab === 'events' && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>过滤器</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex gap-4">
                <div className="flex-1">
                  <label className="block text-sm font-medium mb-1">选择流</label>
                  <Select
                    value={selectedStream}
                    onChange={(e) => setSelectedStream(e.target.value)}
                    className="w-full"
                  >
                    <option value="">全部流</option>
                    {streams?.map((stream) => (
                      <option key={stream.id} value={stream.id}>
                        {stream.name}
                      </option>
                    ))}
                  </Select>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5" />
                实时事件流
                <span className="text-sm font-normal text-gray-500">(自动刷新)</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {eventsLoading ? (
                <div className="text-center text-gray-500 py-8">加载中...</div>
              ) : (
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {events?.map((event) => (
                    <div key={event.id} className="p-4 border rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium">{event.event_type}</span>
                        <span className="text-sm text-gray-500">
                          {new Date(event.timestamp).toLocaleString()}
                        </span>
                      </div>
                      <pre className="text-xs bg-gray-50 p-2 rounded overflow-x-auto">
                        {JSON.stringify(event.event_data, null, 2)}
                      </pre>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* 订阅管理 */}
      {activeTab === 'subscriptions' && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>订阅列表</span>
                <Button onClick={() => setIsSubscribing(true)} size="sm">
                  <Plus className="h-4 w-4 mr-2" />
                  新建订阅
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {subscriptionsLoading ? (
                <div className="text-center text-gray-500 py-8">加载中...</div>
              ) : (
                <div className="space-y-3">
                  {subscriptions?.map((sub) => (
                    <div key={sub.id} className="p-4 border rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{sub.subscriber_id}</span>
                          <span className={`px-2 py-1 rounded text-xs ${getStatusColor(sub.status)}`}>
                            {sub.status}
                          </span>
                        </div>
                        <Button
                          onClick={() => deleteSubscriptionMutation.mutate(sub.id)}
                          variant="ghost"
                          size="sm"
                        >
                          删除
                        </Button>
                      </div>
                      <div className="text-sm text-gray-500">
                        <span>流ID: {sub.stream_id}</span>
                        <span className="ml-4">类型: {sub.subscription_type}</span>
                        <span className="ml-4">创建: {new Date(sub.created_at).toLocaleString()}</span>
                      </div>
                      {sub.filters && (
                        <pre className="text-xs bg-gray-50 p-2 rounded mt-2">
                          {JSON.stringify(sub.filters, null, 2)}
                        </pre>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* 创建订阅表单 */}
          {isSubscribing && (
            <Card>
              <CardHeader>
                <CardTitle>创建订阅</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">流ID</label>
                    <Select
                      value={subscriptionData.stream_id}
                      onChange={(e) => setSubscriptionData({ ...subscriptionData, stream_id: e.target.value })}
                      className="w-full"
                    >
                      <option value="">选择流</option>
                      {streams?.map((stream) => (
                        <option key={stream.id} value={stream.id}>
                          {stream.name} ({stream.id})
                        </option>
                      ))}
                    </Select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">订阅者ID</label>
                    <Input
                      value={subscriptionData.subscriber_id}
                      onChange={(e) => setSubscriptionData({ ...subscriptionData, subscriber_id: e.target.value })}
                      placeholder="subscriber-001"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">订阅类型</label>
                    <Select
                      value={subscriptionData.subscription_type}
                      onChange={(e) => setSubscriptionData({ ...subscriptionData, subscription_type: e.target.value })}
                      className="w-full"
                    >
                      <option value="sse">SSE</option>
                      <option value="websocket">WebSocket</option>
                    </Select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">过滤器（JSON）</label>
                    <textarea
                      value={subscriptionData.filters}
                      onChange={(e) => setSubscriptionData({ ...subscriptionData, filters: e.target.value })}
                      className="w-full px-3 py-2 border rounded-md"
                      rows={3}
                      placeholder='{"event_type": "alert"}'
                    />
                  </div>
                  <div className="flex gap-2">
                    <Button onClick={handleCreateSubscription} disabled={createSubscriptionMutation.isPending}>
                      {createSubscriptionMutation.isPending ? '创建中...' : '创建'}
                    </Button>
                    <Button onClick={() => setIsSubscribing(false)} variant="outline">
                      取消
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  )
}
