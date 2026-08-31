'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import api from '@/lib/api';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLoadingState, useToast, useDebounce } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';
import { FileText, Plus, Trash2, Settings, RefreshCw, Book, Copy, Download, Upload, Eye, Edit, CheckCircle, Clock } from 'lucide-react';

interface Document {
  id: string;
  title: string;
  doc_type: string;
  content: string;
  author: string;
  version: string;
  status: 'draft' | 'published' | 'archived';
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

interface Template {
  id: string;
  template_name: string;
  doc_type: string;
  template_content: string;
  metadata: Record<string, any>;
  created_at: string;
}

interface DocumentVersion {
  id: string;
  doc_id: string;
  version: string;
  content: string;
  created_by: string;
  created_at: string;
  change_summary: string;
}

export default function DocumentationAdvancedPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'documents' | 'templates' | 'versions'>('documents');
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isViewDialogOpen, setIsViewDialogOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [newDocumentData, setNewDocumentData] = useState({
    title: '',
    doc_type: 'api_documentation',
    content: '',
    author: '',
    version: '1.0',
    metadata: {},
  });

  const debouncedSearch = useDebounce(searchTerm, 300);
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(false);
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // Fetch documents
  const { data: documents, isLoading: documentsLoading, error: documentsError, refetch: refetchDocuments } = useQuery<Document[]>({
    queryKey: ['documentation-documents'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/documentation/documents');
      return resp.data.documents || resp.data || [];
    },
    refetchInterval: 120000,
  });

  // Fetch templates
  const { data: templates, isLoading: templatesLoading, error: templatesError, refetch: refetchTemplates } = useQuery<Template[]>({
    queryKey: ['documentation-templates'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/documentation/templates');
      return resp.data.templates || resp.data || [];
    },
    refetchInterval: 300000,
  });

  // Fetch document versions
  const { data: documentVersions, isLoading: versionsLoading, error: versionsError, refetch: refetchVersions } = useQuery<DocumentVersion[]>({
    queryKey: ['documentation-versions'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/documentation/versions');
      return resp.data.versions || resp.data || [];
    },
    refetchInterval: 300000,
  });

