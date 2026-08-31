'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface Language {
  id: string;
  code: string;
  name: string;
  native_name: string;
  enabled: boolean;
  is_default: boolean;
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

interface Resource {
  id: string;
  language_code: string;
  namespace: string;
  key: string;
  value: string;
  context: string | null;
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

interface Translation {
  id: string;
  source_language: string;
  target_language: string;
  namespace: string;
  key: string;
  source_value: string;
  target_value: string;
  status: string;
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

interface Adapter {
  id: string;
  name: string;
  type: string;
  config: Record<string, any>;
  enabled: boolean;
  priority: number;
  created_at: string;
  updated_at: string;
}

export default function LocalizationAdvancedPage() {
  const [activeTab, setActiveTab] = useState<string>('languages');
  const [languages, setLanguages] = useState<Language[]>([]);
  const [resources, setResources] = useState<Resource[]>([]);
  const [translations, setTranslations] = useState<Translation[]>([]);
  const [adapters, setAdapters] = useState<Adapter[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newLanguage, setNewLanguage] = useState({
    code: '',
    name: '',
    native_name: '',
    enabled: true,
    is_default: false,
    metadata: {}
  });
  const [newResource, setNewResource] = useState({
    language_code: '',
    namespace: '',
    key: '',
    value: '',
    context: '',
    metadata: {}
  });

  useEffect(() => {
    fetchData();
  }, [activeTab]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      if (activeTab === 'languages') {
        const response = await api.get('/api/v1/localization/languages');
        setLanguages(response.data || []);
      } else if (activeTab === 'resources') {
        const response = await api.get('/api/v1/localization/resources');
        setResources(response.data || []);
      } else if (activeTab === 'translations') {
        const response = await api.get('/api/v1/localization/translations');
        setTranslations(response.data || []);
      } else if (activeTab === 'adapters') {
        const response = await api.get('/api/v1/localization/adapters');
        setAdapters(response.data || []);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateLanguage = async () => {
    try {
      setError(null);
      await api.post('/api/v1/localization/languages', newLanguage);
      setShowCreateForm(false);
      setNewLanguage({
        code: '',
        name: '',
        native_name: '',
        enabled: true,
        is_default: false,
        metadata: {}
      });
      await fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '创建语言失败');
    }
  };

  const handleCreateResource = async () => {
    try {
      setError(null);
      await api.post('/api/v1/localization/resources', newResource);
      setShowCreateForm(false);
      setNewResource({
        language_code: '',
        namespace: '',
        key: '',
        value: '',
        context: '',
        metadata: {}
      });
      await fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '创建资源失败');
    }
  };

  const handleToggleLanguage = async (languageId: string, enabled: boolean) => {
    try {
      setError(null);
      await api.patch(`/api/v1/localization/languages/${languageId}`, { enabled: !enabled });
      await fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '更新语言失败');
    }
  };

  const handleDeleteLanguage = async (languageId: string) => {
    if (!confirm('确定要删除此语言吗？')) return;

    try {
      setError(null);
      await api.delete(`/api/v1/localization/languages/${languageId}`);
      await fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '删除语言失败');
    }
  };

