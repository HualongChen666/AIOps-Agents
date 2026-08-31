'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select-shadcn'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import api from '@/lib/api'
import toast from 'react-hot-toast'

// Types based on backend API
interface FrameworkType {
  value: string
  label: string
}

interface ParallelMode {
  value: string
  label: string
}

interface TestFrameworkConfig {
  id: string
  framework: string
  version: string
  enabled: boolean
  config: Record<string, any>
  test_paths: string[]
  exclude_patterns: string[]
  parallel_mode: string
  parallel_workers: number
  timeout: number
  retry_count: number
  coverage_enabled: boolean
  coverage_threshold: number
  reporting_enabled: boolean
  report_formats: string[]
  created_at: string
  updated_at: string
  created_by: string
}

interface FrameworkStatus {
  total_frameworks: number
  enabled_frameworks: number
  frameworks: Array<{
    id: string
    framework: string
    version: string
    enabled: boolean
    test_paths: string[]
    parallel_mode: string
    parallel_workers: number
  }>
  timestamp: string
}

interface ValidationResult {
  valid: boolean
  errors: string[]
  warnings: string[]
  config_id: string
  framework: string
}

const FRAMEWORK_TYPES: FrameworkType[] = [
  { value: 'pytest', label: 'Pytest' },
  { value: 'junit', label: 'JUnit' },
  { value: 'selenium', label: 'Selenium' },
  { value: 'cypress', label: 'Cypress' },
  { value: 'locust', label: 'Locust' },
  { value: 'jest', label: 'Jest' },
]

const PARALLEL_MODES: ParallelMode[] = [
  { value: 'none', label: 'None' },
  { value: 'processes', label: 'Processes' },
  { value: 'threads', label: 'Threads' },
  { value: 'distributed', label: 'Distributed' },
]

const REPORT_FORMATS = ['html', 'json', 'xml', 'junit', 'markdown']

// API Functions
const fetchFrameworkConfigurations = async (framework?: string, enabledOnly?: boolean): Promise<TestFrameworkConfig[]> => {
  const params = new URLSearchParams()
  if (framework) params.append('framework', framework)
  if (enabledOnly) params.append('enabled_only', 'true')

  const response = await api.get(`/api/v1/test-framework/configurations?${params.toString()}`)
  return response.data
}

const fetchFrameworkConfiguration = async (id: string): Promise<TestFrameworkConfig> => {
  const response = await api.get(`/api/v1/test-framework/configurations/${id}`)
  return response.data
}

const fetchFrameworkStatus = async (): Promise<FrameworkStatus> => {
  const response = await api.get('/api/v1/test-framework/status')
  return response.data
}

const updateFrameworkConfiguration = async ({ id, data }: { id: string; data: Partial<TestFrameworkConfig> }): Promise<TestFrameworkConfig> => {
  const response = await api.patch(`/api/v1/test-framework/configurations/${id}`, data)
  return response.data
}

const validateFrameworkConfiguration = async (id: string): Promise<ValidationResult> => {
  const response = await api.post(`/api/v1/test-framework/configurations/${id}/validate`)
  return response.data
}

