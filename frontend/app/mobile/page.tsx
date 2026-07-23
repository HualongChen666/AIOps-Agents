'use client'

import { useState, useEffect, useRef, TouchEvent } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';

export default function MobilePage() {
  const [isMobile, setIsMobile] = useState(false);
  const [viewportWidth, setViewportWidth] = useState(0);
  const [touchStart, setTouchStart] = useState<{ x: number; y: number } | null>(null);
  const [swipeDirection, setSwipeDirection] = useState<string>('');
  const [activeTab, setActiveTab] = useState('dashboard');
  const [bottomNavVisible, setBottomNavVisible] = useState(true);
  const cardRef = useRef<HTMLDivElement>(null);

  // 检测移动设备
  useEffect(() => {
    const checkMobile = () => {
      const width = window.innerWidth;
      setViewportWidth(width);
      setIsMobile(width < 768);
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // 手势处理
  const handleTouchStart = (e: TouchEvent) => {
    const touch = e.touches[0];
    setTouchStart({ x: touch.clientX, y: touch.clientY });
  };

  const handleTouchEnd = (e: TouchEvent) => {
    if (!touchStart) return;

    const touch = e.changedTouches[0];
    const deltaX = touch.clientX - touchStart.x;
    const deltaY = touch.clientY - touchStart.y;

    // 判断滑动方向
    if (Math.abs(deltaX) > Math.abs(deltaY)) {
      if (Math.abs(deltaX) > 50) {
        setSwipeDirection(deltaX > 0 ? 'right' : 'left');
      }
    } else {
      if (Math.abs(deltaY) > 50) {
        setSwipeDirection(deltaY > 0 ? 'down' : 'up');
      }
    }

    setTouchStart(null);
  };

  // 清除滑动方向
  useEffect(() => {
    if (swipeDirection) {
      const timer = setTimeout(() => setSwipeDirection(''), 1000);
      return () => clearTimeout(timer);
    }
  }, [swipeDirection]);

  const bottomNavItems = [
    { id: 'dashboard', label: '仪表盘', icon: '📊' },
    { id: 'alerts', label: '告警', icon: '🔔' },
    { id: 'topology', label: '拓扑', icon: '🔗' },
    { id: 'settings', label: '设置', icon: '⚙️' },
  ];

  return (
    <div className="space-y-6 pb-20">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">移动端适配</h1>
        <div className="flex items-center gap-2">
          <span className={`px-3 py-1 rounded-full text-sm ${isMobile ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
            {isMobile ? '移动视图' : '桌面视图'}
          </span>
          <span className="text-sm text-gray-500">{viewportWidth}px</span>
        </div>
      </div>

      {/* 响应式概览 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">视口宽度</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{viewportWidth}px</p>
            <p className="text-sm text-gray-500 mt-1">
              {isMobile ? '移动设备' : '桌面设备'}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">断点</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {viewportWidth < 640 ? 'XS' : viewportWidth < 768 ? 'SM' : viewportWidth < 1024 ? 'MD' : 'LG'}
            </p>
            <p className="text-sm text-gray-500 mt-1">Tailwind断点</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">底部导航</CardTitle>
          </CardHeader>
          <CardContent>
            <p className={`text-2xl font-bold ${bottomNavVisible ? 'text-green-600' : 'text-gray-400'}`}>
              {bottomNavVisible ? '显示' : '隐藏'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* 响应式布局演示 */}
      <Card>
        <CardHeader>
          <CardTitle>响应式布局</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-3">网格布局</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
                <div key={i} className="p-4 bg-blue-50 rounded-lg text-center">
                  <span className="font-medium">项目 {i}</span>
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-500 mt-2">
              调整浏览器窗口大小查看响应式效果
            </p>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-3">弹性布局</h3>
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="flex-1 p-4 bg-green-50 rounded-lg text-center">
                <span className="font-medium">弹性项目 1</span>
              </div>
              <div className="flex-1 p-4 bg-yellow-50 rounded-lg text-center">
                <span className="font-medium">弹性项目 2</span>
              </div>
              <div className="flex-1 p-4 bg-red-50 rounded-lg text-center">
                <span className="font-medium">弹性项目 3</span>
              </div>
            </div>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-3">隐藏/显示</h3>
            <div className="space-y-2">
              <div className="p-3 bg-gray-50 rounded-lg">
                <span className="hidden sm:inline">桌面可见</span>
                <span className="sm:hidden">移动可见</span>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg">
                <span className="hidden md:inline">中等屏幕及以上可见</span>
                <span className="md:hidden">小屏幕可见</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 触摸友好交互 */}
      <Card>
        <CardHeader>
          <CardTitle>触摸友好交互</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-3">触摸目标大小</h3>
            <div className="flex flex-wrap gap-4">
              <Button size="lg" className="min-h-[44px] min-w-[44px]">
                大按钮 (44px+)
              </Button>
              <Button className="min-h-[44px] min-w-[44px]">
                标准按钮
              </Button>
              <Button size="sm" className="min-h-[44px] min-w-[44px]">
                小按钮
              </Button>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              iOS和Android建议最小触摸目标为44x44px
            </p>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-3">触摸反馈</h3>
            <div className="space-y-2">
              <Button className="w-full active:scale-95 transition-transform">
                按下有缩放效果
              </Button>
              <Button variant="outline" className="w-full active:bg-gray-100 transition-colors">
                按下有背景变化
              </Button>
            </div>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-3">滑动卡片</h3>
            <div
              ref={cardRef}
              className="p-6 bg-gradient-to-r from-blue-500 to-purple-500 rounded-lg text-white cursor-grab active:cursor-grabbing select-none"
              onTouchStart={handleTouchStart}
              onTouchEnd={handleTouchEnd}
            >
              <p className="font-medium mb-2">在此区域滑动</p>
              <p className="text-sm opacity-90">检测到的滑动方向: {swipeDirection || '无'}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 底部导航栏 */}
      <Card>
        <CardHeader>
          <CardTitle>底部导航栏</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <div className="flex items-center justify-between mb-4">
              <label className="text-sm font-medium text-gray-700">显示底部导航</label>
              <Button
                variant={bottomNavVisible ? 'default' : 'outline'}
                size="sm"
                onClick={() => setBottomNavVisible(!bottomNavVisible)}
              >
                {bottomNavVisible ? '隐藏' : '显示'}
              </Button>
            </div>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-3">导航项</h3>
            <div className="flex gap-2">
              {bottomNavItems.map((item) => (
                <Button
                  key={item.id}
                  variant={activeTab === item.id ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setActiveTab(item.id)}
                >
                  {item.icon} {item.label}
                </Button>
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-3">移动端预览</h3>
            <div className="relative max-w-sm mx-auto border-2 border-gray-300 rounded-2xl overflow-hidden">
              <div className="bg-gray-100 p-4">
                <div className="bg-white rounded-lg p-4 mb-4">
                  <p className="text-sm text-gray-600">当前页面: {activeTab}</p>
                </div>
              </div>
              {bottomNavVisible && (
                <div className="absolute bottom-0 left-0 right-0 bg-white border-t border-gray-200">
                  <div className="flex justify-around py-2">
                    {bottomNavItems.map((item) => (
                      <button
                        key={item.id}
                        onClick={() => setActiveTab(item.id)}
                        className={`flex flex-col items-center p-2 min-w-[60px] min-h-[60px] ${
                          activeTab === item.id ? 'text-blue-600' : 'text-gray-500'
                        }`}
                      >
                        <span className="text-2xl mb-1">{item.icon}</span>
                        <span className="text-xs">{item.label}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 手势操作 */}
      <Card>
        <CardHeader>
          <CardTitle>手势操作</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-3">支持的手势</h3>
            <div className="space-y-2">
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm">点击</span>
                <span className="text-xs text-gray-500">选择/激活</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm">长按</span>
                <span className="text-xs text-gray-500">显示上下文菜单</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm">滑动</span>
                <span className="text-xs text-gray-500">导航/滚动</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm">捏合</span>
                <span className="text-xs text-gray-500">缩放</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm">双击</span>
                <span className="text-xs text-gray-500">放大/选择</span>
              </div>
            </div>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-3">手势演示区域</h3>
            <div
              className="p-8 bg-gray-100 rounded-lg text-center select-none"
              onTouchStart={handleTouchStart}
              onTouchEnd={handleTouchEnd}
            >
              <p className="text-gray-600 mb-2">在此区域进行手势操作</p>
              <p className="text-sm text-gray-500">
                检测到的滑动: <span className="font-medium">{swipeDirection || '无'}</span>
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 移动端优化建议 */}
      <Card>
        <CardHeader>
          <CardTitle>移动端优化建议</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="p-4 bg-blue-50 rounded-lg">
              <h4 className="font-medium text-blue-900 mb-1">触摸目标</h4>
              <p className="text-sm text-blue-700">确保所有可交互元素至少44x44px，方便手指点击</p>
            </div>
            <div className="p-4 bg-green-50 rounded-lg">
              <h4 className="font-medium text-green-900 mb-1">字体大小</h4>
              <p className="text-sm text-green-700">使用至少16px的字体大小，避免自动缩放</p>
            </div>
            <div className="p-4 bg-yellow-50 rounded-lg">
              <h4 className="font-medium text-yellow-900 mb-1">表单输入</h4>
              <p className="text-sm text-yellow-700">使用适当的input类型触发正确的键盘</p>
            </div>
            <div className="p-4 bg-purple-50 rounded-lg">
              <h4 className="font-medium text-purple-900 mb-1">性能优化</h4>
              <p className="text-sm text-purple-700">减少DOM操作，使用CSS动画和transform</p>
            </div>
            <div className="p-4 bg-red-50 rounded-lg">
              <h4 className="font-medium text-red-900 mb-1">视口设置</h4>
              <p className="text-sm text-red-700">正确设置viewport meta标签禁用缩放</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
