'use client'

import { useState } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';

interface Runbook {
  id: string;
  title: string;
  category: string;
  description: string;
  tags: string[];
  author: string;
  lastUpdated: Date;
  content: string;
}

interface SearchResult {
  runbook: Runbook;
  relevance: number;
  matchedTags: string[];
}

interface RAGItem {
  score: number;
  payload: Record<string, any>;
}

function payloadToRunbook(payload: any, fallbackId: string): Runbook {
  const raw = payload || {};
  const tags = Array.isArray(raw.tags)
    ? raw.tags.map(String)
    : raw.tags
      ? [String(raw.tags)]
      : [];
  return {
    id: raw.id ? String(raw.id) : fallbackId,
    title: raw.title
      ? String(raw.title)
      : raw.name
        ? String(raw.name)
        : fallbackId,
    category: raw.category ? String(raw.category) : '未分类',
    description: raw.description
      ? String(raw.description)
      : raw.summary
        ? String(raw.summary)
        : '',
    tags,
    author: raw.author ? String(raw.author) : 'RAG',
    lastUpdated: new Date(raw.lastUpdated || raw.updated_at || raw.timestamp || Date.now()),
    content: raw.content
      ? String(raw.content)
      : JSON.stringify(raw, null, 2),
  };
}

export default function KnowledgeBasePage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedRunbook, setSelectedRunbook] = useState<Runbook | null>(null);
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [runbooks, setRunbooks] = useState<Runbook[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  const categories = ['all', '故障处理', '运维操作', '告警处理', '配置管理', '日志分析'];

  const handleSearch = async () => {
    const q = searchQuery.trim();
    if (!q) {
      setSearchResults([]);
      setRunbooks([]);
      return;
    }

    setIsSearching(true);
    try {
      const { data } = await api.post<RAGItem[]>('/api/v1/rag/search', {
        query: q,
        top_k: 5,
      });
      const items = Array.isArray(data) ? data : [];
      const mapped: SearchResult[] = items.map((item, index) => {
        const runbook = payloadToRunbook(item.payload, `rag-${index}`);
        const matchedTags = Array.isArray(item.payload?.matched_tags)
          ? item.payload.matched_tags.map(String)
          : runbook.tags;
        return {
          runbook,
          relevance: Number(item.score) || 0,
          matchedTags,
        };
      });
      setSearchResults(mapped);
      setRunbooks(mapped.map((result) => result.runbook));
    } catch (err) {
      setSearchResults([]);
      setRunbooks([]);
    } finally {
      setIsSearching(false);
    }
  };

  const handleAIRecommend = () => {
    const recommended = runbooks.slice(0, 3).map((runbook) => ({
      runbook,
      relevance: Math.floor(Math.random() * 3) + 2,
      matchedTags: runbook.tags.slice(0, 2),
    }));
    setSearchResults(recommended);
  };

  const filteredRunbooks =
    selectedCategory === 'all'
      ? runbooks
      : runbooks.filter((r) => r.category === selectedCategory);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">知识库</h1>
        <Button>创建Runbook</Button>
      </div>

      {/* 搜索和AI推荐 */}
      <Card>
        <CardHeader>
          <CardTitle>搜索文档</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2 mb-4">
            <Input
              placeholder="搜索Runbook、标签或内容..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            />
            <Button onClick={handleSearch} disabled={isSearching}>
              {isSearching ? '搜索中...' : '搜索'}
            </Button>
            <Button variant="outline" onClick={handleAIRecommend}>
              AI推荐
            </Button>
          </div>

          {/* 搜索结果 */}
          {searchResults.length > 0 && (
            <div className="space-y-3">
              <h4 className="font-medium">搜索结果</h4>
              {searchResults.map((result) => (
                <div
                  key={result.runbook.id}
                  className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition cursor-pointer"
                  onClick={() => setSelectedRunbook(result.runbook)}
                >
                  <div className="flex items-start justify-between mb-2">
                    <h4 className="font-medium">{result.runbook.title}</h4>
                    <Badge variant="outline">相关度: {result.relevance}</Badge>
                  </div>
                  <p className="text-sm text-gray-600 mb-2">{result.runbook.description}</p>
                  <div className="flex gap-1">
                    {result.matchedTags.map((tag) => (
                      <Badge key={tag} variant="secondary" className="text-xs">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Runbook列表 */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>分类浏览</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 mb-4">
              {categories.map((category) => (
                <Button
                  key={category}
                  variant={selectedCategory === category ? 'default' : 'outline'}
                  size="sm"
                  className="w-full justify-start"
                  onClick={() => setSelectedCategory(category)}
                >
                  {category === 'all' ? '全部' : category}
                </Button>
              ))}
            </div>
            <div className="space-y-3">
              {filteredRunbooks.map((runbook) => (
                <div
                  key={runbook.id}
                  className={`p-3 border rounded-lg cursor-pointer hover:bg-gray-50 transition ${selectedRunbook?.id === runbook.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                    }`}
                  onClick={() => setSelectedRunbook(runbook)}
                >
                  <h4 className="font-medium text-sm mb-1">{runbook.title}</h4>
                  <p className="text-xs text-gray-500 mb-2">{runbook.description}</p>
                  <div className="flex flex-wrap gap-1">
                    {runbook.tags.slice(0, 2).map((tag) => (
                      <Badge key={tag} variant="outline" className="text-xs">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Runbook详情 */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>
                {selectedRunbook ? selectedRunbook.title : '选择Runbook查看详情'}
              </CardTitle>
              {selectedRunbook && (
                <div className="flex gap-2">
                  <Button variant="outline" size="sm">
                    编辑
                  </Button>
                  <Button variant="outline" size="sm">
                    导出
                  </Button>
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {!selectedRunbook ? (
              <div className="h-96 flex items-center justify-center text-gray-400">
                请选择一个Runbook查看详情
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">分类</label>
                  <Badge variant="outline">{selectedRunbook.category}</Badge>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
                  <p className="text-sm">{selectedRunbook.description}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">标签</label>
                  <div className="flex flex-wrap gap-1">
                    {selectedRunbook.tags.map((tag) => (
                      <Badge key={tag} variant="secondary">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">作者</label>
                    <p className="text-sm">{selectedRunbook.author}</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">最后更新</label>
                    <p className="text-sm">{selectedRunbook.lastUpdated.toLocaleString()}</p>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">内容</label>
                  <div className="bg-gray-50 rounded p-4">
                    <pre className="text-sm whitespace-pre-wrap">{selectedRunbook.content}</pre>
                  </div>
                </div>
                <div className="flex gap-2 pt-4 border-t">
                  <Button variant="outline" size="sm">
                    添加标签
                  </Button>
                  <Button variant="outline" size="sm">
                    分享
                  </Button>
                  <Button variant="outline" size="sm" className="text-red-600">
                    删除
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* AI推荐说明 */}
      <Card>
        <CardHeader>
          <CardTitle>AI智能推荐</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">基于上下文推荐</h4>
              <p className="text-sm text-gray-600">
                根据当前告警、日志或操作上下文，智能推荐相关的Runbook文档
              </p>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">基于历史推荐</h4>
              <p className="text-sm text-gray-600">
                根据用户历史查看记录，推荐可能感兴趣的文档
              </p>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">基于相似度推荐</h4>
              <p className="text-sm text-gray-600">
                基于文档标签和内容的相似度，推荐相关文档
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
