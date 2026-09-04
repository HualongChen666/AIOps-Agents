'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface RAGSearchResult {
  query: string;
  results: any[];
  timestamp: string;
  metadata?: Record<string, any>;
}

interface RAGHistoryRecord {
  id: string;
  query: string;
  results: any[];
  timestamp: string;
  similarity_score?: number;
  source?: string;
}

export default function RAGHistoryPage() {
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [searchResults, setSearchResults] = useState<RAGSearchResult | null>(null);
  const [history, setHistory] = useState<RAGHistoryRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Load history from API
    const loadHistory = async () => {
      try {
        setLoading(true);
        const response = await api.get('/api/rag/history');
        setHistory(response.data.history || []);
      } catch (err: any) {
        console.error('Failed to load RAG history:', err);
        // If API fails, initialize empty history
        setHistory([]);
      } finally {
        setLoading(false);
      }
    };

    loadHistory();
  }, []);

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setError('请输入搜索查询');
      return;
    }

    try {
      setSearching(true);
      setError(null);

      // Call RAG search API
      const response = await api.post('/api/rag/search', {
        query: searchQuery,
        top_k: 5
      });

      setSearchResults({
        query: searchQuery,
        results: response.data.results || [],
        timestamp: new Date().toISOString(),
        metadata: response.data.metadata
      });

      // Add to history
      const newRecord: RAGHistoryRecord = {
        id: Date.now().toString(),
        query: searchQuery,
        results: response.data.results || [],
        timestamp: new Date().toISOString()
      };
      setHistory(prev => [newRecord, ...prev].slice(0, 20)); // Keep last 20 records
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '搜索失败');
    } finally {
      setSearching(false);
    }
  };

  const handleHistorySearch = async (query: string) => {
    setSearchQuery(query);
    await handleSearch();
  };

  const handleClearHistory = async () => {
    if (confirm('确定要清空搜索历史吗？')) {
      try {
        await api.delete('/api/rag/history');
        setHistory([]);
      } catch (err: any) {
        setError('清空历史失败: ' + (err.response?.data?.detail || err.message));
      }
    }
  };

  const getSimilarityColor = (score?: number) => {
    if (!score) return 'outline';
    if (score >= 0.9) return 'default';
    if (score >= 0.7) return 'secondary';
    return 'outline';
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">RAG历史搜索</h1>
        <Button onClick={() => setHistory([])} variant="outline">清空历史</Button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="text-red-800">{error}</div>
          <Button onClick={() => setError(null)} className="mt-2" variant="outline">关闭</Button>
        </div>
      )}

      {/* 搜索框 */}
      <Card>
        <CardHeader>
          <CardTitle>搜索相似案例</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">搜索查询</label>
              <textarea
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full border rounded-md p-2 h-24"
                placeholder="输入问题或关键词，例如：数据库连接超时、CPU使用率过高等..."
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && e.ctrlKey) {
                    handleSearch();
                  }
                }}
              />
              <div className="text-xs text-gray-500 mt-1">提示: 按 Ctrl+Enter 快速搜索</div>
            </div>
            <Button
              onClick={handleSearch}
              disabled={searching}
              className="w-full"
            >
              {searching ? '搜索中...' : '搜索'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 搜索结果 */}
      {searchResults && (
        <Card>
          <CardHeader>
            <CardTitle>搜索结果 ({searchResults.results.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="mb-4 text-sm text-gray-500">
              查询: {searchResults.query} | 时间: {new Date(searchResults.timestamp).toLocaleString()}
            </div>
            {searchResults.results.length === 0 ? (
              <div className="text-gray-500 text-center py-8">未找到相关结果</div>
            ) : (
              <div className="space-y-3">
                {searchResults.results.map((result: any, index: number) => (
                  <div key={index} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <div className="font-semibold">结果 #{index + 1}</div>
                      <div className="flex gap-2">
                        {result.similarity && (
                          <Badge variant={getSimilarityColor(result.similarity)}>
                            相似度: {(result.similarity * 100).toFixed(1)}%
                          </Badge>
                        )}
                        {result.source && (
                          <Badge variant="outline">{result.source}</Badge>
                        )}
                      </div>
                    </div>
                    <div className="text-sm text-gray-700 mb-2">{result.content}</div>
                    {result.metadata && (
                      <div className="text-xs text-gray-500">
                        元数据: {JSON.stringify(result.metadata)}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 搜索历史 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>搜索历史 ({history.length})</CardTitle>
            <Button onClick={handleClearHistory} variant="outline" size="sm">
              清空历史
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {history.length === 0 ? (
            <div className="text-gray-500 text-center py-8">暂无搜索历史</div>
          ) : (
            <div className="space-y-3">
              {history.map((record) => (
                <div key={record.id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold">{record.query}</h3>
                    <div className="flex gap-2">
                      {record.similarity_score && (
                        <Badge variant={getSimilarityColor(record.similarity_score)}>
                          {(record.similarity_score * 100).toFixed(1)}%
                        </Badge>
                      )}
                      {record.source && (
                        <Badge variant="outline">{record.source}</Badge>
                      )}
                    </div>
                  </div>
                  <div className="text-sm text-gray-600 mb-2">
                    结果数: {record.results.length} | 时间: {new Date(record.timestamp).toLocaleString()}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleHistorySearch(record.query)}
                    >
                      重新搜索
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setSearchResults({
                          query: record.query,
                          results: record.results,
                          timestamp: record.timestamp
                        });
                      }}
                    >
                      查看结果
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* 使用说明 */}
      <Card>
        <CardHeader>
          <CardTitle>使用说明</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 text-sm text-gray-600">
            <div>• 输入问题或关键词进行搜索，系统会从知识库中查找相似的历史案例</div>
            <div>• 搜索结果会显示相似度评分，帮助您快速找到最相关的解决方案</div>
            <div>• 搜索历史会自动保存，方便您重复查询</div>
            <div>• 可以点击历史记录中的"重新搜索"按钮快速执行相同查询</div>
            <div>• 支持 Ctrl+Enter 快捷键快速执行搜索</div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
