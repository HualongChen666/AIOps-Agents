'use client'

import { useState, useEffect, useRef, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

// 虚拟列表组件示例
function VirtualList({ items, itemHeight = 50, containerHeight = 400 }: { items: any[], itemHeight?: number, containerHeight?: number }) {
  const [scrollTop, setScrollTop] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const visibleCount = Math.ceil(containerHeight / itemHeight);
  const startIndex = Math.floor(scrollTop / itemHeight);
  const endIndex = Math.min(startIndex + visibleCount, items.length);
  const visibleItems = items.slice(startIndex, endIndex);

  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    setScrollTop(e.currentTarget.scrollTop);
  }, []);

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      style={{ height: containerHeight, overflow: 'auto' }}
      className="border border-gray-200 rounded-lg"
    >
      <div style={{ height: items.length * itemHeight, position: 'relative' }}>
        {visibleItems.map((item, index) => (
          <div
            key={startIndex + index}
            style={{
              position: 'absolute',
              top: (startIndex + index) * itemHeight,
              height: itemHeight,
              left: 0,
              right: 0,
            }}
            className="p-3 border-b border-gray-100 hover:bg-gray-50"
          >
            <div className="flex items-center justify-between">
              <span className="font-medium">{item.name}</span>
              <Badge className={item.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                {item.status}
              </Badge>
            </div>
            <p className="text-sm text-gray-500">{item.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

// 懒加载组件示例
function LazyImage({ src, alt, placeholder }: { src: string, alt: string, placeholder: string }) {
  const [isLoaded, setIsLoaded] = useState(false);
  const [isInView, setIsInView] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsInView(true);
          observer.disconnect();
        }
      },
      { threshold: 0.1 }
    );

    if (imgRef.current) {
      observer.observe(imgRef.current);
    }

    return () => observer.disconnect();
  }, []);

  return (
    <div ref={imgRef} className="aspect-video bg-gray-200 rounded-lg overflow-hidden">
      {isInView ? (
        <img
          src={src}
          alt={alt}
          onLoad={() => setIsLoaded(true)}
          className={`w-full h-full object-cover transition-opacity duration-300 ${isLoaded ? 'opacity-100' : 'opacity-0'}`}
        />
      ) : (
        <div className="w-full h-full flex items-center justify-center text-gray-400">
          {placeholder}
        </div>
      )}
    </div>
  );
}

