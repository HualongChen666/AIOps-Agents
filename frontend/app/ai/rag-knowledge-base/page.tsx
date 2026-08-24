'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import api from '@/lib/api';

interface KnowledgeBase {
  id: string;
  name: string;
  description: string;
  document_count: number;
  embedding_model: string;
  created_at: string;
  updated_at: string;
  status: 'active' | 'indexing' | 'error';
}

interface Document {
  id: string;
  title: string;
  content_preview: string;
  source: string;
  uploaded_at: string;
  status: 'indexed' | 'processing' | 'failed';
}

export default function RAGKnowledgeBasePage() {
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedKB, setSelectedKB] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newKB, setNewKB] = useState({ name: '', description: '', embedding_model: 'text-embedding-ada-002' });

  useEffect(() => {
    fetchKnowledgeBases();
  }, []);

  useEffect(() => {
    if (selectedKB) {
      fetchDocuments(selectedKB);
    }
  }, [selectedKB]);

  const fetchKnowledgeBases = async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/ai/rag-knowledge-base/bases');
      setKnowledgeBases(res.data.bases || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载知识库失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchDocuments = async (kbId: string) => {
    try {
      const res = await api.get(`/api/ai/rag-knowledge-base/bases/${kbId}/documents`);
      setDocuments(res.data.documents || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载文档失败');
    }
  };

  const handleCreateKB = async () => {
    try {
      await api.post('/api/ai/rag-knowledge-base/bases', newKB);
      setNewKB({ name: '', description: '', embedding_model: 'text-embedding-ada-002' });
      fetchKnowledgeBases();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '创建知识库失败');
    }
  };

  const handleUploadDocument = async (file: File) => {
    if (!selectedKB) return;
    try {
      const formData = new FormData();
      formData.append('file', file);
      await api.post(`/api/ai/rag-knowledge-base/bases/${selectedKB}/documents`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      fetchDocuments(selectedKB);
      fetchKnowledgeBases();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '上传文档失败');
    }
  };

  const handleDeleteDocument = async (docId: string) => {
    if (!selectedKB) return;
    try {
      await api.delete(`/api/ai/rag-knowledge-base/bases/${selectedKB}/documents/${docId}`);
      fetchDocuments(selectedKB);
      fetchKnowledgeBases();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '删除文档失败');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="text-red-800">{error}</div>
        <Button onClick={fetchKnowledgeBases} className="mt-2">重试</Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">RAG知识库</h1>
        <Button onClick={fetchKnowledgeBases}>刷新</Button>
      </div>

      {/* 知识库列表 */}
      <Card>
        <CardHeader>
          <CardTitle>知识库列表</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {knowledgeBases.map((kb) => (
              <div
                key={kb.id}
                className={`border rounded-lg p-4 cursor-pointer transition-colors ${
                  selectedKB === kb.id ? 'border-blue-500 bg-blue-50' : ''
                }`}
                onClick={() => setSelectedKB(kb.id)}
              >
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold">{kb.name}</h3>
                  <Badge variant={kb.status === 'active' ? 'default' : 'secondary'}>
                    {kb.status}
                  </Badge>
                </div>
                <div className="text-sm text-gray-600 mb-2">{kb.description}</div>
                <div className="text-sm text-gray-600">文档数: {kb.document_count}</div>
                <div className="text-sm text-gray-600">嵌入模型: {kb.embedding_model}</div>
                <div className="text-xs text-gray-500 mt-2">
                  更新于: {new Date(kb.updated_at).toLocaleString()}
                </div>
              </div>
            ))}
          </div>

          {/* 创建新知识库 */}
          <div className="mt-6 pt-6 border-t">
            <h3 className="font-semibold mb-4">创建新知识库</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input
                placeholder="知识库名称"
                value={newKB.name}
                onChange={(e) => setNewKB({ ...newKB, name: e.target.value })}
              />
              <Input
                placeholder="嵌入模型"
                value={newKB.embedding_model}
                onChange={(e) => setNewKB({ ...newKB, embedding_model: e.target.value })}
              />
              <Input
                placeholder="描述"
                value={newKB.description}
                onChange={(e) => setNewKB({ ...newKB, description: e.target.value })}
                className="md:col-span-2"
              />
            </div>
            <Button onClick={handleCreateKB} className="mt-4">创建知识库</Button>
          </div>
        </CardContent>
      </Card>

      {/* 文档列表 */}
      {selectedKB && (
        <Card>
          <CardHeader>
            <CardTitle>文档列表</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="mb-4">
              <input
                type="file"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleUploadDocument(file);
                }}
                className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
              />
            </div>
            <div className="space-y-2">
              {documents.map((doc) => (
                <div key={doc.id} className="border rounded-lg p-4 flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="font-semibold">{doc.title}</h4>
                      <Badge variant={doc.status === 'indexed' ? 'default' : 'secondary'}>
                        {doc.status}
                      </Badge>
                    </div>
                    <div className="text-sm text-gray-600">{doc.content_preview}</div>
                    <div className="text-xs text-gray-500 mt-1">
                      来源: {doc.source} | 上传于: {new Date(doc.uploaded_at).toLocaleString()}
                    </div>
                  </div>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => handleDeleteDocument(doc.id)}
                  >
                    删除
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