// Main Component
export default function TestFrameworkAdvancedPage() {
  const queryClient = useQueryClient()
  const [selectedFramework, setSelectedFramework] = useState<string>('')
  const [enabledOnly, setEnabledOnly] = useState(false)
  const [selectedConfig, setSelectedConfig] = useState<TestFrameworkConfig | null>(null)
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false)
  const [editFormData, setEditFormData] = useState<Partial<TestFrameworkConfig>>({})

  // Queries
  const { data: configurations, isLoading: configurationsLoading, error: configurationsError } = useQuery({
    queryKey: ['framework-configurations', selectedFramework, enabledOnly],
    queryFn: () => fetchFrameworkConfigurations(selectedFramework, enabledOnly),
  })

  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: ['framework-status'],
    queryFn: fetchFrameworkStatus,
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  // Mutations
  const updateMutation = useMutation({
    mutationFn: updateFrameworkConfiguration,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['framework-configurations'] })
      queryClient.invalidateQueries({ queryKey: ['framework-status'] })
      toast.success('配置更新成功')
      setIsEditDialogOpen(false)
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || '配置更新失败')
    },
  })

  const validateMutation = useMutation({
    mutationFn: validateFrameworkConfiguration,
    onSuccess: (result) => {
      if (result.valid) {
        toast.success('配置验证通过')
      } else {
        toast.error(`配置验证失败: ${result.errors.join(', ')}`)
      }
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || '配置验证失败')
    },
  })

  // Handlers
  const handleEditClick = (config: TestFrameworkConfig) => {
    setSelectedConfig(config)
    setEditFormData({ ...config })
    setIsEditDialogOpen(true)
  }

  const handleSaveConfig = () => {
    if (!selectedConfig) return
    updateMutation.mutate({
      id: selectedConfig.id,
      data: editFormData,
    })
  }

  const handleValidateClick = (config: TestFrameworkConfig) => {
    validateMutation.mutate(config.id)
  }

  const handleToggleEnabled = (config: TestFrameworkConfig) => {
    updateMutation.mutate({
      id: config.id,
      data: { enabled: !config.enabled },
    })
  }

  if (configurationsLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">加载中...</div>
      </div>
    )
  }

  if (configurationsError) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="text-red-800">加载数据失败</div>
        <Button onClick={() => queryClient.invalidateQueries({ queryKey: ['framework-configurations'] })} className="mt-2">
          重试
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">测试框架高级配置</h1>
        <Button
          onClick={() => queryClient.invalidateQueries({ queryKey: ['framework-configurations', 'framework-status'] })}
          variant="outline"
        >
          刷新
        </Button>
      </div>

      <Tabs defaultValue="configurations" className="space-y-4">
        <TabsList>
          <TabsTrigger value="configurations">框架配置</TabsTrigger>
          <TabsTrigger value="execution">执行配置</TabsTrigger>
          <TabsTrigger value="reports">报告配置</TabsTrigger>
          <TabsTrigger value="environment">环境配置</TabsTrigger>
          <TabsTrigger value="status">状态概览</TabsTrigger>
        </TabsList>

        {/* Configurations Tab */}
        <TabsContent value="configurations" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>配置筛选</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex gap-4 items-end">
                <div className="flex-1">
                  <Label htmlFor="framework-filter">框架类型</Label>
                  <Select value={selectedFramework} onValueChange={setSelectedFramework}>
                    <SelectTrigger id="framework-filter">
                      <SelectValue placeholder="全部框架" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">全部框架</SelectItem>
                      {FRAMEWORK_TYPES.map((type) => (
                        <SelectItem key={type.value} value={type.value}>
                          {type.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex items-center space-x-2">
                  <Switch
                    id="enabled-only"
                    checked={enabledOnly}
                    onCheckedChange={setEnabledOnly}
                  />
                  <Label htmlFor="enabled-only">仅显示启用</Label>
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-4">
            {configurations?.map((config) => (
              <Card key={config.id}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="flex items-center gap-2">
                      {config.framework} - {config.version}
                      <Badge variant={config.enabled ? 'default' : 'secondary'}>
                        {config.enabled ? '启用' : '禁用'}
                      </Badge>
                    </CardTitle>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleValidateClick(config)}
                        disabled={validateMutation.isPending}
                      >
                        验证
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleEditClick(config)}
                      >
                        编辑
                      </Button>
                      <Button
                        size="sm"
                        variant={config.enabled ? 'destructive' : 'default'}
                        onClick={() => handleToggleEnabled(config)}
                        disabled={updateMutation.isPending}
                      >
                        {config.enabled ? '禁用' : '启用'}
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="font-semibold">ID:</span> {config.id}
                    </div>
                    <div>
                      <span className="font-semibold">创建者:</span> {config.created_by}
                    </div>
                    <div>
                      <span className="font-semibold">并行模式:</span> {config.parallel_mode}
                    </div>
                    <div>
                      <span className="font-semibold">并行工作数:</span> {config.parallel_workers}
                    </div>
                    <div>
                      <span className="font-semibold">超时(秒):</span> {config.timeout}
                    </div>
                    <div>
                      <span className="font-semibold">重试次数:</span> {config.retry_count}
                    </div>
                    <div>
                      <span className="font-semibold">覆盖率:</span>{' '}
                      {config.coverage_enabled ? `${config.coverage_threshold}%` : '禁用'}
                    </div>
                    <div>
                      <span className="font-semibold">报告:</span>{' '}
                      {config.reporting_enabled ? config.report_formats.join(', ') : '禁用'}
                    </div>
                  </div>
                  <div className="mt-4">
                    <span className="font-semibold text-sm">测试路径:</span>
                    <div className="mt-1 flex flex-wrap gap-2">
                      {config.test_paths.map((path, idx) => (
                        <Badge key={idx} variant="outline">
                          {path}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <div className="mt-4">
                    <span className="font-semibold text-sm">排除模式:</span>
                    <div className="mt-1 flex flex-wrap gap-2">
                      {config.exclude_patterns.map((pattern, idx) => (
                        <Badge key={idx} variant="outline">
                          {pattern}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <div className="mt-4 text-xs text-gray-500">
                    创建时间: {new Date(config.created_at).toLocaleString()} | 更新时间:{' '}
                    {new Date(config.updated_at).toLocaleString()}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Execution Configuration Tab */}
        <TabsContent value="execution" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>执行配置</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {configurations?.map((config) => (
                  <div key={config.id} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="font-semibold">{config.framework} - {config.version}</h3>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleEditClick(config)}
                      >
                        配置
                      </Button>
                    </div>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="font-semibold">并行模式:</span> {config.parallel_mode}
                      </div>
                      <div>
                        <span className="font-semibold">并行工作数:</span> {config.parallel_workers}
                      </div>
                      <div>
                        <span className="font-semibold">超时(秒):</span> {config.timeout}
                      </div>
                      <div>
                        <span className="font-semibold">重试次数:</span> {config.retry_count}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Reports Configuration Tab */}
        <TabsContent value="reports" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>报告配置</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {configurations?.map((config) => (
                  <div key={config.id} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="font-semibold">{config.framework} - {config.version}</h3>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleEditClick(config)}
                      >
                        配置
                      </Button>
                    </div>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="font-semibold">报告启用:</span>{' '}
                        {config.reporting_enabled ? '是' : '否'}
                      </div>
                      <div>
                        <span className="font-semibold">报告格式:</span>{' '}
                        {config.report_formats.join(', ')}
                      </div>
                      <div>
                        <span className="font-semibold">覆盖率启用:</span>{' '}
                        {config.coverage_enabled ? '是' : '否'}
                      </div>
                      <div>
                        <span className="font-semibold">覆盖率阈值:</span>{' '}
                        {config.coverage_threshold}%
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Environment Configuration Tab */}
        <TabsContent value="environment" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>环境配置</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {configurations?.map((config) => (
                  <div key={config.id} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="font-semibold">{config.framework} - {config.version}</h3>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleEditClick(config)}
                      >
                        配置
                      </Button>
                    </div>
                    <div className="space-y-2 text-sm">
                      <div>
                        <span className="font-semibold">测试路径:</span>
                        <div className="mt-1 flex flex-wrap gap-2">
                          {config.test_paths.map((path, idx) => (
                            <Badge key={idx} variant="outline">
                              {path}
                            </Badge>
                          ))}
                        </div>
                      </div>
                      <div>
                        <span className="font-semibold">排除模式:</span>
                        <div className="mt-1 flex flex-wrap gap-2">
                          {config.exclude_patterns.map((pattern, idx) => (
                            <Badge key={idx} variant="outline">
                              {pattern}
                            </Badge>
                          ))}
                        </div>
                      </div>
                      <div>
                        <span className="font-semibold">自定义配置:</span>
                        <pre className="mt-1 bg-gray-50 p-2 rounded text-xs overflow-auto">
                          {JSON.stringify(config.config, null, 2)}
                        </pre>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Status Tab */}
        <TabsContent value="status" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>框架状态概览</CardTitle>
            </CardHeader>
            <CardContent>
              {statusLoading ? (
                <div className="text-gray-500">加载状态中...</div>
              ) : status ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-blue-50 p-4 rounded-lg">
                      <div className="text-2xl font-bold text-blue-900">{status.total_frameworks}</div>
                      <div className="text-sm text-blue-700">总框架数</div>
                    </div>
                    <div className="bg-green-50 p-4 rounded-lg">
                      <div className="text-2xl font-bold text-green-900">{status.enabled_frameworks}</div>
                      <div className="text-sm text-green-700">启用框架数</div>
                    </div>
                  </div>
                  <div>
                    <h3 className="font-semibold mb-2">框架详情</h3>
                    <div className="space-y-2">
                      {status.frameworks.map((fw) => (
                        <div key={fw.id} className="border rounded-lg p-3 flex items-center justify-between">
                          <div>
                            <div className="font-medium">{fw.framework} - {fw.version}</div>
                            <div className="text-sm text-gray-500">
                              并行: {fw.parallel_mode} ({fw.parallel_workers} workers)
                            </div>
                          </div>
                          <Badge variant={fw.enabled ? 'default' : 'secondary'}>
                            {fw.enabled ? '启用' : '禁用'}
                          </Badge>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="text-xs text-gray-500">
                    最后更新: {new Date(status.timestamp).toLocaleString()}
                  </div>
                </div>
              ) : (
                <div className="text-gray-500">无状态数据</div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Edit Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>编辑配置 - {selectedConfig?.framework}</DialogTitle>
          </DialogHeader>
          {selectedConfig && (
            <div className="space-y-4">
              <div className="flex items-center space-x-2">
                <Switch
                  id="edit-enabled"
                  checked={editFormData.enabled ?? false}
                  onCheckedChange={(checked) => setEditFormData({ ...editFormData, enabled: checked })}
                />
                <Label htmlFor="edit-enabled">启用配置</Label>
              </div>

              <div>
                <Label htmlFor="edit-parallel-mode">并行模式</Label>
                <Select
                  value={editFormData.parallel_mode}
                  onValueChange={(value) => setEditFormData({ ...editFormData, parallel_mode: value })}
                >
                  <SelectTrigger id="edit-parallel-mode">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {PARALLEL_MODES.map((mode) => (
                      <SelectItem key={mode.value} value={mode.value}>
                        {mode.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="edit-parallel-workers">并行工作数 (1-32)</Label>
                <Input
                  id="edit-parallel-workers"
                  type="number"
                  min="1"
                  max="32"
                  value={editFormData.parallel_workers ?? 1}
                  onChange={(e) => setEditFormData({ ...editFormData, parallel_workers: parseInt(e.target.value) })}
                />
              </div>

              <div>
                <Label htmlFor="edit-timeout">超时时间(秒) (1-3600)</Label>
                <Input
                  id="edit-timeout"
                  type="number"
                  min="1"
                  max="3600"
                  value={editFormData.timeout ?? 300}
                  onChange={(e) => setEditFormData({ ...editFormData, timeout: parseInt(e.target.value) })}
                />
              </div>

              <div>
                <Label htmlFor="edit-retry-count">重试次数 (0-5)</Label>
                <Input
                  id="edit-retry-count"
                  type="number"
                  min="0"
                  max="5"
                  value={editFormData.retry_count ?? 0}
                  onChange={(e) => setEditFormData({ ...editFormData, retry_count: parseInt(e.target.value) })}
                />
              </div>

              <div className="flex items-center space-x-2">
                <Switch
                  id="edit-coverage-enabled"
                  checked={editFormData.coverage_enabled ?? false}
                  onCheckedChange={(checked) => setEditFormData({ ...editFormData, coverage_enabled: checked })}
                />
                <Label htmlFor="edit-coverage-enabled">启用覆盖率</Label>
              </div>

              <div>
                <Label htmlFor="edit-coverage-threshold">覆盖率阈值 (%) (0-100)</Label>
                <Input
                  id="edit-coverage-threshold"
                  type="number"
                  min="0"
                  max="100"
                  step="0.1"
                  value={editFormData.coverage_threshold ?? 80}
                  onChange={(e) => setEditFormData({ ...editFormData, coverage_threshold: parseFloat(e.target.value) })}
                />
              </div>

              <div className="flex items-center space-x-2">
                <Switch
                  id="edit-reporting-enabled"
                  checked={editFormData.reporting_enabled ?? false}
                  onCheckedChange={(checked) => setEditFormData({ ...editFormData, reporting_enabled: checked })}
                />
                <Label htmlFor="edit-reporting-enabled">启用报告</Label>
              </div>

              <div>
                <Label>报告格式</Label>
                <div className="mt-2 space-y-2">
                  {REPORT_FORMATS.map((format) => (
                    <div key={format} className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        id={`format-${format}`}
                        checked={(editFormData.report_formats ?? []).includes(format)}
                        onChange={(e) => {
                          const formats = editFormData.report_formats ?? []
                          if (e.target.checked) {
                            setEditFormData({ ...editFormData, report_formats: [...formats, format] })
                          } else {
                            setEditFormData({ ...editFormData, report_formats: formats.filter(f => f !== format) })
                          }
                        }}
                      />
                      <Label htmlFor={`format-${format}`}>{format}</Label>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <Label htmlFor="edit-test-paths">测试路径 (每行一个)</Label>
                <Textarea
                  id="edit-test-paths"
                  value={(editFormData.test_paths ?? []).join('\n')}
                  onChange={(e) => setEditFormData({
                    ...editFormData,
                    test_paths: e.target.value.split('\n').filter(p => p.trim())
                  })}
                  rows={3}
                />
              </div>

              <div>
                <Label htmlFor="edit-exclude-patterns">排除模式 (每行一个)</Label>
                <Textarea
                  id="edit-exclude-patterns"
                  value={(editFormData.exclude_patterns ?? []).join('\n')}
                  onChange={(e) => setEditFormData({
                    ...editFormData,
                    exclude_patterns: e.target.value.split('\n').filter(p => p.trim())
                  })}
                  rows={3}
                />
              </div>

              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setIsEditDialogOpen(false)}>
                  取消
                </Button>
                <Button onClick={handleSaveConfig} disabled={updateMutation.isPending}>
                  {updateMutation.isPending ? '保存中...' : '保存'}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
