'use client';

import { useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface TrendChartProps {
  data: number[];
  labels?: string[];
  color?: string;
  height?: number;
  title?: string;
  showGrid?: boolean;
  showTooltip?: boolean;
}

export function TrendChart({
  data,
  labels,
  color = '#3b82f6',
  height = 200,
  title,
  showGrid = true,
  showTooltip = true,
}: TrendChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const padding = 40;
    const chartWidth = canvas.width - padding * 2;
    const chartHeight = canvas.height - padding * 2;

    // Find min and max values
    const maxValue = Math.max(...data, 1);
    const minValue = Math.min(...data, 0);

    // Draw grid
    if (showGrid) {
      ctx.strokeStyle = '#e5e7eb';
      ctx.lineWidth = 1;
      for (let i = 0; i <= 5; i++) {
        const y = padding + (chartHeight / 5) * i;
        ctx.beginPath();
        ctx.moveTo(padding, y);
        ctx.lineTo(canvas.width - padding, y);
        ctx.stroke();
      }
    }

    // Draw line chart
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.beginPath();

    data.forEach((value, index) => {
      const x = padding + (chartWidth / (data.length - 1)) * index;
      const y = padding + chartHeight - ((value - minValue) / (maxValue - minValue)) * chartHeight;

      if (index === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    });

    ctx.stroke();

    // Draw area under line
    ctx.fillStyle = color + '20';
    ctx.lineTo(padding + chartWidth, padding + chartHeight);
    ctx.lineTo(padding, padding + chartHeight);
    ctx.closePath();
    ctx.fill();

    // Draw points
    ctx.fillStyle = color;
    data.forEach((value, index) => {
      const x = padding + (chartWidth / (data.length - 1)) * index;
      const y = padding + chartHeight - ((value - minValue) / (maxValue - minValue)) * chartHeight;

      ctx.beginPath();
      ctx.arc(x, y, 4, 0, Math.PI * 2);
      ctx.fill();
    });

    // Draw labels
    if (labels) {
      ctx.fillStyle = '#6b7280';
      ctx.font = '12px sans-serif';
      ctx.textAlign = 'center';
      labels.forEach((label, index) => {
        const x = padding + (chartWidth / (labels.length - 1)) * index;
        ctx.fillText(label, x, canvas.height - 10);
      });
    }
  }, [data, labels, color, height, showGrid]);

  return (
    <Card>
      {title && (
        <CardHeader>
          <CardTitle className="text-sm">{title}</CardTitle>
        </CardHeader>
      )}
      <CardContent>
        <canvas
          ref={canvasRef}
          width={400}
          height={height}
          className="w-full"
        />
      </CardContent>
    </Card>
  );
}
