'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { EnhancedModal } from '@/components/ui/EnhancedModal';
import { DataTable } from '@/components/ui/DataTable';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { KpiCard } from '@/components/ui/KpiCard';
import { FileText, RefreshCw, Plus, Edit, Eye, Trash2, BookOpen, Settings } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';

interface Document {
  doc_id: string;
  title: string;
  doc_type: string;
  status: string;
  version: string;
  author: string;
  last_updated: string;
  content?: string;
}

interface DocumentationStatus {
  total_documents: number;
  published_documents: number;
  draft_documents: number;
  archived_documents: number;
}

export default function DocumentationPage() {
  const [activeTab, setActiveTab] = useState<'documents' | 'create' | 'templates' | 'settings'>('documents');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showViewModal, setShowViewModal] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [documentData, setDocumentData] = useState({
    doc_id: '',
    title: '',
    doc_type: 'api',
    content: '',
    author: '',
    version: '1.0',
  });

  const queryClient = useQueryClient();

  // 🔧 获取文档状态
  const { data: statusData, isLoading: statusLoading, refetch: refetchStatus } = useQuery<{ data: DocumentationStatus; timestamp: string }>({
    queryKey: ['documentation-status'],
    queryFn: async () => {
      const resp = await api.get('/api/documentation/status');
      return resp.data;
    },
    refetchInterval: 120000, // 2分钟刷新
  });

  // 🔧 获取文档列表
  const { data: documentsData, isLoading: documentsLoading, refetch: refetchDocuments } = useQuery<{ data: { documents: Document[]; count: number }; timestamp: string }>({
    queryKey: ['documentation-documents'],
    queryFn: async () => {
      const resp = await api.get('/api/documentation/documents');
      return resp.data;
    },
    refetchInterval: 120000, // 2分钟刷新
  });

  // 🔧 创建文档
  const createDocumentMutation = useMutation({
    mutationFn: async (data: typeof documentData) => {
      const resp = await api.post('/api/documentation/document/create', data);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documentation-status'] });
      queryClient.invalidateQueries({ queryKey: ['documentation-documents'] });
      setShowCreateModal(false);
      showSuccess('文档创建成功');
    },
    onError: () => {
      showError('文档创建失败');
    },
  });

  // 🔧 更新文档
  const updateDocumentMutation = useMutation({
    mutationFn: async ({ docId, content, status }: { docId: string; content?: string; status?: string }) => {
      const resp = await api.post(`/api/documentation/document/${docId}/update`, { content, status });
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documentation-documents'] });
      showSuccess('文档更新成功');
    },
    onError: () => {
      showError('文档更新失败');
    },
  });

  // 🔧 获取文档详情
  const { data: documentDetailData, isLoading: documentDetailLoading, refetch: refetchDocumentDetail } = useQuery<{ data: Document; timestamp: string }>({
    queryKey: ['document-detail', selectedDocument?.doc_id],
    queryFn: async () => {
      if (!selectedDocument) throw new Error('No document selected');
      const resp = await api.get(`/api/documentation/document/${selectedDocument.doc_id}`);
      return resp.data;
    },
    enabled: !!selectedDocument,
  });

  // 🔧 P1 Integration: Use enhanced loading state
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(
    statusLoading || documentsLoading
  );

  // 🔧 P1 Integration: Use toast notifications
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // 🔧 P1 Integration: Handle errors with toast
  useEffect(() => {
    if (pageError) {
      showError('Failed to load documentation data');
      setPageError(pageError as Error);
    }
  }, [pageError, showError, setPageError]);

  const status = statusData?.data || { total_documents: 0, published_documents: 0, draft_documents: 0, archived_documents: 0 };
  const documents = documentsData?.data?.documents || [];

  const handleCreateDocument = () => {
    createDocumentMutation.mutate(documentData);
  };

  const handleViewDocument = (document: Document) => {
    setSelectedDocument(document);
    setShowViewModal(true);
  };

  const handlePublishDocument = (docId: string) => {
    updateDocumentMutation.mutate({ docId, status: 'published' });
  };

  const handleRefresh = () => {
    refetchStatus();
    refetchDocuments();
  };

  // 🔧 P1 Integration: Use enhanced loading and empty states
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
          action={<Button onClick={handleRefresh}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
          action={<Button onClick={handleRefresh}>重试</Button>}
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
            <h1 className="text-3xl font-bold text-gray-900">文档管理</h1>
            <p className="text-sm text-gray-500">创建、管理和发布文档</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={handleRefresh} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
          <Button onClick={() => setShowCreateModal(true)}>
            <Plus className="h-4 w-4 mr-2" />
            创建文档
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总文档数</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-blue-600">{status.total_documents}</p>
            <p className="text-sm text-gray-500 mt-1">文档总数</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">已发布</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-600">{status.published_documents}</p>
            <p className="text-sm text-gray-500 mt-1">已发布文档</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">草稿</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-orange-600">{status.draft_documents}</p>
            <p className="text-sm text-gray-500 mt-1">草稿文档</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">已归档</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-purple-600">{status.archived_documents}</p>
            <p className="text-sm text-gray-500 mt-1">归档文档</p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b">
        <Button
          variant={activeTab === 'documents' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('documents')}
        >
          <FileText className="h-4 w-4 mr-2" />
          文档列表
        </Button>
        <Button
          variant={activeTab === 'create' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('create')}
        >
          <Plus className="h-4 w-4 mr-2" />
          创建文档
        </Button>
        <Button
          variant={activeTab === 'templates' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('templates')}
        >
          <BookOpen className="h-4 w-4 mr-2" />
          模板库
        </Button>
        <Button
          variant={activeTab === 'settings' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('settings')}
        >
          <Settings className="h-4 w-4 mr-2" />
          设置
        </Button>
      </div>

      {/* Documents Tab */}
      {activeTab === 'documents' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              文档列表
            </CardTitle>
          </CardHeader>
          <CardContent>
            {documents.length > 0 ? (
              <div className="space-y-4">
                {documents.map((doc) => (
                  <div key={doc.doc_id} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <div>
                        <h3 className="font-semibold text-lg">{doc.title}</h3>
                        <p className="text-sm text-gray-500">v{doc.version} by {doc.author}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <StatusBadge status={doc.status as "error" | "success" | "warning" | "info" | "pending" | "unknown"} />
                        <span className="text-xs text-gray-500">{doc.doc_type}</span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="text-xs text-gray-500">
                        最后更新: {new Date(doc.last_updated).toLocaleString()}
                      </div>
                      <div className="flex gap-2">
                        <Button size="sm" variant="outline" onClick={() => handleViewDocument(doc)}>
                          <Eye className="h-4 w-4 mr-1" />
                          查看
                        </Button>
                        {doc.status === 'draft' && (
                          <Button size="sm" onClick={() => handlePublishDocument(doc.doc_id)}>
                            发布
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="暂无文档"
                description="文档库暂无文档"
                action={<Button onClick={() => setShowCreateModal(true)}>创建第一个文档</Button>}
              />
            )}
          </CardContent>
        </Card>
      )}

      {/* Create Tab */}
      {activeTab === 'create' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Plus className="h-5 w-5" />
              创建文档
            </CardTitle>
          </CardHeader>
          <CardContent>
            <EmptyState
              title="创建文档"
              description="创建新的文档内容"
              action={<Button onClick={() => setShowCreateModal(true)}>开始创建</Button>}
            />
          </CardContent>
        </Card>
      )}

      {/* Templates Tab */}
      {activeTab === 'templates' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BookOpen className="h-5 w-5" />
              模板库
            </CardTitle>
          </CardHeader>
          <CardContent>
            <EmptyState
              title="文档模板"
              description="使用模板快速创建文档"
            />
          </CardContent>
        </Card>
      )}

      {/* Settings Tab */}
      {activeTab === 'settings' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5" />
              文档设置
            </CardTitle>
          </CardHeader>
          <CardContent>
            <EmptyState
              title="文档设置"
              description="配置文档管理选项"
            />
          </CardContent>
        </Card>
      )}

      {/* Create Document Modal */}
      <EnhancedModal
        open={showCreateModal}
        onOpenChange={setShowCreateModal}
        title="创建文档"
        size="lg"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">文档ID</label>
            <input
              type="text"
              value={documentData.doc_id}
              onChange={(e) => setDocumentData({ ...documentData, doc_id: e.target.value })}
              placeholder="输入唯一文档ID"
              className="w-full px-3 py-2 border rounded-md bg-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">标题</label>
            <input
              type="text"
              value={documentData.title}
              onChange={(e) => setDocumentData({ ...documentData, title: e.target.value })}
              placeholder="输入文档标题"
              className="w-full px-3 py-2 border rounded-md bg-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">文档类型</label>
            <select
              value={documentData.doc_type}
              onChange={(e) => setDocumentData({ ...documentData, doc_type: e.target.value })}
              className="w-full px-3 py-2 border rounded-md bg-white"
            >
              <option value="api">API文档</option>
              <option value="user_guide">用户指南</option>
              <option value="developer_guide">开发者指南</option>
              <option value="architecture">架构文档</option>
              <option value="deployment">部署文档</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">作者</label>
            <input
              type="text"
              value={documentData.author}
              onChange={(e) => setDocumentData({ ...documentData, author: e.target.value })}
              placeholder="输入作者名称"
              className="w-full px-3 py-2 border rounded-md bg-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">版本</label>
            <input
              type="text"
              value={documentData.version}
              onChange={(e) => setDocumentData({ ...documentData, version: e.target.value })}
              placeholder="输入版本号 (如 1.0)"
              className="w-full px-3 py-2 border rounded-md bg-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">内容</label>
            <textarea
              value={documentData.content}
              onChange={(e) => setDocumentData({ ...documentData, content: e.target.value })}
              placeholder="输入文档内容"
              className="w-full px-3 py-2 border rounded-md bg-white min-h-[200px]"
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowCreateModal(false)}>
              取消
            </Button>
            <Button onClick={handleCreateDocument} disabled={createDocumentMutation.isPending}>
              {createDocumentMutation.isPending ? '创建中...' : '创建'}
            </Button>
          </div>
        </div>
      </EnhancedModal>

      {/* View Document Modal */}
      <EnhancedModal
        open={showViewModal}
        onOpenChange={setShowViewModal}
        title="查看文档"
        size="lg"
      >
        <div className="space-y-4">
          {documentDetailLoading ? (
            <div className="flex items-center justify-center">
              <LoadingSpinner size="md" />
            </div>
          ) : (
            <>
              <div>
                <h3 className="text-lg font-semibold">{documentDetailData?.data?.title}</h3>
                <p className="text-sm text-gray-500">v{documentDetailData?.data?.version} by {documentDetailData?.data?.author}</p>
              </div>
              <div className="border rounded-lg p-4 bg-gray-50">
                <pre className="whitespace-pre-wrap text-sm">{documentDetailData?.data?.content}</pre>
              </div>
            </>
          )}
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowViewModal(false)}>
              关闭
            </Button>
          </div>
        </div>
      </EnhancedModal>
    </div>
  );
}