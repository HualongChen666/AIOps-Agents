'use client';

import { useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface GaugeChartProps {
  value: number;
  min?: number;
  max?: number;
  title?: string;
  unit?: string;
  color?: string;
  size?: number;
}

export function GaugeChart({
  value,
  min = 0,
  max = 100,
  title,
  unit = '%',
  color = '#3b82f6',
  size = 200,
}: GaugeChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const radius = Math.min(centerX, centerY) - 20;

    // Normalize value
    const normalizedValue = Math.max(min, Math.min(max, value));
    const percentage = (normalizedValue - min) / (max - min);

    // Draw background arc
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, Math.PI * 0.75, Math.PI * 2.25);
    ctx.strokeStyle = '#e5e7eb';
    ctx.lineWidth = 20;
    ctx.lineCap = 'round';
    ctx.stroke();

    // Draw value arc
    const startAngle = Math.PI * 0.75;
    const endAngle = startAngle + (Math.PI * 1.5) * percentage;

    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, startAngle, endAngle);
    ctx.strokeStyle = color;
    ctx.lineWidth = 20;
    ctx.lineCap = 'round';
    ctx.stroke();

    // Draw value text
    ctx.fillStyle = '#1f2937';
    ctx.font = 'bold 32px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(`${normalizedValue.toFixed(1)}${unit}`, centerX, centerY);

    // Draw title
    if (title) {
      ctx.fillStyle = '#6b7280';
      ctx.font = '14px sans-serif';
      ctx.fillText(title, centerX, centerY + 40);
    }
  }, [value, min, max, title, unit, color, size]);

  return (
    <Card>
      {title && (
        <CardHeader>
          <CardTitle className="text-sm">{title}</CardTitle>
        </CardHeader>
      )}
      <CardContent className="flex justify-center">
        <canvas
          ref={canvasRef}
          width={size}
          height={size}
        />
      </CardContent>
    </Card>
  );
}