  const handleDeleteResource = async (resourceId: string) => {
    if (!confirm('确定要删除此资源吗？')) return;

    try {
      setError(null);
      await api.delete(`/api/v1/localization/resources/${resourceId}`);
      await fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '删除资源失败');
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
        <h1 className="text-3xl font-bold text-gray-900">高级本地化管理</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="text-red-800">{error}</div>
          <Button onClick={() => setError(null)} className="mt-2" variant="outline">关闭</Button>
        </div>
      )}

      {/* 标签页 */}
      <div className="flex border-b">
        {[
          { id: 'languages', name: '语言' },
          { id: 'resources', name: '资源' },
          { id: 'translations', name: '翻译' },
          { id: 'adapters', name: '适配器' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 border-b-2 transition-colors ${
              activeTab === tab.id
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab.name}
          </button>
        ))}
      </div>

      {/* 创建语言表单 */}
      {showCreateForm && activeTab === 'languages' && (
        <Card>
          <CardHeader>
            <CardTitle>创建新语言</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">语言代码</label>
                <input
                  type="text"
                  value={newLanguage.code}
                  onChange={(e) => setNewLanguage({ ...newLanguage, code: e.target.value })}
                  className="w-full border rounded-md p-2"
                  placeholder="例如: zh-CN, en-US"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">语言名称</label>
                <input
                  type="text"
                  value={newLanguage.name}
                  onChange={(e) => setNewLanguage({ ...newLanguage, name: e.target.value })}
                  className="w-full border rounded-md p-2"
                  placeholder="例如: Chinese (Simplified)"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">本地名称</label>
                <input
                  type="text"
                  value={newLanguage.native_name}
                  onChange={(e) => setNewLanguage({ ...newLanguage, native_name: e.target.value })}
                  className="w-full border rounded-md p-2"
                  placeholder="例如: 简体中文"
                />
              </div>
              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={newLanguage.enabled}
                    onChange={(e) => setNewLanguage({ ...newLanguage, enabled: e.target.checked })}
                  />
                  <span className="text-sm text-gray-700">启用</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={newLanguage.is_default}
                    onChange={(e) => setNewLanguage({ ...newLanguage, is_default: e.target.checked })}
                  />
                  <span className="text-sm text-gray-700">设为默认</span>
                </label>
              </div>
              <div className="flex gap-2">
                <Button onClick={handleCreateLanguage} className="flex-1">创建语言</Button>
                <Button onClick={() => setShowCreateForm(false)} variant="outline">取消</Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 创建资源表单 */}
      {showCreateForm && activeTab === 'resources' && (
        <Card>
          <CardHeader>
            <CardTitle>创建新资源</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">语言代码</label>
                <input
                  type="text"
                  value={newResource.language_code}
                  onChange={(e) => setNewResource({ ...newResource, language_code: e.target.value })}
                  className="w-full border rounded-md p-2"
                  placeholder="例如: zh-CN"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">命名空间</label>
                <input
                  type="text"
                  value={newResource.namespace}
                  onChange={(e) => setNewResource({ ...newResource, namespace: e.target.value })}
                  className="w-full border rounded-md p-2"
                  placeholder="例如: common, errors"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">键</label>
                <input
                  type="text"
                  value={newResource.key}
                  onChange={(e) => setNewResource({ ...newResource, key: e.target.value })}
                  className="w-full border rounded-md p-2"
                  placeholder="例如: welcome_message"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">值</label>
                <textarea
                  value={newResource.value}
                  onChange={(e) => setNewResource({ ...newResource, value: e.target.value })}
                  className="w-full border rounded-md p-2 h-24"
                  placeholder="翻译文本"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">上下文</label>
                <input
                  type="text"
                  value={newResource.context}
                  onChange={(e) => setNewResource({ ...newResource, context: e.target.value })}
                  className="w-full border rounded-md p-2"
                  placeholder="翻译上下文（可选）"
                />
              </div>
              <div className="flex gap-2">
                <Button onClick={handleCreateResource} className="flex-1">创建资源</Button>
                <Button onClick={() => setShowCreateForm(false)} variant="outline">取消</Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 语言列表 */}
      {activeTab === 'languages' && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>语言 ({languages.length})</CardTitle>
              <Button onClick={() => setShowCreateForm(!showCreateForm)}>
                {showCreateForm ? '取消' : '创建语言'}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {languages.length === 0 ? (
              <div className="text-gray-500 text-center py-8">暂无语言</div>
            ) : (
              <div className="space-y-3">
                {languages.map((language) => (
                  <div key={language.id} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <div>
                        <h3 className="font-semibold">{language.name}</h3>
                        <div className="text-sm text-gray-500">{language.native_name}</div>
                      </div>
                      <div className="flex gap-2">
                        {language.is_default && <Badge variant="default">默认</Badge>}
                        <Badge variant={language.enabled ? 'default' : 'secondary'}>
                          {language.enabled ? '已启用' : '已禁用'}
                        </Badge>
                      </div>
                    </div>
                    <div className="text-sm text-gray-600 mb-2">代码: {language.code}</div>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleToggleLanguage(language.id, language.enabled)}
                      >
                        {language.enabled ? '禁用' : '启用'}
                      </Button>
                      {!language.is_default && (
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => handleDeleteLanguage(language.id)}
                        >
                          删除
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 资源列表 */}
      {activeTab === 'resources' && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>资源 ({resources.length})</CardTitle>
              <Button onClick={() => setShowCreateForm(!showCreateForm)}>
                {showCreateForm ? '取消' : '创建资源'}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {resources.length === 0 ? (
              <div className="text-gray-500 text-center py-8">暂无资源</div>
            ) : (
              <div className="space-y-3">
                {resources.map((resource) => (
                  <div key={resource.id} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="font-semibold">{resource.key}</h3>
                      <Badge variant="outline">{resource.language_code}</Badge>
                    </div>
                    <div className="text-sm text-gray-600 mb-2">
                      命名空间: {resource.namespace}
                      {resource.context && ` | 上下文: ${resource.context}`}
                    </div>
                    <div className="text-sm text-gray-700 mb-2">{resource.value}</div>
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => handleDeleteResource(resource.id)}
                    >
                      删除
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 翻译列表 */}
      {activeTab === 'translations' && (
        <Card>
          <CardHeader>
            <CardTitle>翻译 ({translations.length})</CardTitle>
          </CardHeader>
          <CardContent>
            {translations.length === 0 ? (
              <div className="text-gray-500 text-center py-8">暂无翻译</div>
            ) : (
              <div className="space-y-3">
                {translations.map((translation) => (
                  <div key={translation.id} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="font-semibold">{translation.key}</h3>
                      <Badge variant={translation.status === 'published' ? 'default' : 'secondary'}>
                        {translation.status}
                      </Badge>
                    </div>
                    <div className="grid grid-cols-2 gap-4 text-sm mb-2">
                      <div>
                        <div className="text-gray-500">源语言: {translation.source_language}</div>
                        <div className="text-gray-700">{translation.source_value}</div>
                      </div>
                      <div>
                        <div className="text-gray-500">目标语言: {translation.target_language}</div>
                        <div className="text-gray-700">{translation.target_value}</div>
                      </div>
                    </div>
                    <div className="text-xs text-gray-500">
                      命名空间: {translation.namespace}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 适配器列表 */}
      {activeTab === 'adapters' && (
        <Card>
          <CardHeader>
            <CardTitle>适配器 ({adapters.length})</CardTitle>
          </CardHeader>
          <CardContent>
            {adapters.length === 0 ? (
              <div className="text-gray-500 text-center py-8">暂无适配器</div>
            ) : (
              <div className="space-y-3">
                {adapters.map((adapter) => (
                  <div key={adapter.id} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="font-semibold">{adapter.name}</h3>
                      <div className="flex gap-2">
                        <Badge variant={adapter.enabled ? 'default' : 'secondary'}>
                          {adapter.enabled ? '已启用' : '已禁用'}
                        </Badge>
                        <Badge variant="outline">优先级: {adapter.priority}</Badge>
                      </div>
                    </div>
                    <div className="text-sm text-gray-600 mb-2">类型: {adapter.type}</div>
                    <div className="text-xs text-gray-500">
                      配置: {JSON.stringify(adapter.config)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