  // Create document mutation
  const createDocumentMutation = useMutation({
    mutationFn: async (documentData: typeof newDocumentData) => {
      const resp = await api.post('/api/v1/documentation/documents', documentData);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('Document created successfully');
      setIsCreateDialogOpen(false);
      queryClient.invalidateQueries({ queryKey: ['documentation-documents'] });
    },
    onError: (error: any) => {
      showError(`Failed to create document: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Delete document mutation
  const deleteDocumentMutation = useMutation({
    mutationFn: async (documentId: string) => {
      const resp = await api.delete(`/api/v1/documentation/documents/${documentId}`);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('Document deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['documentation-documents'] });
    },
    onError: (error: any) => {
      showError(`Failed to delete document: ${error.response?.data?.detail || error.message}`);
    },
  });

  useEffect(() => {
    if (documentsError) {
      setPageError(documentsError as Error);
      showError('Failed to load documents');
    }
  }, [documentsError, setPageError, showError]);

  const filteredDocuments = documents?.filter((doc) => {
    if (typeFilter !== 'all' && doc.doc_type !== typeFilter) return false;
    if (statusFilter !== 'all' && doc.status !== statusFilter) return false;
    if (debouncedSearch && !doc.title.toLowerCase().includes(debouncedSearch.toLowerCase())) return false;
    return true;
  }) || [];

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'published':
        return 'bg-green-100 text-green-800';
      case 'draft':
        return 'bg-yellow-100 text-yellow-800';
      case 'archived':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const handleCreateDocument = () => {
    if (!newDocumentData.title || !newDocumentData.content) {
      showError('Please fill in title and content');
      return;
    }
    createDocumentMutation.mutate(newDocumentData);
  };

  const handleDeleteDocument = (documentId: string) => {
    if (!window.confirm('Are you sure you want to delete this document?')) return;
    deleteDocumentMutation.mutate(documentId);
  };

  if (pageLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (pageError) {
    return (
      <ErrorBoundary fallback={
        <EmptyState
          title="加载失败"
          description="无法加载文档数据，请稍后重试"
          action={<Button onClick={() => refetchDocuments()}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
          action={<Button onClick={() => refetchDocuments()}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <FileText className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">文档管理高级</h1>
            <p className="text-sm text-gray-500">文档、模板和版本管理</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => refetchDocuments()} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
          <Button onClick={() => setIsCreateDialogOpen(true)} size="sm">
            <Plus className="h-4 w-4 mr-2" />
            创建文档
          </Button>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="documents">
            <FileText className="h-4 w-4 mr-2" />
            文档
          </TabsTrigger>
          <TabsTrigger value="templates">
            <Book className="h-4 w-4 mr-2" />
            模板
          </TabsTrigger>
          <TabsTrigger value="versions">
            <Clock className="h-4 w-4 mr-2" />
            版本
          </TabsTrigger>
        </TabsList>

        <TabsContent value="documents" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <FileText className="h-5 w-5" />
                  文档管理
                </span>
                <div className="flex gap-2">
                  <Input
                    placeholder="搜索文档..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-64"
                  />
                  <Select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
                    <option value="all">全部类型</option>
                    <option value="api_documentation">API文档</option>
                    <option value="runbook">Runbook</option>
                    <option value="sop">SOP</option>
                    <option value="architecture">架构文档</option>
                    <option value="deployment">部署文档</option>
                  </Select>
                  <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                    <option value="all">全部状态</option>
                    <option value="draft">草稿</option>
                    <option value="published">已发布</option>
                    <option value="archived">已归档</option>
                  </Select>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {documentsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : filteredDocuments.length === 0 ? (
                <EmptyState
                  title="没有文档"
                  description="点击创建文档开始文档管理"
                  action={<Button onClick={() => setIsCreateDialogOpen(true)}>创建文档</Button>}
                />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>标题</TableHead>
                      <TableHead>类型</TableHead>
                      <TableHead>作者</TableHead>
                      <TableHead>版本</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>创建时间</TableHead>
                      <TableHead>更新时间</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredDocuments.map((doc) => (
                      <TableRow key={doc.id}>
                        <TableCell className="font-mono text-sm">{doc.id}</TableCell>
                        <TableCell className="font-medium">{doc.title}</TableCell>
                        <TableCell className="capitalize">{doc.doc_type.replace('_', ' ')}</TableCell>
                        <TableCell>{doc.author}</TableCell>
                        <TableCell>{doc.version}</TableCell>
                        <TableCell>
                          <Badge className={getStatusColor(doc.status)}>
                            {doc.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {new Date(doc.created_at).toLocaleString()}
                        </TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {new Date(doc.updated_at).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setSelectedDocument(doc);
                                setIsViewDialogOpen(true);
                              }}
                            >
                              <Eye className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setSelectedDocument(doc)}
                            >
                              <Edit className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeleteDocument(doc.id)}
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

        <TabsContent value="templates" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Book className="h-5 w-5" />
                模板管理
              </CardTitle>
            </CardHeader>
            <CardContent>
              {templatesLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : !templates || templates.length === 0 ? (
                <EmptyState title="无模板" description="暂无模板记录" />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>模板名称</TableHead>
                      <TableHead>文档类型</TableHead>
                      <TableHead>创建时间</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {templates.map((template) => (
                      <TableRow key={template.id}>
                        <TableCell className="font-mono text-sm">{template.id}</TableCell>
                        <TableCell className="font-medium">{template.template_name}</TableCell>
                        <TableCell className="capitalize">{template.doc_type.replace('_', ' ')}</TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {new Date(template.created_at).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <Button variant="ghost" size="sm">
                              <Copy className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="sm">
                              <Edit className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="sm">
                              <Download className="h-4 w-4" />
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

        <TabsContent value="versions" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="h-5 w-5" />
                版本历史
              </CardTitle>
            </CardHeader>
            <CardContent>
              {versionsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : !documentVersions || documentVersions.length === 0 ? (
                <EmptyState title="无版本记录" description="暂无版本历史记录" />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>文档ID</TableHead>
                      <TableHead>版本</TableHead>
                      <TableHead>创建者</TableHead>
                      <TableHead>变更摘要</TableHead>
                      <TableHead>创建时间</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {documentVersions.map((version) => (
                      <TableRow key={version.id}>
                        <TableCell className="font-mono text-sm">{version.id}</TableCell>
                        <TableCell className="font-mono text-sm">{version.doc_id}</TableCell>
                        <TableCell>{version.version}</TableCell>
                        <TableCell>{version.created_by}</TableCell>
                        <TableCell>{version.change_summary || '-'}</TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {new Date(version.created_at).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <Button variant="ghost" size="sm">
                              <Eye className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="sm">
                              <Copy className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="sm">
                              <CheckCircle className="h-4 w-4" />
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
      </Tabs>

      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>创建文档</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">标题</label>
              <Input
                value={newDocumentData.title}
                onChange={(e) => setNewDocumentData({ ...newDocumentData, title: e.target.value })}
                placeholder="输入文档标题"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">文档类型</label>
              <Select
                value={newDocumentData.doc_type}
                onChange={(e) => setNewDocumentData({ ...newDocumentData, doc_type: e.target.value })}
              >
                <option value="api_documentation">API文档</option>
                <option value="runbook">Runbook</option>
                <option value="sop">SOP</option>
                <option value="architecture">架构文档</option>
                <option value="deployment">部署文档</option>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">作者</label>
              <Input
                value={newDocumentData.author}
                onChange={(e) => setNewDocumentData({ ...newDocumentData, author: e.target.value })}
                placeholder="作者名称"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">版本</label>
              <Input
                value={newDocumentData.version}
                onChange={(e) => setNewDocumentData({ ...newDocumentData, version: e.target.value })}
                placeholder="例如: 1.0"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">内容</label>
              <Textarea
                value={newDocumentData.content}
                onChange={(e) => setNewDocumentData({ ...newDocumentData, content: e.target.value })}
                placeholder="输入文档内容（支持Markdown）"
                rows={10}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleCreateDocument} disabled={createDocumentMutation.isPending}>
              {createDocumentMutation.isPending ? '创建中...' : '创建'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={isViewDialogOpen} onOpenChange={setIsViewDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              {selectedDocument?.title}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="flex gap-4 text-sm text-gray-600">
              <span>版本: {selectedDocument?.version}</span>
              <span>作者: {selectedDocument?.author}</span>
              <span>类型: {selectedDocument?.doc_type}</span>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <pre className="whitespace-pre-wrap text-sm">{selectedDocument?.content}</pre>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsViewDialogOpen(false)}>
              关闭
            </Button>
            <Button variant="outline">
              <Copy className="h-4 w-4 mr-2" />
              复制
            </Button>
            <Button variant="outline">
              <Download className="h-4 w-4 mr-2" />
              下载
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
