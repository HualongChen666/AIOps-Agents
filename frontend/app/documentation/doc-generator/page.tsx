'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface GeneratorStatus {
  available: boolean;
  total_templates: number;
}

interface Template {
  name: string;
  description?: string;
}

interface GeneratedDocument {
  doc_id: string;
  title: string;
  generator_type: string;
  generated_at: string;
  content?: string;
}

export default function DocGeneratorPage() {
  const [status, setStatus] = useState<GeneratorStatus | null>(null);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [documents, setDocuments] = useState<GeneratedDocument[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');
  const [docTitle, setDocTitle] = useState<string>('');
  const [contentVars, setContentVars] = useState<string>('{}');
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [statusRes, templatesRes, documentsRes] = await Promise.all([
        api.get('/api/doc-generator/status'),
        api.get('/api/doc-generator/templates'),
        api.get('/api/doc-generator/documents')
      ]);
      setStatus(statusRes.data.data);
      setTemplates(templatesRes.data.data.templates || []);
      setDocuments(documentsRes.data.data.documents || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateDocument = async () => {
    if (!selectedTemplate || !docTitle) {
      setError('请选择模板并输入文档标题');
      return;
    }

    try {
      setGenerating(true);
      setError(null);
      const vars = JSON.parse(contentVars);
      const response = await api.post('/api/doc-generator/document/generate', {
        doc_id: `doc-${Date.now()}`,
        title: docTitle,
        template_name: selectedTemplate,
        content_vars: vars,
        generator_type: 'markdown'
      });
      await fetchData();
      setDocTitle('');
      setContentVars('{}');
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '生成文档失败');
    } finally {
      setGenerating(false);
    }
  };

  const handleViewDocument = async (docId: string) => {
    try {
      const response = await api.get(`/api/doc-generator/document/${docId}`);
      const doc = response.data.data;
      alert(`文档内容:\n\n${doc.content || '无内容'}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '获取文档失败');
    }
  };

  const handleSaveDocument = async (docId: string) => {
    try {
      const outputPath = prompt('请输入保存路径:', `/docs/${docId}.md`);
      if (outputPath) {
        await api.post(`/api/doc-generator/document/${docId}/save`, { output_path: outputPath });
        alert('文档保存成功');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '保存文档失败');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">文档生成器</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="text-red-800">{error}</div>
          <Button onClick={() => setError(null)} className="mt-2" variant="outline">关闭</Button>
        </div>
      )}

      {/* 生成器状态 */}
      <Card>
        <CardHeader>
          <CardTitle>生成器状态</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-sm text-gray-500">可用状态</div>
              <Badge variant={status?.available ? 'default' : 'destructive'}>
                {status?.available ? '可用' : '不可用'}
              </Badge>
            </div>
            <div>
              <div className="text-sm text-gray-500">模板总数</div>
              <div className="text-2xl font-semibold">{status?.total_templates || 0}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 生成文档 */}
      <Card>
        <CardHeader>
          <CardTitle>生成新文档</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">选择模板</label>
              <select
                value={selectedTemplate}
                onChange={(e) => setSelectedTemplate(e.target.value)}
                className="w-full border rounded-md p-2"
              >
                <option value="">请选择模板</option>
                {templates.map((template, index) => (
                  <option key={index} value={template.name}>{template.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">文档标题</label>
              <input
                type="text"
                value={docTitle}
                onChange={(e) => setDocTitle(e.target.value)}
                className="w-full border rounded-md p-2"
                placeholder="输入文档标题"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">内容变量 (JSON)</label>
              <textarea
                value={contentVars}
                onChange={(e) => setContentVars(e.target.value)}
                className="w-full border rounded-md p-2 h-32 font-mono text-sm"
                placeholder='{"key": "value"}'
              />
            </div>
            <Button
              onClick={handleGenerateDocument}
              disabled={generating}
              className="w-full"
            >
              {generating ? '生成中...' : '生成文档'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 已生成文档列表 */}
      <Card>
        <CardHeader>
          <CardTitle>已生成文档 ({documents.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {documents.length === 0 ? (
            <div className="text-gray-500 text-center py-8">暂无生成的文档</div>
          ) : (
            <div className="space-y-3">
              {documents.map((doc) => (
                <div key={doc.doc_id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold">{doc.title}</h3>
                    <Badge variant="outline">{doc.generator_type}</Badge>
                  </div>
                  <div className="text-sm text-gray-600 mb-3">
                    ID: {doc.doc_id} | 生成时间: {new Date(doc.generated_at).toLocaleString()}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleViewDocument(doc.doc_id)}
                    >
                      查看内容
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleSaveDocument(doc.doc_id)}
                    >
                      保存文档
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
