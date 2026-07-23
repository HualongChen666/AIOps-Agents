'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

export default function AnimationPage() {
  const [pageTransition, setPageTransition] = useState<'fade' | 'slide' | 'scale'>('fade');
  const [dataUpdate, setDataUpdate] = useState(false);
  const [loading, setLoading] = useState(false);
  const [interaction, setInteraction] = useState(false);
  const [counter, setCounter] = useState(0);

  const triggerDataUpdate = () => {
    setDataUpdate(true);
    setTimeout(() => setDataUpdate(false), 500);
  };

  const triggerLoading = () => {
    setLoading(true);
    setTimeout(() => setLoading(false), 2000);
  };

  const triggerInteraction = () => {
    setInteraction(true);
    setTimeout(() => setInteraction(false), 300);
  };

  const incrementCounter = () => setCounter(c => c + 1);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">动画系统</h1>
      </div>

      {/* 页面转场动画 */}
      <Card>
        <CardHeader>
          <CardTitle>页面转场动画</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2 mb-4">
            <Button 
              variant={pageTransition === 'fade' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setPageTransition('fade')}
            >
              淡入淡出
            </Button>
            <Button 
              variant={pageTransition === 'slide' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setPageTransition('slide')}
            >
              滑动
            </Button>
            <Button 
              variant={pageTransition === 'scale' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setPageTransition('scale')}
            >
              缩放
            </Button>
          </div>

          <div className="border border-gray-200 rounded-lg p-8">
            <div
              className={`transition-all duration-500 ${
                pageTransition === 'fade' ? 'opacity-50' : 'opacity-100'
              }`}
            >
              <div
                className={`transition-all duration-500 ${
                  pageTransition === 'slide' ? 'translate-x-4' : 'translate-x-0'
                }`}
              >
                <div
                  className={`transition-all duration-500 ${
                    pageTransition === 'scale' ? 'scale-95' : 'scale-100'
                  }`}
                >
                  <div className="p-6 bg-blue-50 rounded-lg">
                    <h3 className="font-medium text-blue-900 mb-2">页面内容</h3>
                    <p className="text-sm text-blue-800">
                      这是一个演示页面转场动画的示例内容。
                      选择不同的动画类型查看效果。
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 数据更新动画 */}
      <Card>
        <CardHeader>
          <CardTitle>数据更新动画</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button onClick={triggerDataUpdate}>触发数据更新</Button>

          <div className="grid grid-cols-3 gap-4">
            <div
              className={`p-4 border border-gray-200 rounded-lg transition-all duration-300 ${
                dataUpdate ? 'bg-green-50 border-green-300 scale-105' : 'bg-white'
              }`}
            >
              <p className="text-2xl font-bold">42</p>
              <p className="text-sm text-gray-500">CPU使用率</p>
            </div>
            <div
              className={`p-4 border border-gray-200 rounded-lg transition-all duration-300 ${
                dataUpdate ? 'bg-blue-50 border-blue-300 scale-105' : 'bg-white'
              }`}
            >
              <p className="text-2xl font-bold">68</p>
              <p className="text-sm text-gray-500">内存使用率</p>
            </div>
            <div
              className={`p-4 border border-gray-200 rounded-lg transition-all duration-300 ${
                dataUpdate ? 'bg-purple-50 border-purple-300 scale-105' : 'bg-white'
              }`}
            >
              <p className="text-2xl font-bold">23</p>
              <p className="text-sm text-gray-500">磁盘使用率</p>
            </div>
          </div>

          <div className="p-4 border border-gray-200 rounded-lg">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm">进度条1</span>
                <span className="text-sm font-medium">75%</span>
              </div>
              <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className={`h-full bg-blue-500 transition-all duration-500 ${
                    dataUpdate ? 'w-0' : 'w-3/4'
                  }`}
                />
              </div>
            </div>
            <div className="space-y-2 mt-4">
              <div className="flex items-center justify-between">
                <span className="text-sm">进度条2</span>
                <span className="text-sm font-medium">50%</span>
              </div>
              <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className={`h-full bg-green-500 transition-all duration-500 ${
                    dataUpdate ? 'w-0' : 'w-1/2'
                  }`}
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 加载状态动画 */}
      <Card>
        <CardHeader>
          <CardTitle>加载状态动画</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button onClick={triggerLoading}>触发加载状态</Button>

          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-3">旋转加载</h4>
              {loading && (
                <div className="flex justify-center">
                  <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
                </div>
              )}
              {!loading && <p className="text-center text-gray-500">加载完成</p>}
            </div>

            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-3">脉冲加载</h4>
              {loading && (
                <div className="flex justify-center gap-2">
                  <div className="w-3 h-3 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-3 h-3 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-3 h-3 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              )}
              {!loading && <p className="text-center text-gray-500">加载完成</p>}
            </div>

            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-3">骨架屏加载</h4>
              {loading && (
                <div className="space-y-2">
                  <div className="h-4 bg-gray-200 rounded animate-pulse" />
                  <div className="h-4 bg-gray-200 rounded animate-pulse w-3/4" />
                  <div className="h-4 bg-gray-200 rounded animate-pulse w-1/2" />
                </div>
              )}
              {!loading && <p className="text-center text-gray-500">加载完成</p>}
            </div>

            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-3">进度条加载</h4>
              {loading && (
                <div className="space-y-2">
                  <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-500 animate-pulse w-full" />
                  </div>
                  <p className="text-center text-sm text-gray-500">加载中...</p>
                </div>
              )}
              {!loading && <p className="text-center text-gray-500">加载完成</p>}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 交互反馈动画 */}
      <Card>
        <CardHeader>
          <CardTitle>交互反馈动画</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-3">点击反馈</h4>
              <Button
                onClick={triggerInteraction}
                className={`w-full transition-all duration-200 ${
                  interaction ? 'scale-95 bg-blue-600' : 'scale-100'
                }`}
              >
                点击我
              </Button>
            </div>

            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-3">悬停反馈</h4>
              <Button
                className="w-full transition-all duration-200 hover:scale-105 hover:shadow-lg"
              >
                悬停我
              </Button>
            </div>

            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-3">计数器动画</h4>
              <div className="flex items-center gap-4">
                <Button onClick={incrementCounter}>增加</Button>
                <span
                  className={`text-2xl font-bold transition-all duration-300 ${
                    counter > 0 ? 'text-green-600 scale-125' : 'text-gray-900'
                  }`}
                >
                  {counter}
                </span>
              </div>
            </div>

            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-3">焦点反馈</h4>
              <input
                type="text"
                placeholder="输入框"
                className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200"
              />
            </div>
          </div>

          <div className="p-4 border border-gray-200 rounded-lg">
            <h4 className="font-medium mb-3">卡片交互</h4>
            <div className="grid grid-cols-3 gap-4">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="p-4 bg-gray-50 rounded-lg cursor-pointer transition-all duration-200 hover:scale-105 hover:shadow-md hover:bg-blue-50"
                >
                  <p className="font-medium">卡片 {i}</p>
                  <p className="text-sm text-gray-500">悬停查看效果</p>
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 动画最佳实践 */}
      <Card>
        <CardHeader>
          <CardTitle>最佳实践</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">性能优化</h4>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• 优先使用transform和opacity属性</li>
                <li>• 避免使用width、height等触发布局重排的属性</li>
                <li>• 使用will-change提示浏览器优化</li>
                <li>• 减少动画持续时间，保持流畅</li>
              </ul>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">用户体验</h4>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• 动画应该有明确的目的</li>
                <li>• 避免过度使用动画</li>
                <li>• 尊重用户的减少动画偏好设置</li>
                <li>• 提供动画禁用选项</li>
              </ul>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">可访问性</h4>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• 使用prefers-reduced-motion媒体查询</li>
                <li>• 确保动画不会引起眩晕</li>
                <li>• 为屏幕阅读器用户提供替代方案</li>
                <li>• 测试动画在不同设备上的表现</li>
              </ul>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">推荐库</h4>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• Framer Motion - React动画库</li>
                <li>• React Spring - 基于物理的动画</li>
                <li>• AutoAnimate - 自动布局动画</li>
                <li>• GSAP - 专业级动画库</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
