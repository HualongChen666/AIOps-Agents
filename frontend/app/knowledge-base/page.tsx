'use client'

import { useState } from 'react';
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

export default function KnowledgeBasePage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedRunbook, setSelectedRunbook] = useState<Runbook | null>(null);
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);

  const [runbooks, setRunbooks] = useState<Runbook[]>([
    {
      id: 'RB-001',
      title: '数据库故障排查',
      category: '故障处理',
      description: '数据库连接失败、慢查询等常见问题的排查步骤',
      tags: ['数据库', '故障', '排查'],
      author: '张三',
      lastUpdated: new Date(Date.now() - 86400000),
      content: '1. 检查数据库连接状态\n2. 查看慢查询日志\n3. 分析索引使用情况\n4. 优化SQL语句',
    },
    {
      id: 'RB-002',
      title: '服务扩容流程',
      category: '运维操作',
      description: '服务扩容的标准操作流程和注意事项',
      tags: ['扩容', '运维', '流程'],
      author: '李四',
      lastUpdated: new Date(Date.now() - 172800000),
      content: '1. 评估当前负载\n2. 选择扩容方案\n3. 执行扩容操作\n4. 验证服务状态',
    },
    {
      id: 'RB-003',
      title: '告警响应SOP',
      category: '告警处理',
      description: '各类告警的标准响应流程和处理方法',
      tags: ['告警', '响应', 'SOP'],
      author: '王五',
      lastUpdated: new Date(Date.now() - 259200000),
      content: '1. 接收告警通知\n2. 确认告警级别\n3. 执行相应处理\n4. 记录处理结果',
    },
    {
      id: 'RB-004',
      title: 'API限流配置',
      category: '配置管理',
      description: 'API限流的配置方法和最佳实践',
      tags: ['API', '限流', '配置'],
      author: '赵六',
      lastUpdated: new Date(Date.now() - 345600000),
      content: '1. 确定限流策略\n2. 配置限流规则\n3. 监控限流效果\n4. 调整限流参数',
    },
    {
      id: 'RB-005',
      title: '日志分析技巧',
      category: '日志分析',
      description: '日志分析的方法和常用工具',
      tags: ['日志', '分析', '工具'],
      author: '张三',
      lastUpdated: new Date(Date.now() - 432000000),
      content: '1. 收集日志数据\n2. 使用日志分析工具\n3. 识别异常模式\n4. 生成分析报告',
    },
  ]);

  const categories = ['all', '故障处理', '运维操作', '告警处理', '配置管理', '日志分析'];

  const handleSearch = () => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }

    const results: SearchResult[] = runbooks
      .map((runbook) => {
        const titleMatch = runbook.title.toLowerCase().includes(searchQuery.toLowerCase());
        const descMatch = runbook.description.toLowerCase().includes(searchQuery.toLowerCase());
        const tagMatches = runbook.tags.filter((tag) =>
          tag.toLowerCase().includes(searchQuery.toLowerCase())
        );
        const contentMatch = runbook.content.toLowerCase().includes(searchQuery.toLowerCase());

        let relevance = 0;
        if (titleMatch) relevance += 3;
        if (descMatch) relevance += 2;
        if (tagMatches.length > 0) relevance += tagMatches.length * 2;
        if (contentMatch) relevance += 1;

        return {
          runbook,
          relevance,
          matchedTags: tagMatches,
        };
      })
      .filter((result) => result.relevance > 0)
      .sort((a, b) => b.relevance - a.relevance);

    setSearchResults(results);
  };

  const handleAIRecommend = () => {
    // 模拟AI推荐
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
            <Button onClick={handleSearch}>搜索</Button>
            <Button variant="outline" onClick={handleAIRecommend}>
              AI推荐
            </Button>
          </div>

          {/* 搜索结果 */}
          {searchResults.length > 0 && (
            <div className="space-y-3">
              <h4 className="font-medium">搜索结果</h4>
              {searchResults.map((result, index) => (
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
                  className={`p-3 border rounded-lg cursor-pointer hover:bg-gray-50 transition ${
                    selectedRunbook?.id === runbook.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
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
