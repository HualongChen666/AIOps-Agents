'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

interface MaturityDimension {
  name: string;
  score: number;
  maxScore: number;
  description: string;
}

interface ImprovementSuggestion {
  id: string;
  category: string;
  title: string;
  description: string;
  priority: 'high' | 'medium' | 'low';
  estimatedTime: string;
  targetLevel: number;
}

interface MaturityLevel {
  level: number;
  name: string;
  description: string;
  criteria: string[];
}

export default function MaturityPage() {
  const [dimensions, setDimensions] = useState<MaturityDimension[]>([]);

  const [suggestions, setSuggestions] = useState<ImprovementSuggestion[]>([]);
  const [loading, setLoading] = useState(false);

  const [maturityLevels] = useState<MaturityLevel[]>([
    {
      level: 1,
      name: '初始级',
      description: '依赖人工操作，缺乏自动化和监控',
      criteria: ['手动运维', '基础监控', '被动响应'],
    },
    {
      level: 2,
      name: '可重复级',
      description: '标准化流程，部分自动化工具',
      criteria: ['标准化流程', '脚本化操作', '基础告警'],
    },
    {
      level: 3,
      name: '已定义级',
      description: '完善的监控体系，自动化程度较高',
      criteria: ['全面监控', '自动化告警', '标准化修复'],
    },
    {
      level: 4,
      name: '已管理级',
      description: '数据驱动决策，具备预测能力',
      criteria: ['数据分析', '故障预测', '智能告警'],
    },
    {
      level: 5,
      name: '优化级',
      description: 'AI驱动，自主优化，持续改进',
      criteria: ['AI驱动', '自主优化', '持续改进'],
    },
  ]);

  const fetchMaturity = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/maturity/assess');
      if (!res.ok) {
        throw new Error(`评估接口返回 ${res.status}`);
      }
      const data = await res.json();
      setDimensions((data.dimensions || []) as MaturityDimension[]);
      setSuggestions((data.recommendations || []) as ImprovementSuggestion[]);
    } catch (err) {
      console.error('成熟度评估加载失败:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMaturity();
  }, []);

  const overallScore = dimensions.length
    ? Math.round(dimensions.reduce((sum, d) => sum + d.score, 0) / dimensions.length)
    : 0;
  const currentLevel = overallScore >= 90 ? 5 : overallScore >= 75 ? 4 : overallScore >= 60 ? 3 : overallScore >= 40 ? 2 : 1;

  const highestDimension = dimensions.length
    ? dimensions.reduce((max, d) => (d.score > max.score ? d : max), dimensions[0])
    : null;
  const lowestDimension = dimensions.length
    ? dimensions.reduce((min, d) => (d.score < min.score ? d : min), dimensions[0])
    : null;

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'bg-red-100 text-red-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'low':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">AIOps成熟度评估</h1>
        <Button onClick={fetchMaturity} disabled={loading}>
          {loading ? '评估中...' : '重新评估'}
        </Button>
      </div>

      {/* 总体评分 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总体成熟度</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-4xl font-bold text-blue-600">{overallScore}</p>
            <p className="text-sm text-gray-500 mt-1">当前等级: Level {currentLevel}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">当前等级</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{maturityLevels[currentLevel - 1].name}</p>
            <p className="text-sm text-gray-500 mt-1">{maturityLevels[currentLevel - 1].description}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">最高维度</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{highestDimension?.name ?? '-'}</p>
            <p className="text-sm text-gray-500 mt-1">得分: {highestDimension?.score ?? 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">待提升维度</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{lowestDimension?.name ?? '-'}</p>
            <p className="text-sm text-gray-500 mt-1">得分: {lowestDimension?.score ?? 0}</p>
          </CardContent>
        </Card>
      </div>

      {/* 雷达图 */}
      <Card>
        <CardHeader>
          <CardTitle>成熟度雷达图</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-96 bg-gray-50 rounded-lg flex items-center justify-center">
            <p className="text-gray-500">雷达图区域</p>
          </div>
        </CardContent>
      </Card>

      {/* 维度详情 */}
      <Card>
        <CardHeader>
          <CardTitle>维度详情</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {dimensions.map((dimension) => (
              <div key={dimension.name} className="p-4 border border-gray-200 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <h3 className="font-medium">{dimension.name}</h3>
                    <p className="text-sm text-gray-500">{dimension.description}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-2xl font-bold">{dimension.score}</p>
                    <p className="text-sm text-gray-500">/ {dimension.maxScore}</p>
                  </div>
                </div>
                <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-600"
                    style={{ width: `${(dimension.score / dimension.maxScore) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 改进建议 */}
      <Card>
        <CardHeader>
          <CardTitle>改进建议</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {suggestions.map((suggestion) => (
              <div key={suggestion.id} className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-sm text-gray-500">{suggestion.category}</span>
                      <span className={`px-2 py-1 text-xs font-medium rounded ${getPriorityColor(suggestion.priority)}`}>
                        {suggestion.priority === 'high' ? '高优先级' : suggestion.priority === 'medium' ? '中优先级' : '低优先级'}
                      </span>
                      <span className="text-xs text-gray-500">预计: {suggestion.estimatedTime}</span>
                      <span className="text-xs text-blue-600">目标: Level {suggestion.targetLevel}</span>
                    </div>
                    <h3 className="font-medium text-gray-900 mb-1">{suggestion.title}</h3>
                    <p className="text-sm text-gray-600">{suggestion.description}</p>
                  </div>
                  <Button variant="outline" size="sm">
                    查看详情
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 成熟度等级说明 */}
      <Card>
        <CardHeader>
          <CardTitle>成熟度等级说明</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {maturityLevels.map((level) => (
              <div
                key={level.level}
                className={`p-4 border rounded-lg ${level.level === currentLevel
                  ? 'border-blue-500 bg-blue-50'
                  : level.level < currentLevel
                    ? 'border-green-200 bg-green-50'
                    : 'border-gray-200'
                  }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-2xl font-bold">Level {level.level}</span>
                  {level.level === currentLevel && (
                    <span className="px-2 py-1 text-xs bg-blue-500 text-white rounded">当前</span>
                  )}
                  {level.level < currentLevel && (
                    <span className="px-2 py-1 text-xs bg-green-500 text-white rounded">已达成</span>
                  )}
                </div>
                <h4 className="font-medium mb-1">{level.name}</h4>
                <p className="text-xs text-gray-600 mb-2">{level.description}</p>
                <div className="space-y-1">
                  {level.criteria.map((criterion, index) => (
                    <div key={index} className="flex items-center gap-1 text-xs text-gray-500">
                      <span>•</span>
                      <span>{criterion}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 改进路线图 */}
      <Card>
        <CardHeader>
          <CardTitle>改进路线图</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {/* 阶段1 */}
            <div className="relative pl-8 border-l-2 border-blue-200">
              <div className="absolute -left-2 top-0 w-4 h-4 bg-blue-500 rounded-full" />
              <div className="mb-2">
                <h4 className="font-medium text-lg">阶段1: 基础优化 (1-2个月)</h4>
                <p className="text-sm text-gray-500">目标: 达到Level 3</p>
              </div>
              <div className="space-y-2">
                {suggestions.filter(s => s.targetLevel === 3).map((suggestion) => (
                  <div key={suggestion.id} className="p-3 bg-gray-50 rounded">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-sm">{suggestion.title}</span>
                      <span className={`px-2 py-0.5 text-xs rounded ${getPriorityColor(suggestion.priority)}`}>
                        {suggestion.priority === 'high' ? '高' : '中'}
                      </span>
                    </div>
                    <p className="text-xs text-gray-600">{suggestion.description}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* 阶段2 */}
            <div className="relative pl-8 border-l-2 border-purple-200">
              <div className="absolute -left-2 top-0 w-4 h-4 bg-purple-500 rounded-full" />
              <div className="mb-2">
                <h4 className="font-medium text-lg">阶段2: 智能化升级 (3-4个月)</h4>
                <p className="text-sm text-gray-500">目标: 达到Level 4</p>
              </div>
              <div className="space-y-2">
                {suggestions.filter(s => s.targetLevel === 4).map((suggestion) => (
                  <div key={suggestion.id} className="p-3 bg-gray-50 rounded">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-sm">{suggestion.title}</span>
                      <span className={`px-2 py-0.5 text-xs rounded ${getPriorityColor(suggestion.priority)}`}>
                        {suggestion.priority === 'high' ? '高' : '中'}
                      </span>
                    </div>
                    <p className="text-xs text-gray-600">{suggestion.description}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* 阶段3 */}
            <div className="relative pl-8 border-l-2 border-green-200">
              <div className="absolute -left-2 top-0 w-4 h-4 bg-green-500 rounded-full" />
              <div className="mb-2">
                <h4 className="font-medium text-lg">阶段3: AI驱动优化 (6-12个月)</h4>
                <p className="text-sm text-gray-500">目标: 达到Level 5</p>
              </div>
              <div className="p-3 bg-gray-50 rounded">
                <p className="text-sm text-gray-600">
                  引入AI驱动的自主优化能力，实现持续改进和智能决策
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
