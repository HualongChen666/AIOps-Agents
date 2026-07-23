'use client'

import { useEffect, useRef } from 'react';

interface ResourceData {
  timestamp: string;
  cpu: number;
  memory: number;
  disk: number;
}

interface ResourceTrendChartProps {
  data: ResourceData[];
}

export const ResourceTrendChart = ({ data }: ResourceTrendChartProps) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!canvasRef.current || !data.length) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // 设置画布尺寸
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * 2;
    canvas.height = rect.height * 2;
    ctx.scale(2, 2);

    const width = rect.width;
    const height = rect.height;
    const padding = 40;

    // 清空画布
    ctx.clearRect(0, 0, width, height);

    // 绘制背景
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, width, height);

    // 绘制网格
    ctx.strokeStyle = '#e5e7eb';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 5; i++) {
      const y = padding + (height - 2 * padding) * (i / 5);
      ctx.beginPath();
      ctx.moveTo(padding, y);
      ctx.lineTo(width - padding, y);
      ctx.stroke();
    }

    // 绘制数据线
    const drawLine = (values: number[], color: string) => {
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.beginPath();

      values.forEach((value, index) => {
        const x = padding + (width - 2 * padding) * (index / (values.length - 1));
        const y = height - padding - (height - 2 * padding) * (value / 100);
        if (index === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      });

      ctx.stroke();
    };

    // 绘制CPU、内存、磁盘趋势
    drawLine(data.map((d) => d.cpu), '#3b82f6');
    drawLine(data.map((d) => d.memory), '#10b981');
    drawLine(data.map((d) => d.disk), '#f59e0b');

    // 绘制图例
    const legendY = 20;
    ctx.font = '12px sans-serif';
    
    ctx.fillStyle = '#3b82f6';
    ctx.fillRect(width - 150, legendY, 12, 12);
    ctx.fillStyle = '#374151';
    ctx.fillText('CPU', width - 130, legendY + 10);

    ctx.fillStyle = '#10b981';
    ctx.fillRect(width - 80, legendY, 12, 12);
    ctx.fillStyle = '#374151';
    ctx.fillText('内存', width - 60, legendY + 10);

    ctx.fillStyle = '#f59e0b';
    ctx.fillRect(width - 150, legendY + 20, 12, 12);
    ctx.fillStyle = '#374151';
    ctx.fillText('磁盘', width - 130, legendY + 30);
  }, [data]);

  return (
    <div className="w-full h-64">
      <canvas ref={canvasRef} className="w-full h-full" />
    </div>
  );
};
