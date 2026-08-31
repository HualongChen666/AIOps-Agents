'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import api from '@/lib/api'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useLoadingState, useToast } from '@/hooks/useEnhancements'
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI'
import { AuthorizationGuard } from '@/components/auth/AuthorizationGuard'
import {
  Layers,
  Palette,
  Layout,
  Globe,
  Plus,
  Edit,
  Trash2,
  RefreshCw,
  CheckCircle,
  XCircle,
  Code,
  Settings
} from 'lucide-react'

interface Component {
  component_id: string
  name: string
  type: string
  category: string
  description: string
  props: Record<string, any>
  code: string
  dependencies: string[]
  is_public: boolean
  status: string
  created_at: string
  updated_at: string
}

interface Theme {
  theme_id: string
  name: string
  base_theme: string
  colors: Record<string, string>
  fonts?: Record<string, string>
  spacing?: Record<string, any>
  is_default: boolean
  created_at: string
  updated_at: string
}

interface LayoutItem {
  layout_id: string
  name: string
  type: string
  structure: Record<string, any>
  breakpoints?: Record<string, any>
  is_default: boolean
  created_at: string
  updated_at: string
}

interface LocalizationData {
  language: string
  translations: Record<string, string>
}

export default function FrontendAdvancedPage() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<'components' | 'themes' | 'layouts' | 'localization'>('components')
  const [selectedItem, setSelectedItem] = useState<any>(null)
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [dialogMode, setDialogMode] = useState<'create' | 'edit'>('create')
  const [formData, setFormData] = useState<Record<string, any>>({})

  // 🔧 P1 Integration: Use enhanced loading state
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(false)

  // 🔧 P1 Integration: Use toast notifications
  const toast = useToast()
  const showSuccess = toast.success
  const showError = toast.error

  // 🔧 Fetch Components
  const { data: componentsData, isLoading: componentsLoading, error: componentsError, refetch: refetchComponents } = useQuery({
    queryKey: ['frontend-components'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/frontend/components?limit=100')
      return resp.data
    },
    refetchInterval: 60000,
  })

  // 🔧 Fetch Themes
  const { data: themesData, isLoading: themesLoading, error: themesError, refetch: refetchThemes } = useQuery({
    queryKey: ['frontend-themes'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/frontend/themes?limit=100')
      return resp.data
    },
    refetchInterval: 60000,
  })

  // 🔧 Fetch Layouts
  const { data: layoutsData, isLoading: layoutsLoading, error: layoutsError, refetch: refetchLayouts } = useQuery({
    queryKey: ['frontend-layouts'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/frontend/layouts?limit=100')
      return resp.data
    },
    refetchInterval: 60000,
  })

  // 🔧 Fetch Localization
  const { data: localizationData, isLoading: localizationLoading, error: localizationError, refetch: refetchLocalization } = useQuery({
    queryKey: ['frontend-localization'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/frontend/localization')
      return resp.data
    },
    refetchInterval: 120000,
  })

  // 🔧 Handle errors
  useEffect(() => {
    if (componentsError || themesError || layoutsError || localizationError) {
      const error = componentsError || themesError || layoutsError || localizationError
      showError('Failed to load frontend data')
      setPageError(error as Error)
    }
  }, [componentsError, themesError, layoutsError, localizationError, showError, setPageError])

  // 🔧 Create Component Mutation
  const createComponentMutation = useMutation({
    mutationFn: async (data: any) => {
      const resp = await api.post('/api/v1/frontend/components', data)
      return resp.data
    },
    onSuccess: () => {
      showSuccess('Component created successfully')
      queryClient.invalidateQueries({ queryKey: ['frontend-components'] })
      setIsDialogOpen(false)
    },
    onError: (error: any) => {
      showError(error.response?.data?.detail || 'Failed to create component')
    },
  })

  // 🔧 Update Component Mutation
  const updateComponentMutation = useMutation({
    mutationFn: async ({ componentId, data }: { componentId: string; data: any }) => {
      const resp = await api.patch(`/api/v1/frontend/components/${componentId}`, data)
      return resp.data
    },
    onSuccess: () => {
      showSuccess('Component updated successfully')
      queryClient.invalidateQueries({ queryKey: ['frontend-components'] })
      setIsDialogOpen(false)
    },
    onError: (error: any) => {
      showError(error.response?.data?.detail || 'Failed to update component')
    },
  })

  // 🔧 Delete Component Mutation
  const deleteComponentMutation = useMutation({
    mutationFn: async (componentId: string) => {
      const resp = await api.delete(`/api/v1/frontend/components/${componentId}`)
      return resp.data
    },
    onSuccess: () => {
      showSuccess('Component deleted successfully')
      queryClient.invalidateQueries({ queryKey: ['frontend-components'] })
    },
    onError: (error: any) => {
      showError(error.response?.data?.detail || 'Failed to delete component')
    },
  })

  // 🔧 Create Theme Mutation
  const createThemeMutation = useMutation({
    mutationFn: async (data: any) => {
      const resp = await api.post('/api/v1/frontend/themes', data)
      return resp.data
    },
    onSuccess: () => {
      showSuccess('Theme created successfully')
      queryClient.invalidateQueries({ queryKey: ['frontend-themes'] })
      setIsDialogOpen(false)
    },
    onError: (error: any) => {
      showError(error.response?.data?.detail || 'Failed to create theme')
    },
  })

  // 🔧 Create Layout Mutation
  const createLayoutMutation = useMutation({
    mutationFn: async (data: any) => {
      const resp = await api.post('/api/v1/frontend/layouts', data)
      return resp.data
    },
    onSuccess: () => {
      showSuccess('Layout created successfully')
      queryClient.invalidateQueries({ queryKey: ['frontend-layouts'] })
      setIsDialogOpen(false)
    },
    onError: (error: any) => {
      showError(error.response?.data?.detail || 'Failed to create layout')
    },
  })

  // 🔧 Update Localization Mutation
  const updateLocalizationMutation = useMutation({
    mutationFn: async (data: LocalizationData) => {
      const resp = await api.put('/api/v1/frontend/localization', data)
      return resp.data
    },
    onSuccess: () => {
      showSuccess('Localization updated successfully')
      queryClient.invalidateQueries({ queryKey: ['frontend-localization'] })
      setIsDialogOpen(false)
    },
    onError: (error: any) => {
      showError(error.response?.data?.detail || 'Failed to update localization')
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

    try {
      if (type === 'component') {
        await deleteComponentMutation.mutateAsync(id)
      }
    } catch (error) {
      showError('Delete operation failed')
    }
  }

  const handleSubmit = async () => {
    try {
      if (activeTab === 'components') {
        if (dialogMode === 'create') {
          await createComponentMutation.mutateAsync(formData)
        } else {
          await updateComponentMutation.mutateAsync({ componentId: selectedItem.component_id, data: formData })
        }
      } else if (activeTab === 'themes') {
        await createThemeMutation.mutateAsync(formData)
      } else if (activeTab === 'layouts') {
        await createLayoutMutation.mutateAsync(formData)
      } else if (activeTab === 'localization') {
        await updateLocalizationMutation.mutateAsync(formData)
      }
    } catch (error) {
      // Error handled in mutation callbacks
    }
  }

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'active':
        return 'bg-green-100 text-green-800'
      case 'inactive':
        return 'bg-gray-100 text-gray-800'
      case 'draft':
        return 'bg-yellow-100 text-yellow-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const components = componentsData?.data?.components || []
  const themes = themesData?.data?.themes || []
  const layouts = layoutsData?.data?.layouts || []
  const localization = localizationData?.data || {}

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
          description="无法加载前端数据，请稍后重试"
          action={<Button onClick={() => {
            refetchComponents()
            refetchThemes()
            refetchLayouts()
            refetchLocalization()
          }}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
          action={<Button onClick={() => {
            refetchComponents()
            refetchThemes()
            refetchLayouts()
            refetchLocalization()
          }}>重试</Button>}
        />
      </ErrorBoundary>
    )
  }

  return (
    <AuthorizationGuard requiredRole="admin" requiredPermission="frontend:manage">
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Settings className="h-8 w-8 text-[var(--accent-cyan)]" />
            <div>
              <h1 className="text-3xl font-bold text-gray-900">前端高级功能</h1>
              <p className="text-sm text-gray-500">组件、主题、布局和本地化管理</p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button
              onClick={() => {
                refetchComponents()
                refetchThemes()
                refetchLayouts()
                refetchLocalization()
              }}
              variant="outline"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              刷新
            </Button>
            <Button onClick={() => handleCreate(activeTab)}>
              <Plus className="h-4 w-4 mr-2" />
              新建
            </Button>
          </div>
        </div>

        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)}>
          <TabsList>
            <TabsTrigger value="components">
              <Layers className="h-4 w-4 mr-2" />
              组件管理
            </TabsTrigger>
            <TabsTrigger value="themes">
              <Palette className="h-4 w-4 mr-2" />
              主题管理
            </TabsTrigger>
            <TabsTrigger value="layouts">
              <Layout className="h-4 w-4 mr-2" />
              布局管理
            </TabsTrigger>
            <TabsTrigger value="localization">
              <Globe className="h-4 w-4 mr-2" />
              本地化
            </TabsTrigger>
          </TabsList>

          {/* Components Tab */}
          <TabsContent value="components">
            <Card>
              <CardHeader>
                <CardTitle>组件列表 ({components.length})</CardTitle>
              </CardHeader>
              <CardContent>
                {components.length === 0 ? (
                  <EmptyState
                    title="没有组件"
                    description="当前没有组件，点击新建按钮创建第一个组件"
                  />
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>ID</TableHead>
                        <TableHead>名称</TableHead>
                        <TableHead>类型</TableHead>
                        <TableHead>分类</TableHead>
                        <TableHead>状态</TableHead>
                        <TableHead>公共</TableHead>
                        <TableHead>操作</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {components.map((component: Component) => (
                        <TableRow key={component.component_id}>
                          <TableCell className="font-mono text-sm">{component.component_id}</TableCell>
                          <TableCell className="font-medium">{component.name}</TableCell>
                          <TableCell>{component.type}</TableCell>
                          <TableCell>{component.category}</TableCell>
                          <TableCell>
                            <Badge className={getStatusColor(component.status)}>
                              {component.status}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            {component.is_public ? (
                              <CheckCircle className="h-4 w-4 text-green-500" />
                            ) : (
                              <XCircle className="h-4 w-4 text-gray-400" />
                            )}
                          </TableCell>
                          <TableCell>
                            <div className="flex gap-2">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleEdit(component, 'component')}
                              >
                                <Edit className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleDelete(component.component_id, 'component')}
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

          {/* Themes Tab */}
          <TabsContent value="themes">
            <Card>
              <CardHeader>
                <CardTitle>主题列表 ({themes.length})</CardTitle>
              </CardHeader>
              <CardContent>
                {themes.length === 0 ? (
                  <EmptyState
                    title="没有主题"
                    description="当前没有主题，点击新建按钮创建第一个主题"
                  />
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>ID</TableHead>
                        <TableHead>名称</TableHead>
                        <TableHead>基础主题</TableHead>
                        <TableHead>默认</TableHead>
                        <TableHead>操作</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {themes.map((theme: Theme) => (
                        <TableRow key={theme.theme_id}>
                          <TableCell className="font-mono text-sm">{theme.theme_id}</TableCell>
                          <TableCell className="font-medium">{theme.name}</TableCell>
                          <TableCell>{theme.base_theme}</TableCell>
                          <TableCell>
                            {theme.is_default ? (
                              <CheckCircle className="h-4 w-4 text-green-500" />
                            ) : (
                              <XCircle className="h-4 w-4 text-gray-400" />
                            )}
                          </TableCell>
                          <TableCell>
                            <div className="flex gap-2">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleEdit(theme, 'theme')}
                              >
                                <Edit className="h-4 w-4" />
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

          {/* Layouts Tab */}
          <TabsContent value="layouts">
            <Card>
              <CardHeader>
                <CardTitle>布局列表 ({layouts.length})</CardTitle>
              </CardHeader>
              <CardContent>
                {layouts.length === 0 ? (
                  <EmptyState
                    title="没有布局"
                    description="当前没有布局，点击新建按钮创建第一个布局"
                  />
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>ID</TableHead>
                        <TableHead>名称</TableHead>
                        <TableHead>类型</TableHead>
                        <TableHead>默认</TableHead>
                        <TableHead>操作</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {layouts.map((layout: LayoutItem) => (
                        <TableRow key={layout.layout_id}>
                          <TableCell className="font-mono text-sm">{layout.layout_id}</TableCell>
                          <TableCell className="font-medium">{layout.name}</TableCell>
                          <TableCell>{layout.type}</TableCell>
                          <TableCell>
                            {layout.is_default ? (
                              <CheckCircle className="h-4 w-4 text-green-500" />
                            ) : (
                              <XCircle className="h-4 w-4 text-gray-400" />
                            )}
                          </TableCell>
                          <TableCell>
                            <div className="flex gap-2">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleEdit(layout, 'layout')}
                              >
                                <Edit className="h-4 w-4" />
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

          {/* Localization Tab */}
          <TabsContent value="localization">
            <Card>
              <CardHeader>
                <CardTitle>本地化设置</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {Object.entries(localization).map(([language, translations]: [string, any]) => (
                    <div key={language} className="p-4 border rounded-lg">
                      <div className="flex items-center justify-between mb-3">
                        <h3 className="font-medium">{language}</h3>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEdit({ language, translations }, 'localization')}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        {Object.entries(translations).slice(0, 4).map(([key, value]) => (
                          <div key={key}>
                            <div className="text-gray-500">{key}</div>
                            <div className="font-medium">{value as string}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Create/Edit Dialog */}
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>
                {dialogMode === 'create' ? '新建' : '编辑'} {activeTab === 'components' ? '组件' : activeTab === 'themes' ? '主题' : activeTab === 'layouts' ? '布局' : '本地化'}
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              {activeTab === 'components' && (
                <>
                  <div>
                    <label className="block text-sm font-medium mb-1">名称</label>
                    <Input
                      value={formData.name || ''}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      placeholder="组件名称"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">类型</label>
                    <Input
                      value={formData.type || ''}
                      onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                      placeholder="组件类型"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">分类</label>
                    <Input
                      value={formData.category || ''}
                      onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                      placeholder="组件分类"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">描述</label>
                    <Input
                      value={formData.description || ''}
                      onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                      placeholder="组件描述"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">代码</label>
                    <textarea
                      className="w-full p-2 border rounded-md min-h-[200px] font-mono text-sm"
                      value={formData.code || ''}
                      onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                      placeholder="组件代码"
                    />
                  </div>
                </>
              )}
              {activeTab === 'themes' && (
                <>
                  <div>
                    <label className="block text-sm font-medium mb-1">名称</label>
                    <Input
                      value={formData.name || ''}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      placeholder="主题名称"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">基础主题</label>
                    <Input
                      value={formData.base_theme || 'light'}
                      onChange={(e) => setFormData({ ...formData, base_theme: e.target.value })}
                      placeholder="light 或 dark"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">颜色配置 (JSON)</label>
                    <textarea
                      className="w-full p-2 border rounded-md min-h-[150px] font-mono text-sm"
                      value={typeof formData.colors === 'object' ? JSON.stringify(formData.colors, null, 2) : formData.colors || '{}'}
                      onChange={(e) => {
                        try {
                          setFormData({ ...formData, colors: JSON.parse(e.target.value) })
                        } catch {
                          setFormData({ ...formData, colors: e.target.value })
                        }
                      }}
                      placeholder='{"primary": "#3b82f6", "secondary": "#6366f1"}'
                    />
                  </div>
                </>
              )}
              {activeTab === 'layouts' && (
                <>
                  <div>
                    <label className="block text-sm font-medium mb-1">名称</label>
                    <Input
                      value={formData.name || ''}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      placeholder="布局名称"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">类型</label>
                    <Input
                      value={formData.type || ''}
                      onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                      placeholder="dashboard, page, modal 等"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">结构配置 (JSON)</label>
                    <textarea
                      className="w-full p-2 border rounded-md min-h-[150px] font-mono text-sm"
                      value={typeof formData.structure === 'object' ? JSON.stringify(formData.structure, null, 2) : formData.structure || '{}'}
                      onChange={(e) => {
                        try {
                          setFormData({ ...formData, structure: JSON.parse(e.target.value) })
                        } catch {
                          setFormData({ ...formData, structure: e.target.value })
                        }
                      }}
                      placeholder='{"header": {"height": 64}, "sidebar": {"width": 240}}'
                    />
                  </div>
                </>
              )}
              {activeTab === 'localization' && (
                <>
                  <div>
                    <label className="block text-sm font-medium mb-1">语言代码</label>
                    <Input
                      value={formData.language || ''}
                      onChange={(e) => setFormData({ ...formData, language: e.target.value })}
                      placeholder="en-US, zh-CN 等"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">翻译 (JSON)</label>
                    <textarea
                      className="w-full p-2 border rounded-md min-h-[150px] font-mono text-sm"
                      value={typeof formData.translations === 'object' ? JSON.stringify(formData.translations, null, 2) : formData.translations || '{}'}
                      onChange={(e) => {
                        try {
                          setFormData({ ...formData, translations: JSON.parse(e.target.value) })
                        } catch {
                          setFormData({ ...formData, translations: e.target.value })
                        }
                      }}
                      placeholder='{"welcome": "Welcome", "dashboard": "Dashboard"}'
                    />
                  </div>
                </>
              )}
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
                取消
              </Button>
              <Button onClick={handleSubmit} disabled={createComponentMutation.isPending || updateComponentMutation.isPending}>
                {dialogMode === 'create' ? '创建' : '更新'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </AuthorizationGuard>
  )
}
