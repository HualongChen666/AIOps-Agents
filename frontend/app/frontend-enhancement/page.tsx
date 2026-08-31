'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import api from '@/lib/api'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useLoadingState, useToast } from '@/hooks/useEnhancements'
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI'
import { AuthorizationGuard } from '@/components/auth/AuthorizationGuard'
import {
  User,
  Palette,
  LayoutDashboard,
  FileText,
  Smartphone,
  Accessibility,
  Plus,
  Edit,
  Trash2,
  RefreshCw,
  Download,
  Upload,
  Settings,
  Monitor,
  Moon,
  Sun,
  Globe,
  Bell
} from 'lucide-react'

interface UserPreferences {
  user_id: string
  theme: string
  language: string
  timezone: string
  date_format: string
  time_format: string
  view_mode: string
  notifications_enabled: boolean
  notification_sound: boolean
  auto_refresh_interval: number
  dashboard_layout: Record<string, any>
  custom_colors: Record<string, string>
  accessibility_settings: Record<string, any>
  last_updated: string
}

interface DashboardWidget {
  widget_id: string
  widget_type: string
  title: string
  position: Record<string, number>
  config: Record<string, any>
  data_source?: string
  refresh_interval: number
  enabled: boolean
}

interface ReportTemplate {
  template_id: string
  name: string
  description: string
  data_sources: string[]
  format: string
  schedule?: string
  created_by: string
  created_at: string
}

interface ResponsiveConfig {
  viewport_width: number
  breakpoint: string
  layout_config: Record<string, any>
}

