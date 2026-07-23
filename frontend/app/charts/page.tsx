'use client'

import { useState, useRef, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';

export default function AdvancedChartsPage() {
  const [activeChart, setActiveChart] = useState('heatmap');
  const heatmapRef = useRef<HTMLCanvasElement>(null);
  const sankeyRef = useRef<HTMLCanvasElement>(null);
  const sunburstRef = useRef<HTMLCanvasElement>(null);
  const chordRef = useRef<HTMLCanvasElement>(null);

  // 热力图数据
  const heatmapData = Array.from({ length: 12 }, (_, i) =>
    Array.from({ length: 24 }, (_, j) => Math.floor(Math.random() * 100))
  );

  // 绘制热力图
  useEffect(() => {
    if (activeChart !== 'heatmap' || !heatmapRef.current) return;
    const canvas = heatmapRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const cellWidth = canvas.width / 24;
    const cellHeight = canvas.height / 12;

    heatmapData.forEach((row, i) => {
      row.forEach((value, j) => {
        const hue = 240 - (value * 2.4); // 从蓝色到红色
        ctx.fillStyle = `hsl(${hue}, 70%, 50%)`;
        ctx.fillRect(j * cellWidth, i * cellHeight, cellWidth - 1, cellHeight - 1);
      });
    });
  }, [activeChart]);

  // 绘制桑基图（简化版）
  useEffect(() => {
    if (activeChart !== 'sankey' || !sankeyRef.current) return;
    const canvas = sankeyRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // 绘制节点
    const nodes = [
      { x: 50, y: 100, label: '源' },
      { x: 50, y: 200, label: '源' },
      { x: 50, y: 300, label: '源' },
      { x: 300, y: 150, label: '中' },
      { x: 300, y: 250, label: '中' },
      { x: 550, y: 200, label: '目标' },
    ];

    // 绘制连接线
    ctx.strokeStyle = 'rgba(59, 130, 246, 0.3)';
    ctx.lineWidth = 20;
    ctx.lineCap = 'round';

    ctx.beginPath();
    ctx.moveTo(100, 100);
    ctx.bezierCurveTo(200, 100, 200, 150, 300, 150);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(100, 200);
    ctx.bezierCurveTo(200, 200, 200, 150, 300, 150);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(100, 200);
    ctx.bezierCurveTo(200, 200, 200, 250, 300, 250);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(100, 300);
    ctx.bezierCurveTo(200, 300, 200, 250, 300, 250);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(350, 150);
    ctx.bezierCurveTo(450, 150, 450, 200, 550, 200);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(350, 250);
    ctx.bezierCurveTo(450, 250, 450, 200, 550, 200);
    ctx.stroke();

    // 绘制节点
    nodes.forEach((node) => {
      ctx.fillStyle = '#3b82f6';
      ctx.fillRect(node.x, node.y - 20, 50, 40);
      ctx.fillStyle = '#fff';
      ctx.font = '12px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(node.label, node.x + 25, node.y + 5);
    });
  }, [activeChart]);

  // 绘制旭日图（简化版）
  useEffect(() => {
    if (activeChart !== 'sunburst' || !sunburstRef.current) return;
    const canvas = sunburstRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;

    const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];
    const data = [
      { startAngle: 0, endAngle: Math.PI * 0.5, innerRadius: 0, outerRadius: 80, color: colors[0] },
      { startAngle: Math.PI * 0.5, endAngle: Math.PI, innerRadius: 0, outerRadius: 80, color: colors[1] },
      { startAngle: Math.PI, endAngle: Math.PI * 1.5, innerRadius: 0, outerRadius: 80, color: colors[2] },
      { startAngle: Math.PI * 1.5, endAngle: Math.PI * 2, innerRadius: 0, outerRadius: 80, color: colors[3] },
      { startAngle: 0, endAngle: Math.PI * 0.25, innerRadius: 85, outerRadius: 130, color: colors[0] },
      { startAngle: Math.PI * 0.25, endAngle: Math.PI * 0.5, innerRadius: 85, outerRadius: 130, color: colors[1] },
      { startAngle: Math.PI * 0.5, endAngle: Math.PI * 0.75, innerRadius: 85, outerRadius: 130, color: colors[2] },
      { startAngle: Math.PI * 0.75, endAngle: Math.PI, innerRadius: 85, outerRadius: 130, color: colors[3] },
      { startAngle: Math.PI, endAngle: Math.PI * 1.25, innerRadius: 85, outerRadius: 130, color: colors[4] },
      { startAngle: Math.PI * 1.25, endAngle: Math.PI * 1.5, innerRadius: 85, outerRadius: 130, color: colors[0] },
      { startAngle: Math.PI * 1.5, endAngle: Math.PI * 1.75, innerRadius: 85, outerRadius: 130, color: colors[1] },
      { startAngle: Math.PI * 1.75, endAngle: Math.PI * 2, innerRadius: 85, outerRadius: 130, color: colors[2] },
    ];

    data.forEach((segment) => {
      ctx.beginPath();
      ctx.arc(centerX, centerY, segment.outerRadius, segment.startAngle, segment.endAngle);
      ctx.arc(centerX, centerY, segment.innerRadius, segment.endAngle, segment.startAngle, true);
      ctx.closePath();
      ctx.fillStyle = segment.color;
      ctx.fill();
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 2;
      ctx.stroke();
    });
  }, [activeChart]);

  // 绘制和弦图（简化版）
  useEffect(() => {
    if (activeChart !== 'chord' || !chordRef.current) return;
    const canvas = chordRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const radius = 120;

    const nodes = [
      { angle: 0, label: 'A' },
      { angle: Math.PI * 0.5, label: 'B' },
      { angle: Math.PI, label: 'C' },
      { angle: Math.PI * 1.5, label: 'D' },
    ];

    const links = [
      { from: 0, to: 1, value: 0.5 },
      { from: 1, to: 2, value: 0.3 },
      { from: 2, to: 3, value: 0.4 },
      { from: 3, to: 0, value: 0.6 },
      { from: 0, to: 2, value: 0.2 },
    ];

    // 绘制连接线
    links.forEach((link) => {
      const fromNode = nodes[link.from];
      const toNode = nodes[link.to];
      const fromX = centerX + Math.cos(fromNode.angle) * radius;
      const fromY = centerY + Math.sin(fromNode.angle) * radius;
      const toX = centerX + Math.cos(toNode.angle) * radius;
      const toY = centerY + Math.sin(toNode.angle) * radius;

      ctx.beginPath();
      ctx.moveTo(fromX, fromY);
      ctx.quadraticCurveTo(centerX, centerY, toX, toY);
      ctx.strokeStyle = `rgba(59, 130, 246, ${link.value})`;
      ctx.lineWidth = link.value * 20;
      ctx.stroke();
    });

    // 绘制节点
    nodes.forEach((node) => {
      const x = centerX + Math.cos(node.angle) * radius;
      const y = centerY + Math.sin(node.angle) * radius;

      ctx.beginPath();
      ctx.arc(x, y, 20, 0, Math.PI * 2);
      ctx.fillStyle = '#3b82f6';
      ctx.fill();
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 2;
      ctx.stroke();

      ctx.fillStyle = '#fff';
      ctx.font = '14px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(node.label, x, y);
    });
  }, [activeChart]);

  const chartTypes = [
    { id: 'heatmap', name: '热力图', description: '用于展示二维数据的密度分布' },
    { id: 'sankey', name: '桑基图', description: '用于展示流向和流量关系' },
    { id: 'sunburst', name: '旭日图', description: '用于展示层级结构和占比' },
    { id: 'chord', name: '和弦图', description: '用于展示节点间的关系强度' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">高级图表组件</h1>
        <div className="flex gap-2">
          <Select value={activeChart} onChange={(e) => setActiveChart(e.target.value)}>
            {chartTypes.map((type) => (
              <option key={type.id} value={type.id}>
                {type.name}
              </option>
            ))}
          </Select>
        </div>
      </div>

      {/* 图表概览 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {chartTypes.map((type) => (
          <Card
            key={type.id}
            className={`cursor-pointer transition-all ${
              activeChart === type.id ? 'ring-2 ring-blue-500' : 'hover:shadow-md'
            }`}
            onClick={() => setActiveChart(type.id)}
          >
            <CardHeader>
              <CardTitle className="text-sm">{type.name}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-gray-500">{type.description}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* 图表展示区 */}
      <Card>
        <CardHeader>
          <CardTitle>{chartTypes.find((t) => t.id === activeChart)?.name}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex justify-center">
            {activeChart === 'heatmap' && (
              <canvas ref={heatmapRef} width={600} height={300} className="border border-gray-200 rounded" />
            )}
            {activeChart === 'sankey' && (
              <canvas ref={sankeyRef} width={600} height={400} className="border border-gray-200 rounded" />
            )}
            {activeChart === 'sunburst' && (
              <canvas ref={sunburstRef} width={600} height={400} className="border border-gray-200 rounded" />
            )}
            {activeChart === 'chord' && (
              <canvas ref={chordRef} width={600} height={400} className="border border-gray-200 rounded" />
            )}
          </div>
          <p className="text-center text-sm text-gray-500 mt-4">
            使用 Canvas API 绘制的简化版图表，生产环境建议使用 ECharts 或 D3.js
          </p>
        </CardContent>
      </Card>

      {/* 图表说明 */}
      <Card>
        <CardHeader>
          <CardTitle>图表说明</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {activeChart === 'heatmap' && (
              <div>
                <h3 className="font-medium mb-2">热力图</h3>
                <p className="text-sm text-gray-600 mb-3">
                  热力图通过颜色的深浅来表示数据的大小，常用于展示二维数据的密度分布。
                </p>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-blue-500 rounded" />
                  <span className="text-xs">低值</span>
                  <div className="w-4 h-4 bg-green-500 rounded" />
                  <span className="text-xs">中值</span>
                  <div className="w-4 h-4 bg-yellow-500 rounded" />
                  <span className="text-xs">高值</span>
                  <div className="w-4 h-4 bg-red-500 rounded" />
                  <span className="text-xs">极高值</span>
                </div>
              </div>
            )}
            {activeChart === 'sankey' && (
              <div>
                <h3 className="font-medium mb-2">桑基图</h3>
                <p className="text-sm text-gray-600">
                  桑基图用于展示数据从一个状态流向另一个状态的过程，线条的粗细代表流量的大小。
                  常用于展示用户转化路径、能源流向等场景。
                </p>
              </div>
            )}
            {activeChart === 'sunburst' && (
              <div>
                <h3 className="font-medium mb-2">旭日图</h3>
                <p className="text-sm text-gray-600">
                  旭日图是一种多层饼图，用于展示层级结构数据。内层代表父类别，外层代表子类别，
                  扇区的大小代表数值的占比。常用于展示文件目录结构、组织架构等。
                </p>
              </div>
            )}
            {activeChart === 'chord' && (
              <div>
                <h3 className="font-medium mb-2">和弦图</h3>
                <p className="text-sm text-gray-600">
                  和弦图用于展示多个实体之间的关系强度。节点代表实体，连接线的粗细代表关系的强度。
                  常用于展示社交网络关系、贸易关系、代码依赖等。
                </p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 推荐库 */}
      <Card>
        <CardHeader>
          <CardTitle>推荐图表库</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">ECharts</h4>
              <p className="text-sm text-gray-600 mb-3">
                百度开源的可视化库，支持丰富的图表类型，文档完善，社区活跃。
              </p>
              <Button variant="outline" size="sm" className="w-full">
                查看文档
              </Button>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">D3.js</h4>
              <p className="text-sm text-gray-600 mb-3">
                强大的数据驱动文档库，提供底层API，灵活性极高，适合定制化需求。
              </p>
              <Button variant="outline" size="sm" className="w-full">
                查看文档
              </Button>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">Chart.js</h4>
              <p className="text-sm text-gray-600 mb-3">
                简单易用的图表库，支持响应式设计，适合快速实现常见图表。
              </p>
              <Button variant="outline" size="sm" className="w-full">
                查看文档
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