export default function PerformancePage() {
  const [workerResult, setWorkerResult] = useState<string>('');
  const [isCalculating, setIsCalculating] = useState(false);
  const [serviceWorkerStatus, setServiceWorkerStatus] = useState<'unknown' | 'supported' | 'not-supported'>('unknown');

  // 生成大量测试数据
  const generateLargeDataset = useCallback((count: number) => {
    return Array.from({ length: count }, (_, i) => ({
      id: i,
      name: `项目 ${i + 1}`,
      status: i % 3 === 0 ? 'active' : 'inactive',
      description: `这是第 ${i + 1} 个项目的描述信息`,
    }));
  }, []);

  const largeDataset = generateLargeDataset(10000);

  // Web Worker 示例
  const runHeavyCalculation = useCallback(() => {
    setIsCalculating(true);
    
    const workerCode = `
      self.onmessage = function(e) {
        const result = heavyCalculation(e.data);
        self.postMessage(result);
      };
      
      function heavyCalculation(n) {
        let sum = 0;
        for (let i = 0; i < n; i++) {
          for (let j = 0; j < 1000; j++) {
            sum += Math.sqrt(i * j);
          }
        }
        return sum;
      }
    `;

    const blob = new Blob([workerCode], { type: 'application/javascript' });
    const worker = new Worker(URL.createObjectURL(blob));

    worker.onmessage = (e) => {
      setWorkerResult(`计算结果: ${e.data.toFixed(2)}`);
      setIsCalculating(false);
      worker.terminate();
    };

    worker.postMessage(10000);
  }, []);

  // 检查 Service Worker 支持
  useEffect(() => {
    if ('serviceWorker' in navigator) {
      setServiceWorkerStatus('supported');
    } else {
      setServiceWorkerStatus('not-supported');
    }
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">性能优化</h1>
        <Badge className="bg-blue-100 text-blue-800">技术展示</Badge>
      </div>

      {/* 性能优化概览 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">虚拟列表</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-green-600">✓</p>
            <p className="text-sm text-gray-500">已实现</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">懒加载</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-green-600">✓</p>
            <p className="text-sm text-gray-500">已实现</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Web Worker</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-green-600">✓</p>
            <p className="text-sm text-gray-500">已实现</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Service Worker</CardTitle>
          </CardHeader>
          <CardContent>
            <p className={`text-2xl font-bold ${serviceWorkerStatus === 'supported' ? 'text-green-600' : 'text-red-600'}`}>
              {serviceWorkerStatus === 'supported' ? '✓' : '✗'}
            </p>
            <p className="text-sm text-gray-500">
              {serviceWorkerStatus === 'supported' ? '支持' : '不支持'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* 虚拟列表演示 */}
      <Card>
        <CardHeader>
          <CardTitle>虚拟列表 (10,000 条数据)</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-600 mb-4">
            虚拟列表只渲染可见区域的元素，大幅提升大数据量列表的性能。
          </p>
          <VirtualList items={largeDataset} itemHeight={60} containerHeight={400} />
        </CardContent>
      </Card>

      {/* 懒加载演示 */}
      <Card>
        <CardHeader>
          <CardTitle>懒加载组件</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-600 mb-4">
            图片和组件只在进入视口时才加载，减少初始加载时间和带宽消耗。
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <LazyImage
              src="https://via.placeholder.com/400x300/3b82f6/ffffff?text=Image+1"
              alt="示例图片1"
              placeholder="图片加载中..."
            />
            <LazyImage
              src="https://via.placeholder.com/400x300/10b981/ffffff?text=Image+2"
              alt="示例图片2"
              placeholder="图片加载中..."
            />
            <LazyImage
              src="https://via.placeholder.com/400x300/f59e0b/ffffff?text=Image+3"
              alt="示例图片3"
              placeholder="图片加载中..."
            />
          </div>
        </CardContent>
      </Card>

      {/* Web Worker 演示 */}
      <Card>
        <CardHeader>
          <CardTitle>Web Worker</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-600 mb-4">
            Web Worker 在后台线程执行计算密集型任务，避免阻塞主线程，保持UI响应流畅。
          </p>
          <div className="space-y-4">
            <Button onClick={runHeavyCalculation} disabled={isCalculating}>
              {isCalculating ? '计算中...' : '运行繁重计算'}
            </Button>
            {workerResult && (
              <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                <p className="text-green-800">{workerResult}</p>
              </div>
            )}
            <p className="text-xs text-gray-500">
              注意：此计算在 Web Worker 中执行，不会阻塞主线程。
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Service Worker 状态 */}
      <Card>
        <CardHeader>
          <CardTitle>Service Worker 缓存</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-600 mb-4">
            Service Worker 可以缓存静态资源，实现离线访问和更快的加载速度。
          </p>
          <div className="p-4 border border-gray-200 rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium">Service Worker 支持</span>
              <Badge className={serviceWorkerStatus === 'supported' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                {serviceWorkerStatus === 'supported' ? '支持' : '不支持'}
              </Badge>
            </div>
            <p className="text-sm text-gray-600">
              {serviceWorkerStatus === 'supported'
                ? '当前浏览器支持 Service Worker，可以注册 Service Worker 实现资源缓存和离线访问。'
                : '当前浏览器不支持 Service Worker，无法使用 Service Worker 缓存功能。'}
            </p>
          </div>
        </CardContent>
      </Card>

      {/* 性能优化建议 */}
      <Card>
        <CardHeader>
          <CardTitle>性能优化建议</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-start gap-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <span className="text-blue-600">1.</span>
              <div>
                <p className="font-medium text-blue-800">使用虚拟列表</p>
                <p className="text-sm text-blue-700">对于大数据量列表，使用虚拟滚动只渲染可见元素。</p>
              </div>
            </div>
            <div className="flex items-start gap-3 p-3 bg-green-50 border border-green-200 rounded-lg">
              <span className="text-green-600">2.</span>
              <div>
                <p className="font-medium text-green-800">实现懒加载</p>
                <p className="text-sm text-green-700">图片和组件按需加载，减少初始加载时间。</p>
              </div>
            </div>
            <div className="flex items-start gap-3 p-3 bg-purple-50 border border-purple-200 rounded-lg">
              <span className="text-purple-600">3.</span>
              <div>
                <p className="font-medium text-purple-800">使用 Web Worker</p>
                <p className="text-sm text-purple-700">将计算密集型任务放到后台线程执行。</p>
              </div>
            </div>
            <div className="flex items-start gap-3 p-3 bg-orange-50 border border-orange-200 rounded-lg">
              <span className="text-orange-600">4.</span>
              <div>
                <p className="font-medium text-orange-800">启用 Service Worker</p>
                <p className="text-sm text-orange-700">缓存静态资源，实现离线访问和快速加载。</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
