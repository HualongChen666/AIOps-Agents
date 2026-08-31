'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import api from '@/lib/api'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { RefreshCw, Plus, Edit, Trash2, TrendingUp, AlertCircle, History, Calculator } from 'lucide-react'
import toast from 'react-hot-toast'

interface PriorityRule {
  id: string
  name: string
  description: string | null
  conditions: Record<string, any>
  priority_level: string
  weight: number
  enabled: boolean
  created_at: string
  updated_at: string
  created_by: string | null
  meta_data: Record<string, any> | null
}

interface PriorityScore {
  id: number
  alert_id: string
  priority_level: string
  score: number
  bis_score: number | null
  factors: Record<string, any> | null
  calculated_at: string
  meta_data: Record<string, any> | null
}

interface PriorityHistory {
  id: number
  alert_id: string
  old_priority: string | null
  new_priority: string
  old_score: number | null
  new_score: number
  change_reason: string | null
  changed_by: string | null
  changed_at: string
  meta_data: Record<string, any> | null
}

export default function PriorityAdvancedPage() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState('rules')
  const [enabledFilter, setEnabledFilter] = useState<boolean | null>(null)
  const [priorityLevelFilter, setPriorityLevelFilter] = useState<string>('')
  const [isCreating, setIsCreating] = useState(false)
  const [editingRule, setEditingRule] = useState<PriorityRule | null>(null)
  const [newRule, setNewRule] = useState({
    name: '',
    description: '',
    conditions: '{}',
    priority_level: 'P2',
    weight: 1.0
  })
  const [scoreRequest, setScoreRequest] = useState({
    alert_id: '',
    metrics: '{}',
    context: '{}'
  })

  // 获取优先级规则列表
  const { data: rules, isLoading: rulesLoading, refetch: refetchRules } = useQuery({
    queryKey: ['priority-rules', enabledFilter, priorityLevelFilter],
    queryFn: async () => {
      const params: Record<string, any> = {}
      if (enabledFilter !== null) params.enabled = enabledFilter
      if (priorityLevelFilter) params.priority_level = priorityLevelFilter
      const resp = await api.get('/api/v1/priority/rules', { params })
      return resp.data as PriorityRule[]
    }
  })

  // 获取优先级分数
  const { data: scoreResult, isLoading: scoreLoading, refetch: refetchScore } = useQuery({
    queryKey: ['priority-score', scoreRequest.alert_id],
    queryFn: async () => {
      const metrics = JSON.parse(scoreRequest.metrics)
      const context = scoreRequest.context ? JSON.parse(scoreRequest.context) : undefined
      const resp = await api.post('/api/v1/priority/scores', {
        alert_id: scoreRequest.alert_id,
        metrics,
        context
      })
      return resp.data as PriorityScore
    },
    enabled: false
  })

  // 获取优先级历史
  const { data: history, isLoading: historyLoading, refetch: refetchHistory } = useQuery({
    queryKey: ['priority-history'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/priority/history')
      return resp.data as PriorityHistory[]
    }
  })

  // 创建规则
  const createRuleMutation = useMutation({
    mutationFn: async (rule: any) => {
      const resp = await api.post('/api/v1/priority/rules', rule)
      return resp.data
    },
    onSuccess: () => {
      toast.success('规则创建成功')
      setIsCreating(false)
      setNewRule({ name: '', description: '', conditions: '{}', priority_level: 'P2', weight: 1.0 })
      refetchRules()
    },
    onError: (error: any) => {
      toast.error(`创建失败: ${error.response?.data?.detail || error.message}`)
    }
  })

  // 更新规则
  const updateRuleMutation = useMutation({
    mutationFn: async ({ ruleId, data }: { ruleId: string; data: any }) => {
      const resp = await api.patch(`/api/v1/priority/rules/${ruleId}`, data)
      return resp.data
    },
    onSuccess: () => {
      toast.success('规则更新成功')
      setEditingRule(null)
      refetchRules()
    },
    onError: (error: any) => {
      toast.error(`更新失败: ${error.response?.data?.detail || error.message}`)
    }
  })

  // 删除规则
  const deleteRuleMutation = useMutation({
    mutationFn: async (ruleId: string) => {
      const resp = await api.delete(`/api/v1/priority/rules/${ruleId}`)
      return resp.data
    },
    onSuccess: () => {
      toast.success('规则删除成功')
      refetchRules()
    },
    onError: (error: any) => {
      toast.error(`删除失败: ${error.response?.data?.detail || error.message}`)
    }
  })

  const handleRefreshAll = () => {
    refetchRules()
    refetchHistory()
  }

  const handleCreateRule = () => {
    try {
      const conditions = JSON.parse(newRule.conditions)
      createRuleMutation.mutate({
        name: newRule.name,
        description: newRule.description,
        conditions,
        priority_level: newRule.priority_level,
        weight: newRule.weight
      })
    } catch (e) {
      toast.error('条件JSON格式错误')
    }
  }

  const handleUpdateRule = () => {
    if (!editingRule) return
    try {
      const conditions = JSON.parse(editingRule.conditions as any)
      updateRuleMutation.mutate({
        ruleId: editingRule.id,
        data: {
          name: editingRule.name,
          description: editingRule.description,
          conditions,
          priority_level: editingRule.priority_level,
          weight: editingRule.weight,
          enabled: editingRule.enabled
        }
      })
    } catch (e) {
      toast.error('条件JSON格式错误')
    }
  }

  const handleCalculateScore = () => {
    try {
      JSON.parse(scoreRequest.metrics)
      if (scoreRequest.context) JSON.parse(scoreRequest.context)
      refetchScore()
    } catch (e) {
      toast.error('JSON格式错误')
    }
  }

  const getPriorityColor = (level: string) => {
    switch (level) {
      case 'P0':
        return 'text-red-600 bg-red-50'
      case 'P1':
        return 'text-orange-600 bg-orange-50'
      case 'P2':
        return 'text-yellow-600 bg-yellow-50'
      case 'P3':
        return 'text-blue-600 bg-blue-50'
      case 'P4':
        return 'text-gray-600 bg-gray-50'
      default:
        return 'text-gray-600 bg-gray-50'
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">高级优先级管理</h1>
          <p className="text-sm text-gray-500 mt-1">告警优先级规则与智能评分</p>
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
          { id: 'rules', label: '优先级规则', icon: TrendingUp },
          { id: 'calculator', label: '优先级计算', icon: Calculator },
          { id: 'history', label: '变更历史', icon: History }
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

      {/* 优先级规则 */}
      {activeTab === 'rules' && (
        <div className="space-y-4">
          {/* 过滤器 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">过滤器</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">状态</label>
                  <Select
                    value={enabledFilter === null ? 'all' : enabledFilter ? 'true' : 'false'}
                    onChange={(e) => setEnabledFilter(e.target.value === 'all' ? null : e.target.value === 'true')}
                    className="w-40"
                  >
                    <option value="all">全部</option>
                    <option value="true">启用</option>
                    <option value="false">禁用</option>
                  </Select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">优先级级别</label>
                  <Select
                    value={priorityLevelFilter}
                    onChange={(e) => setPriorityLevelFilter(e.target.value)}
                    className="w-40"
                  >
                    <option value="">全部</option>
                    <option value="P0">P0</option>
                    <option value="P1">P1</option>
                    <option value="P2">P2</option>
                    <option value="P3">P3</option>
                    <option value="P4">P4</option>
                  </Select>
                </div>
                <div className="flex items-end">
                  <Button onClick={() => setIsCreating(true)} size="sm">
                    <Plus className="h-4 w-4 mr-2" />
                    新建规则
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 创建规则表单 */}
          {isCreating && (
            <Card>
              <CardHeader>
                <CardTitle>创建优先级规则</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">规则名称</label>
                    <Input
                      value={newRule.name}
                      onChange={(e) => setNewRule({ ...newRule, name: e.target.value })}
                      placeholder="规则名称"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">描述</label>
                    <Input
                      value={newRule.description}
                      onChange={(e) => setNewRule({ ...newRule, description: e.target.value })}
                      placeholder="规则描述"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">条件（JSON）</label>
                    <textarea
                      value={newRule.conditions}
                      onChange={(e) => setNewRule({ ...newRule, conditions: e.target.value })}
                      className="w-full px-3 py-2 border rounded-md"
                      rows={4}
                      placeholder='{"metric": "cpu_usage", "operator": ">", "threshold": 90}'
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium mb-1">优先级级别</label>
                      <Select
                        value={newRule.priority_level}
                        onChange={(e) => setNewRule({ ...newRule, priority_level: e.target.value })}
                        className="w-full"
                      >
                        <option value="P0">P0 - 严重</option>
                        <option value="P1">P1 - 高</option>
                        <option value="P2">P2 - 中</option>
                        <option value="P3">P3 - 低</option>
                        <option value="P4">P4 - 最低</option>
                      </Select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">权重</label>
                      <Input
                        type="number"
                        step="0.1"
                        value={newRule.weight}
                        onChange={(e) => setNewRule({ ...newRule, weight: parseFloat(e.target.value) })}
                        min={0}
                        max={10}
                      />
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button onClick={handleCreateRule} disabled={createRuleMutation.isPending}>
                      {createRuleMutation.isPending ? '创建中...' : '创建'}
                    </Button>
                    <Button onClick={() => setIsCreating(false)} variant="outline">
                      取消
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* 规则列表 */}
          <Card>
            <CardHeader>
              <CardTitle>规则列表</CardTitle>
            </CardHeader>
            <CardContent>
              {rulesLoading ? (
                <div className="text-center text-gray-500 py-8">加载中...</div>
              ) : (
                <div className="space-y-3">
                  {rules?.map((rule) => (
                    <div key={rule.id} className="p-4 border rounded-lg">
                      {editingRule?.id === rule.id ? (
                        <div className="space-y-3">
                          <Input
                            value={editingRule.name}
                            onChange={(e) => setEditingRule({ ...editingRule, name: e.target.value })}
                          />
                          <Input
                            value={editingRule.description || ''}
                            onChange={(e) => setEditingRule({ ...editingRule, description: e.target.value })}
                          />
                          <textarea
                            value={editingRule.conditions as any}
                            onChange={(e) => setEditingRule({ ...editingRule, conditions: e.target.value })}
                            className="w-full px-3 py-2 border rounded-md"
                            rows={3}
                          />
                          <div className="flex gap-2">
                            <Select
                              value={editingRule.priority_level}
                              onChange={(e) => setEditingRule({ ...editingRule, priority_level: e.target.value })}
                              className="w-32"
                            >
                              <option value="P0">P0</option>
                              <option value="P1">P1</option>
                              <option value="P2">P2</option>
                              <option value="P3">P3</option>
                              <option value="P4">P4</option>
                            </Select>
                            <Input
                              type="number"
                              step="0.1"
                              value={editingRule.weight}
                              onChange={(e) => setEditingRule({ ...editingRule, weight: parseFloat(e.target.value) })}
                              className="w-24"
                            />
                            <Button onClick={handleUpdateRule} size="sm">
                              保存
                            </Button>
                            <Button onClick={() => setEditingRule(null)} variant="outline" size="sm">
                              取消
                            </Button>
                          </div>
                        </div>
                      ) : (
                        <div>
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <span className="font-medium">{rule.name}</span>
                              <span className={`px-2 py-1 rounded text-xs ${getPriorityColor(rule.priority_level)}`}>
                                {rule.priority_level}
                              </span>
                              <span className={`px-2 py-1 rounded text-xs ${rule.enabled ? 'text-green-600 bg-green-50' : 'text-gray-600 bg-gray-50'}`}>
                                {rule.enabled ? '启用' : '禁用'}
                              </span>
                            </div>
                            <div className="flex gap-2">
                              <Button onClick={() => setEditingRule(rule)} variant="ghost" size="sm">
                                <Edit className="h-4 w-4" />
                              </Button>
                              <Button
                                onClick={() => deleteRuleMutation.mutate(rule.id)}
                                variant="ghost"
                                size="sm"
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          </div>
                          {rule.description && (
                            <p className="text-sm text-gray-600 mb-2">{rule.description}</p>
                          )}
                          <div className="text-sm text-gray-500">
                            <span>权重: {rule.weight}</span>
                            <span className="ml-4">创建时间: {new Date(rule.created_at).toLocaleString()}</span>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* 优先级计算 */}
      {activeTab === 'calculator' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calculator className="h-5 w-5" />
              优先级计算器
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">告警ID</label>
                <Input
                  value={scoreRequest.alert_id}
                  onChange={(e) => setScoreRequest({ ...scoreRequest, alert_id: e.target.value })}
                  placeholder="ALT-001"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">指标数据（JSON）</label>
                <textarea
                  value={scoreRequest.metrics}
                  onChange={(e) => setScoreRequest({ ...scoreRequest, metrics: e.target.value })}
                  className="w-full px-3 py-2 border rounded-md"
                  rows={4}
                  placeholder='{"cpu_usage": 95, "memory_usage": 80, "response_time": 5000}'
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">上下文信息（JSON，可选）</label>
                <textarea
                  value={scoreRequest.context}
                  onChange={(e) => setScoreRequest({ ...scoreRequest, context: e.target.value })}
                  className="w-full px-3 py-2 border rounded-md"
                  rows={3}
                  placeholder='{"service": "api-service", "affected_users": 1000}'
                />
              </div>
              <Button onClick={handleCalculateScore} disabled={scoreLoading}>
                {scoreLoading ? '计算中...' : '计算优先级'}
              </Button>

              {scoreResult && (
                <div className="mt-4 p-4 bg-gray-50 rounded">
                  <h3 className="font-medium mb-2">计算结果</h3>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-gray-600">告警ID:</span>
                      <span>{scoreResult.alert_id}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">优先级级别:</span>
                      <span className={`px-2 py-1 rounded text-xs ${getPriorityColor(scoreResult.priority_level)}`}>
                        {scoreResult.priority_level}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">优先级分数:</span>
                      <span className="font-medium">{scoreResult.score.toFixed(2)}</span>
                    </div>
                    {scoreResult.bis_score && (
                      <div className="flex justify-between">
                        <span className="text-gray-600">BIS分数:</span>
                        <span>{scoreResult.bis_score.toFixed(2)}</span>
                      </div>
                    )}
                    <div className="flex justify-between">
                      <span className="text-gray-600">计算时间:</span>
                      <span>{new Date(scoreResult.calculated_at).toLocaleString()}</span>
                    </div>
                    {scoreResult.factors && (
                      <div>
                        <span className="text-gray-600">影响因素:</span>
                        <pre className="mt-1 text-xs bg-white p-2 rounded">
                          {JSON.stringify(scoreResult.factors, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 变更历史 */}
      {activeTab === 'history' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <History className="h-5 w-5" />
              优先级变更历史
            </CardTitle>
          </CardHeader>
          <CardContent>
            {historyLoading ? (
              <div className="text-center text-gray-500 py-8">加载中...</div>
            ) : (
              <div className="space-y-3">
                {history?.map((item) => (
                  <div key={item.id} className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium">{item.alert_id}</span>
                      <span className="text-sm text-gray-500">
                        {new Date(item.changed_at).toLocaleString()}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 text-sm">
                      {item.old_priority && (
                        <span className={`px-2 py-1 rounded text-xs ${getPriorityColor(item.old_priority)}`}>
                          {item.old_priority}
                        </span>
                      )}
                      <span>→</span>
                      <span className={`px-2 py-1 rounded text-xs ${getPriorityColor(item.new_priority)}`}>
                        {item.new_priority}
                      </span>
                    </div>
                    {item.change_reason && (
                      <p className="text-sm text-gray-600 mt-2">原因: {item.change_reason}</p>
                    )}
                    {item.changed_by && (
                      <p className="text-sm text-gray-500">操作者: {item.changed_by}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
