'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

interface AnomalyData {
  timestamp: string;
  value: number;
  predicted: number;
  lowerBound: number;
  upperBound: number;
  isAnomaly: boolean;
}

interface AnomalyRecord {
  id: string;
  timestamp: string;
  metric: string;
  actualValue: number;
  predictedValue: number;
  deviation: number;
  confidence: number;
}

export default function AnomalyPage() {
  const [selectedModel, setSelectedModel] = useState('prophet');
  const [confidence, setConfidence] = useState(95);
  const [anomalyData, setAnomalyData] = useState<AnomalyData[]>([]);
  const [anomalyRecords, setAnomalyRecords] = useState<AnomalyRecord[]>([
    {
      id: 'AN-001',
      timestamp: new Date().toISOString(),
      metric: 'CPU使用率',
      actualValue: 92,
      predictedValue: 65,
      deviation: 27,
      confidence: 98,
    },
    {
      id: 'AN-002',
      timestamp: new Date(Date.now() - 3600000).toISOString(),
      metric: '内存使用率',
      actualValue: 88,
      predictedValue: 60,
      deviation: 28,
      confidence: 95,
    },
    {
      id: 'AN-003',
      timestamp: new Date(Date.now() - 7200000).toISOString(),
      metric: '磁盘IO',
      actualValue: 4500,
      predictedValue: 2000,
      deviation: 125,
      confidence: 92,
    },
  ]);

  // 生成模拟的时序数据
  const generateAnomalyData = () => {
    const data: AnomalyData[] = [];
    for (let i = 0; i < 100; i++) {
      const timestamp = new Date(Date.now() - (99 - i) * 3600000).toISOString();
      const baseValue = 50 + Math.sin(i / 10) * 20;
      const noise = (Math.random() - 0.5) * 10;
      const value = baseValue + noise;
      const predicted = baseValue;
      const lowerBound = predicted - 15;
      const upperBound = predicted + 15;
      const isAnomaly = value < lowerBound || value > upperBound;
      
      data.push({ timestamp, value, predicted, lowerBound, upperBound, isAnomaly });
    }
    setAnomalyData(data);
  };

  useEffect(() => {
    generateAnomalyData();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">异常检测</h1>
        <Button onClick={generateAnomalyData}>刷新数据</Button>
      </div>

      {/* 模型选择 */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">检测模型</label>
              <Select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
              >
                <option value="prophet">Prophet</option>
                <option value="isolation-forest">Isolation Forest</option>
                <option value="ensemble">Ensemble</option>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">置信度阈值 (%)</label>
              <Select
                value={confidence.toString()}
                onChange={(e) => setConfidence(Number(e.target.value))}
              >
                <option value="90">90%</option>
                <option value="95">95%</option>
                <option value="99">99%</option>
              </Select>
            </div>
            <div className="flex items-end">
              <Button className="w-full">应用配置</Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 时序图表 */}
      <Card>
        <CardHeader>
          <CardTitle>时序异常检测</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64 bg-gray-50 rounded-lg flex items-center justify-center">
            <p className="text-gray-500">时序图表区域 (使用ECharts渲染)</p>
            <div className="absolute bottom-4 right-4 space-x-2">
              <Badge className="bg-blue-100 text-blue-800">实际值</Badge>
              <Badge className="bg-green-100 text-green-800">预测值</Badge>
              <Badge className="bg-yellow-100 text-yellow-800">置信区间</Badge>
              <Badge className="bg-red-100 text-red-800">异常点</Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 异常记录列表 */}
      <Card>
        <CardHeader>
          <CardTitle>异常记录</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>时间</TableHead>
                <TableHead>指标</TableHead>
                <TableHead>实际值</TableHead>
                <TableHead>预测值</TableHead>
                <TableHead>偏差</TableHead>
                <TableHead>置信度</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {anomalyRecords.map((record) => (
                <TableRow key={record.id}>
                  <TableCell className="font-mono text-sm">{record.id}</TableCell>
                  <TableCell className="text-sm text-gray-500">
                    {new Date(record.timestamp).toLocaleString()}
                  </TableCell>
                  <TableCell>{record.metric}</TableCell>
                  <TableCell className="font-medium">{record.actualValue}</TableCell>
                  <TableCell>{record.predictedValue}</TableCell>
                  <TableCell>
                    <Badge className={record.deviation > 20 ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'}>
                      {record.deviation > 0 ? '+' : ''}{record.deviation.toFixed(1)}%
                    </Badge>
                  </TableCell>
                  <TableCell>{record.confidence}%</TableCell>
                  <TableCell>
                    <Button variant="outline" size="sm">
                      查看详情
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* 模型配置面板 */}
      <Card>
        <CardHeader>
          <CardTitle>模型配置</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">采样率</label>
              <Select>
                <option value="1s">1秒</option>
                <option value="5s">5秒</option>
                <option value="1m">1分钟</option>
                <option value="5m">5分钟</option>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">历史数据窗口</label>
              <Select>
                <option value="1h">1小时</option>
                <option value="24h">24小时</option>
                <option value="7d">7天</option>
                <option value="30d">30天</option>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">异常检测灵敏度</label>
              <Select>
                <option value="low">低</option>
                <option value="medium">中</option>
                <option value="high">高</option>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">自动告警</label>
              <Select>
                <option value="enabled">启用</option>
                <option value="disabled">禁用</option>
              </Select>
            </div>
          </div>
          <div className="mt-6 flex justify-end">
            <Button>保存配置</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