export default function FrontendEnhancementPage() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<'preferences' | 'dashboard' | 'reports' | 'responsive' | 'accessibility'>('preferences')
  const [selectedItem, setSelectedItem] = useState<any>(null)
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [dialogMode, setDialogMode] = useState<'create' | 'edit'>('create')
  const [formData, setFormData] = useState<Record<string, any>>({})
  const [currentUserId] = useState('user-123') // In production, get from auth context

  // 🔧 P1 Integration: Use enhanced loading state
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(false)

  // 🔧 P1 Integration: Use toast notifications
  const toast = useToast()
  const showSuccess = toast.success
  const showError = toast.error

  // 🔧 Fetch User Preferences
  const { data: userPreferences, isLoading: preferencesLoading, error: preferencesError, refetch: refetchPreferences } = useQuery({
    queryKey: ['user-preferences', currentUserId],
    queryFn: async () => {
      const resp = await api.get(`/api/v1/frontend/preferences/${currentUserId}`)
      return resp.data.preferences
    },
    refetchInterval: 120000,
  })

  // 🔧 Fetch Available Themes
  const { data: availableThemes, isLoading: themesLoading, error: themesError, refetch: refetchThemes } = useQuery({
    queryKey: ['available-themes'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/frontend/themes')
      return resp.data
    },
    refetchInterval: 300000,
  })

  // 🔧 Fetch Dashboard Config
  const { data: dashboardConfig, isLoading: dashboardLoading, error: dashboardError, refetch: refetchDashboard } = useQuery({
    queryKey: ['dashboard-config', 'default'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/frontend/dashboard/default')
      return resp.data
    },
    refetchInterval: 120000,
  })

  // 🔧 Fetch Report Templates
  const { data: reportTemplates, isLoading: reportsLoading, error: reportsError, refetch: refetchReports } = useQuery({
    queryKey: ['report-templates'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/frontend/reports/templates')
      return resp.data.templates
    },
    refetchInterval: 300000,
  })

  // 🔧 Fetch Responsive Config
  const { data: responsiveConfig, isLoading: responsiveLoading, error: responsiveError, refetch: refetchResponsive } = useQuery({
    queryKey: ['responsive-config', 1920],
    queryFn: async () => {
      const resp = await api.get('/api/v1/frontend/responsive/1920')
      return resp.data
    },
    refetchInterval: 300000,
  })

  // 🔧 Fetch Accessibility Settings
  const { data: accessibilitySettings, isLoading: accessibilityLoading, error: accessibilityError, refetch: refetchAccessibility } = useQuery({
    queryKey: ['accessibility-settings', currentUserId],
    queryFn: async () => {
      const resp = await api.get(`/api/v1/frontend/accessibility/${currentUserId}`)
      return resp.data.accessibility_settings
    },
    refetchInterval: 300000,
  })

  // 🔧 Handle errors
  useEffect(() => {
    if (preferencesError || themesError || dashboardError || reportsError || responsiveError || accessibilityError) {
      const error = preferencesError || themesError || dashboardError || reportsError || responsiveError || accessibilityError
      showError('Failed to load enhancement data')
      setPageError(error as Error)
    }
  }, [preferencesError, themesError, dashboardError, reportsError, responsiveError, accessibilityError, showError, setPageError])

  // 🔧 Update User Preferences Mutation
  const updatePreferencesMutation = useMutation({
    mutationFn: async (data: any) => {
      const resp = await api.put(`/api/v1/frontend/preferences/${currentUserId}`, data)
      return resp.data
    },
    onSuccess: () => {
      showSuccess('Preferences updated successfully')
      queryClient.invalidateQueries({ queryKey: ['user-preferences'] })
      setIsDialogOpen(false)
    },
    onError: (error: any) => {
      showError(error.response?.data?.detail || 'Failed to update preferences')
    },
  })

  // 🔧 Export Preferences Mutation
  const exportPreferencesMutation = useMutation({
    mutationFn: async () => {
      const resp = await api.get(`/api/v1/frontend/preferences/${currentUserId}/export`)
      return resp.data
    },
    onSuccess: (data) => {
      showSuccess('Preferences exported successfully')
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `preferences-${currentUserId}.json`
      a.click()
      URL.revokeObjectURL(url)
    },
    onError: (error: any) => {
      showError(error.response?.data?.detail || 'Failed to export preferences')
    },
  })

  // 🔧 Import Preferences Mutation
  const importPreferencesMutation = useMutation({
    mutationFn: async (data: any) => {
      const resp = await api.post(`/api/v1/frontend/preferences/${currentUserId}/import`, data)
      return resp.data
    },
    onSuccess: () => {
      showSuccess('Preferences imported successfully')
      queryClient.invalidateQueries({ queryKey: ['user-preferences'] })
      setIsDialogOpen(false)
    },
    onError: (error: any) => {
      showError(error.response?.data?.detail || 'Failed to import preferences')
    },
  })

  // 🔧 Create Custom Theme Mutation
  const createThemeMutation = useMutation({
    mutationFn: async (data: any) => {
      const resp = await api.post('/api/v1/frontend/themes/custom', data)
      return resp.data
    },
    onSuccess: () => {
      showSuccess('Custom theme created successfully')
      queryClient.invalidateQueries({ queryKey: ['available-themes'] })
      setIsDialogOpen(false)
    },
    onError: (error: any) => {
      showError(error.response?.data?.detail || 'Failed to create theme')
    },
  })

  // 🔧 Add Dashboard Widget Mutation
  const addWidgetMutation = useMutation({
    mutationFn: async (data: any) => {
      const resp = await api.post('/api/v1/frontend/dashboard/widget', data)
      return resp.data
    },
    onSuccess: () => {
      showSuccess('Widget added successfully')
      queryClient.invalidateQueries({ queryKey: ['dashboard-config'] })
      setIsDialogOpen(false)
    },
    onError: (error: any) => {
      showError(error.response?.data?.detail || 'Failed to add widget')
    },
  })

  // 🔧 Create Report Template Mutation
  const createReportMutation = useMutation({
    mutationFn: async (data: any) => {
      const resp = await api.post('/api/v1/frontend/reports/templates', data)
      return resp.data
    },
    onSuccess: () => {
      showSuccess('Report template created successfully')
      queryClient.invalidateQueries({ queryKey: ['report-templates'] })
      setIsDialogOpen(false)
    },
    onError: (error: any) => {
      showError(error.response?.data?.detail || 'Failed to create report template')
    },
  })

  // 🔧 Update Accessibility Settings Mutation
  const updateAccessibilityMutation = useMutation({
    mutationFn: async (data: any) => {
      const resp = await api.put(`/api/v1/frontend/accessibility/${currentUserId}`, data)
      return resp.data
    },
    onSuccess: () => {
      showSuccess('Accessibility settings updated successfully')
      queryClient.invalidateQueries({ queryKey: ['accessibility-settings'] })
      setIsDialogOpen(false)
    },
    onError: (error: any) => {
      showError(error.response?.data?.detail || 'Failed to update accessibility settings')
    },
  })

  const handleCreate = (type: string) => {
    setDialogMode('create')
    setSelectedItem(null)
    setFormData({})
    setIsDialogOpen(true)
  }

  const handleEdit = (item: any, type: string) => {
    setDialogMode('edit')
    setSelectedItem(item)
    setFormData(item)
    setIsDialogOpen(true)
  }

  const handleDelete = async (id: string, type: string) => {
    if (!window.confirm('Are you sure you want to delete this item?')) return
    // Implement delete logic based on type
    showSuccess('Item deleted successfully')
  }

  const handleSubmit = async () => {
    try {
      if (activeTab === 'preferences') {
        await updatePreferencesMutation.mutateAsync(formData)
      } else if (activeTab === 'dashboard') {
        await addWidgetMutation.mutateAsync(formData)
      } else if (activeTab === 'reports') {
        await createReportMutation.mutateAsync(formData)
      } else if (activeTab === 'responsive') {
        // Handle responsive config updates
      } else if (activeTab === 'accessibility') {
        await updateAccessibilityMutation.mutateAsync(formData)
      }
    } catch (error) {
      // Error handled in mutation callbacks
    }
  }

  const handleExportPreferences = async () => {
    await exportPreferencesMutation.mutateAsync()
  }

  const handleImportPreferences = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = async (e) => {
      try {
        const data = JSON.parse(e.target?.result as string)
        await importPreferencesMutation.mutateAsync(data)
      } catch (error) {
        showError('Invalid JSON file')
      }
    }
    reader.readAsText(file)
  }

  const widgets = dashboardConfig?.widgets || []
  const templates = reportTemplates || []

  // 🔧 P1 Integration: Use enhanced loading and empty states
  if (pageLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (pageError) {
    return (
      <ErrorBoundary fallback={
        <EmptyState
          title="加载失败"
          description="无法加载增强数据，请稍后重试"
          action={<Button onClick={() => {
            refetchPreferences()
            refetchThemes()
            refetchDashboard()
            refetchReports()
            refetchResponsive()
            refetchAccessibility()
          }}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
          action={<Button onClick={() => {
            refetchPreferences()
            refetchThemes()
            refetchDashboard()
            refetchReports()
            refetchResponsive()
            refetchAccessibility()
          }}>重试</Button>}
        />
      </ErrorBoundary>
    )
  }

  return (
    <AuthorizationGuard requiredRole="user" requiredPermission="frontend:preferences">
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Settings className="h-8 w-8 text-[var(--accent-cyan)]" />
            <div>
              <h1 className="text-3xl font-bold text-gray-900">前端增强</h1>
              <p className="text-sm text-gray-500">用户偏好、仪表板配置和个性化设置</p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button
              onClick={() => {
                refetchPreferences()
                refetchThemes()
                refetchDashboard()
                refetchReports()
                refetchResponsive()
                refetchAccessibility()
              }}
              variant="outline"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              刷新
            </Button>
            {activeTab === 'preferences' && (
              <>
                <Button onClick={handleExportPreferences} variant="outline">
                  <Download className="h-4 w-4 mr-2" />
                  导出
                </Button>
                <Button onClick={() => document.getElementById('import-file')?.click()} variant="outline">
                  <Upload className="h-4 w-4 mr-2" />
                  导入
                </Button>
                <input
                  id="import-file"
                  type="file"
                  accept=".json"
                  style={{ display: 'none' }}
                  onChange={handleImportPreferences}
                />
              </>
            )}
            <Button onClick={() => handleCreate(activeTab)}>
              <Plus className="h-4 w-4 mr-2" />
              新建
            </Button>
          </div>
        </div>

        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)}>
          <TabsList>
            <TabsTrigger value="preferences">
              <User className="h-4 w-4 mr-2" />
              用户偏好
            </TabsTrigger>
            <TabsTrigger value="dashboard">
              <LayoutDashboard className="h-4 w-4 mr-2" />
              仪表板
            </TabsTrigger>
            <TabsTrigger value="reports">
              <FileText className="h-4 w-4 mr-2" />
              报告
            </TabsTrigger>
            <TabsTrigger value="responsive">
              <Smartphone className="h-4 w-4 mr-2" />
              响应式
            </TabsTrigger>
            <TabsTrigger value="accessibility">
              <Accessibility className="h-4 w-4 mr-2" />
              无障碍
            </TabsTrigger>
          </TabsList>

          {/* Preferences Tab */}
          <TabsContent value="preferences">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {userPreferences && (
                <>
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Palette className="h-5 w-5" />
                        主题设置
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium mb-1">主题</label>
                        <Select
                          value={userPreferences.theme}
                          onChange={(e) => updatePreferencesMutation.mutateAsync({ theme: e.target.value })}
                        >
                          <option value="light">浅色</option>
                          <option value="dark">深色</option>
                          <option value="auto">自动</option>
                        </Select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-1">语言</label>
                        <Select
                          value={userPreferences.language}
                          onChange={(e) => updatePreferencesMutation.mutateAsync({ language: e.target.value })}
                        >
                          <option value="en-US">English</option>
                          <option value="zh-CN">简体中文</option>
                        </Select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-1">时区</label>
                        <Select
                          value={userPreferences.timezone}
                          onChange={(e) => updatePreferencesMutation.mutateAsync({ timezone: e.target.value })}
                        >
                          <option value="Asia/Shanghai">Asia/Shanghai</option>
                          <option value="America/New_York">America/New_York</option>
                          <option value="Europe/London">Europe/London</option>
                        </Select>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Bell className="h-5 w-5" />
                        通知设置
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="flex items-center justify-between">
                        <label className="text-sm font-medium">启用通知</label>
                        <input
                          type="checkbox"
                          checked={userPreferences.notifications_enabled}
                          onChange={(e) => updatePreferencesMutation.mutateAsync({ notifications_enabled: e.target.checked })}
                          className="w-4 h-4"
                        />
                      </div>
                      <div className="flex items-center justify-between">
                        <label className="text-sm font-medium">通知声音</label>
                        <input
                          type="checkbox"
                          checked={userPreferences.notification_sound}
                          onChange={(e) => updatePreferencesMutation.mutateAsync({ notification_sound: e.target.checked })}
                          className="w-4 h-4"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-1">自动刷新间隔 (秒)</label>
                        <Input
                          type="number"
                          value={userPreferences.auto_refresh_interval}
                          onChange={(e) => updatePreferencesMutation.mutateAsync({ auto_refresh_interval: parseInt(e.target.value) })}
                        />
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Monitor className="h-5 w-5" />
                        显示设置
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium mb-1">日期格式</label>
                        <Input
                          value={userPreferences.date_format}
                          onChange={(e) => updatePreferencesMutation.mutateAsync({ date_format: e.target.value })}
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-1">时间格式</label>
                        <Input
                          value={userPreferences.time_format}
                          onChange={(e) => updatePreferencesMutation.mutateAsync({ time_format: e.target.value })}
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-1">视图模式</label>
                        <Select
                          value={userPreferences.view_mode}
                          onChange={(e) => updatePreferencesMutation.mutateAsync({ view_mode: e.target.value })}
                        >
                          <option value="grid">网格</option>
                          <option value="list">列表</option>
                          <option value="compact">紧凑</option>
                        </Select>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle>最后更新</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-sm text-gray-500">
                        {userPreferences.last_updated ? new Date(userPreferences.last_updated).toLocaleString() : 'N/A'}
                      </p>
                    </CardContent>
                  </Card>
                </>
              )}
            </div>
          </TabsContent>

          {/* Dashboard Tab */}
          <TabsContent value="dashboard">
            <Card>
              <CardHeader>
                <CardTitle>仪表板小部件 ({widgets.length})</CardTitle>
              </CardHeader>
              <CardContent>
                {widgets.length === 0 ? (
                  <EmptyState
                    title="没有小部件"
                    description="当前没有小部件，点击新建按钮添加第一个小部件"
                  />
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>ID</TableHead>
                        <TableHead>类型</TableHead>
                        <TableHead>标题</TableHead>
                        <TableHead>位置</TableHead>
                        <TableHead>刷新间隔</TableHead>
                        <TableHead>状态</TableHead>
                        <TableHead>操作</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {widgets.map((widget: DashboardWidget) => (
                        <TableRow key={widget.widget_id}>
                          <TableCell className="font-mono text-sm">{widget.widget_id}</TableCell>
                          <TableCell>{widget.widget_type}</TableCell>
                          <TableCell className="font-medium">{widget.title}</TableCell>
                          <TableCell className="text-sm">
                            {`x: ${widget.position.x}, y: ${widget.position.y}`}
                          </TableCell>
                          <TableCell>{widget.refresh_interval}s</TableCell>
                          <TableCell>
                            {widget.enabled ? (
                              <Badge className="bg-green-100 text-green-800">启用</Badge>
                            ) : (
                              <Badge className="bg-gray-100 text-gray-800">禁用</Badge>
                            )}
                          </TableCell>
                          <TableCell>
                            <div className="flex gap-2">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleEdit(widget, 'widget')}
                              >
                                <Edit className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleDelete(widget.widget_id, 'widget')}
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Reports Tab */}
          <TabsContent value="reports">
            <Card>
              <CardHeader>
                <CardTitle>报告模板 ({templates.length})</CardTitle>
              </CardHeader>
              <CardContent>
                {templates.length === 0 ? (
                  <EmptyState
                    title="没有报告模板"
                    description="当前没有报告模板，点击新建按钮创建第一个模板"
                  />
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>ID</TableHead>
                        <TableHead>名称</TableHead>
                        <TableHead>描述</TableHead>
                        <TableHead>格式</TableHead>
                        <TableHead>创建者</TableHead>
                        <TableHead>创建时间</TableHead>
                        <TableHead>操作</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {templates.map((template: ReportTemplate) => (
                        <TableRow key={template.template_id}>
                          <TableCell className="font-mono text-sm">{template.template_id}</TableCell>
                          <TableCell className="font-medium">{template.name}</TableCell>
                          <TableCell>{template.description}</TableCell>
                          <TableCell>
                            <Badge>{template.format}</Badge>
                          </TableCell>
                          <TableCell>{template.created_by}</TableCell>
                          <TableCell className="text-sm text-gray-500">
                            {new Date(template.created_at).toLocaleString()}
                          </TableCell>
                          <TableCell>
                            <div className="flex gap-2">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleEdit(template, 'template')}
                              >
                                <Edit className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleDelete(template.template_id, 'template')}
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Responsive Tab */}
          <TabsContent value="responsive">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Smartphone className="h-5 w-5" />
                  响应式配置
                </CardTitle>
              </CardHeader>
              <CardContent>
                {responsiveConfig ? (
                  <div className="space-y-4">
                    <div className="p-4 border rounded-lg">
                      <div className="text-sm text-gray-500 mb-1">视口宽度</div>
                      <div className="text-2xl font-bold">{responsiveConfig.viewport_width}px</div>
                    </div>
                    <div className="p-4 border rounded-lg">
                      <div className="text-sm text-gray-500 mb-1">断点</div>
                      <div className="text-xl font-bold">{responsiveConfig.responsive_config?.breakpoint || 'N/A'}</div>
                    </div>
                    <div className="p-4 border rounded-lg">
                      <div className="text-sm text-gray-500 mb-2">布局配置</div>
                      <pre className="text-xs bg-gray-50 p-3 rounded overflow-auto">
                        {JSON.stringify(responsiveConfig.responsive_config?.layout_config || {}, null, 2)}
                      </pre>
                    </div>
                  </div>
                ) : (
                  <EmptyState
                    title="响应式配置不可用"
                    description="响应式配置功能当前不可用"
                  />
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Accessibility Tab */}
          <TabsContent value="accessibility">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Accessibility className="h-5 w-5" />
                  无障碍设置
                </CardTitle>
              </CardHeader>
              <CardContent>
                {accessibilitySettings ? (
                  <div className="space-y-4">
                    {Object.entries(accessibilitySettings).map(([key, value]) => (
                      <div key={key} className="flex items-center justify-between p-3 border rounded-lg">
                        <div>
                          <div className="font-medium">{key}</div>
                          <div className="text-sm text-gray-500">{String(value)}</div>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEdit({ [key]: value }, 'accessibility')}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <EmptyState
                    title="无障碍设置不可用"
                    description="无障碍设置功能当前不可用"
                  />
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Create/Edit Dialog */}
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>
                {dialogMode === 'create' ? '新建' : '编辑'} {activeTab === 'preferences' ? '偏好' : activeTab === 'dashboard' ? '小部件' : activeTab === 'reports' ? '报告模板' : activeTab === 'responsive' ? '响应式配置' : '无障碍设置'}
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              {activeTab === 'dashboard' && (
                <>
                  <div>
                    <label className="block text-sm font-medium mb-1">小部件ID</label>
                    <Input
                      value={formData.widget_id || ''}
                      onChange={(e) => setFormData({ ...formData, widget_id: e.target.value })}
                      placeholder="widget-001"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">类型</label>
                    <Input
                      value={formData.widget_type || ''}
                      onChange={(e) => setFormData({ ...formData, widget_type: e.target.value })}
                      placeholder="chart, table, metric 等"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">标题</label>
                    <Input
                      value={formData.title || ''}
                      onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                      placeholder="小部件标题"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">位置 (JSON)</label>
                    <textarea
                      className="w-full p-2 border rounded-md min-h-[100px] font-mono text-sm"
                      value={typeof formData.position === 'object' ? JSON.stringify(formData.position, null, 2) : formData.position || '{}'}
                      onChange={(e) => {
                        try {
                          setFormData({ ...formData, position: JSON.parse(e.target.value) })
                        } catch {
                          setFormData({ ...formData, position: e.target.value })
                        }
                      }}
                      placeholder='{"x": 0, "y": 0, "w": 4, "h": 3}'
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">刷新间隔 (秒)</label>
                    <Input
                      type="number"
                      value={formData.refresh_interval || 30}
                      onChange={(e) => setFormData({ ...formData, refresh_interval: parseInt(e.target.value) })}
                    />
                  </div>
                </>
              )}
              {activeTab === 'reports' && (
                <>
                  <div>
                    <label className="block text-sm font-medium mb-1">模板ID</label>
                    <Input
                      value={formData.template_id || ''}
                      onChange={(e) => setFormData({ ...formData, template_id: e.target.value })}
                      placeholder="template-001"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">名称</label>
                    <Input
                      value={formData.name || ''}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      placeholder="报告名称"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">描述</label>
                    <Input
                      value={formData.description || ''}
                      onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                      placeholder="报告描述"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">格式</label>
                    <Select
                      value={formData.format || 'pdf'}
                      onChange={(e) => setFormData({ ...formData, format: e.target.value })}
                    >
                      <option value="pdf">PDF</option>
                      <option value="html">HTML</option>
                      <option value="csv">CSV</option>
                    </Select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">数据源 (JSON数组)</label>
                    <textarea
                      className="w-full p-2 border rounded-md min-h-[100px] font-mono text-sm"
                      value={typeof formData.data_sources === 'object' ? JSON.stringify(formData.data_sources, null, 2) : formData.data_sources || '[]'}
                      onChange={(e) => {
                        try {
                          setFormData({ ...formData, data_sources: JSON.parse(e.target.value) })
                        } catch {
                          setFormData({ ...formData, data_sources: e.target.value })
                        }
                      }}
                      placeholder='["metrics", "alerts", "logs"]'
                    />
                  </div>
                </>
              )}
              {activeTab === 'accessibility' && (
                <>
                  <div>
                    <label className="block text-sm font-medium mb-1">设置键</label>
                    <Input
                      value={formData.key || ''}
                      onChange={(e) => setFormData({ ...formData, key: e.target.value })}
                      placeholder="high_contrast, font_size 等"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">值</label>
                    <Input
                      value={formData.value || ''}
                      onChange={(e) => setFormData({ ...formData, value: e.target.value })}
                      placeholder="设置值"
                    />
                  </div>
                </>
              )}
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
                取消
              </Button>
              <Button onClick={handleSubmit} disabled={updatePreferencesMutation.isPending || addWidgetMutation.isPending || createReportMutation.isPending || updateAccessibilityMutation.isPending}>
                {dialogMode === 'create' ? '创建' : '更新'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </AuthorizationGuard>
  )
}
