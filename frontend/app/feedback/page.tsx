'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

// Skeleton组件
const Skeleton = ({ className, variant = 'default' }: { className?: string; variant?: 'default' | 'text' | 'circular' }) => {
  const baseClasses = 'animate-pulse bg-gray-200';
  const variantClasses = {
    default: 'rounded',
    text: 'rounded h-4',
    circular: 'rounded-full',
  };
  
  return (
    <div className={`${baseClasses} ${variantClasses[variant]} ${className || ''}`} />
  );
};

// Empty组件
const Empty = ({ 
  title = '暂无数据', 
  description = '这里什么都没有',
  action,
  icon 
}: { 
  title?: string; 
  description?: string; 
  action?: { label: string; onClick: () => void };
  icon?: React.ReactNode;
}) => {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4">
      {icon || (
        <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
          <span className="text-3xl">📭</span>
        </div>
      )}
      <h3 className="text-lg font-medium text-gray-900 mb-2">{title}</h3>
      <p className="text-sm text-gray-500 mb-4 text-center">{description}</p>
      {action && (
        <Button onClick={action.onClick}>{action.label}</Button>
      )}
    </div>
  );
};

export default function FeedbackPage() {
  const [loading, setLoading] = useState(true);
  const [hasData, setHasData] = useState(false);
  const [skeletonVariant, setSkeletonVariant] = useState<'default' | 'text' | 'circular'>('default');

  const toggleLoading = () => setLoading(!loading);
  const toggleData = () => setHasData(!hasData);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">反馈组件</h1>
      </div>

      {/* Skeleton骨架屏 */}
      <Card>
        <CardHeader>
          <CardTitle>Skeleton骨架屏</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex gap-2 mb-4">
            <Button 
              variant={skeletonVariant === 'default' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSkeletonVariant('default')}
            >
              默认
            </Button>
            <Button 
              variant={skeletonVariant === 'text' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSkeletonVariant('text')}
            >
              文本
            </Button>
            <Button 
              variant={skeletonVariant === 'circular' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSkeletonVariant('circular')}
            >
              圆形
            </Button>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-3">卡片骨架屏</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[1, 2, 3].map((i) => (
                <Card key={i}>
                  <CardHeader>
                    <Skeleton className="h-5 w-3/4 mb-2" variant="text" />
                    <Skeleton className="h-4 w-1/2" variant="text" />
                  </CardHeader>
                  <CardContent>
                    <Skeleton className="h-4 w-full mb-2" variant="text" />
                    <Skeleton className="h-4 w-5/6 mb-2" variant="text" />
                    <Skeleton className="h-4 w-4/6" variant="text" />
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-3">列表骨架屏</h3>
            <div className="space-y-3">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="flex items-center gap-4 p-4 border border-gray-200 rounded-lg">
                  <Skeleton className="w-12 h-12" variant={skeletonVariant} />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-4 w-1/3" variant="text" />
                    <Skeleton className="h-4 w-2/3" variant="text" />
                  </div>
                  <Skeleton className="w-20 h-8" variant="default" />
                </div>
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-3">表格骨架屏</h3>
            <div className="border border-gray-200 rounded-lg overflow-hidden">
              <div className="flex bg-gray-50 border-b p-4">
                <Skeleton className="h-4 w-1/4 mr-4" variant="text" />
                <Skeleton className="h-4 w-1/4 mr-4" variant="text" />
                <Skeleton className="h-4 w-1/4 mr-4" variant="text" />
                <Skeleton className="h-4 w-1/4" variant="text" />
              </div>
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="flex border-b p-4">
                  <Skeleton className="h-4 w-1/4 mr-4" variant="text" />
                  <Skeleton className="h-4 w-1/4 mr-4" variant="text" />
                  <Skeleton className="h-4 w-1/4 mr-4" variant="text" />
                  <Skeleton className="h-4 w-1/4" variant="text" />
                </div>
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-3">头像骨架屏</h3>
            <div className="flex items-center gap-4">
              <Skeleton className="w-10 h-10" variant="circular" />
              <Skeleton className="w-12 h-12" variant="circular" />
              <Skeleton className="w-16 h-16" variant="circular" />
              <Skeleton className="w-20 h-20" variant="circular" />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Empty空状态 */}
      <Card>
        <CardHeader>
          <CardTitle>Empty空状态</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex gap-2 mb-4">
            <Button variant="outline" size="sm" onClick={toggleData}>
              {hasData ? '显示空状态' : '显示数据'}
            </Button>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-3">基础空状态</h3>
            <div className="border border-gray-200 rounded-lg p-8">
              {hasData ? (
                <div className="text-center">
                  <p className="text-gray-600">这里有一些数据</p>
                </div>
              ) : (
                <Empty />
              )}
            </div>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-3">带描述的空状态</h3>
            <div className="border border-gray-200 rounded-lg p-8">
              {hasData ? (
                <div className="text-center">
                  <p className="text-gray-600">这里有一些数据</p>
                </div>
              ) : (
                <Empty
                  title="暂无告警"
                  description="当前没有活跃的告警，系统运行正常"
                />
              )}
            </div>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-3">带操作的空状态</h3>
            <div className="border border-gray-200 rounded-lg p-8">
              {hasData ? (
                <div className="text-center">
                  <p className="text-gray-600">这里有一些数据</p>
                </div>
              ) : (
                <Empty
                  title="暂无服务"
                  description="您还没有创建任何服务"
                  action={{
                    label: '创建服务',
                    onClick: () => alert('创建服务')
                  }}
                />
              )}
            </div>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-3">自定义图标的空状态</h3>
            <div className="border border-gray-200 rounded-lg p-8">
              {hasData ? (
                <div className="text-center">
                  <p className="text-gray-600">这里有一些数据</p>
                </div>
              ) : (
                <Empty
                  title="搜索无结果"
                  description="没有找到匹配的内容"
                  icon={<span className="text-4xl">🔍</span>}
                />
              )}
            </div>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-3">列表空状态</h3>
            <div className="border border-gray-200 rounded-lg">
              {hasData ? (
                <div className="p-4 space-y-2">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="p-3 bg-gray-50 rounded">
                      列表项 {i}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-8">
                  <Empty
                    title="暂无列表项"
                    description="列表为空"
                  />
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 使用场景 */}
      <Card>
        <CardHeader>
          <CardTitle>使用场景</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">Skeleton适用场景</h4>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• 数据加载时显示占位符</li>
                <li>• 首屏加载优化</li>
                <li>• 异步数据获取</li>
                <li>• 图片加载占位</li>
              </ul>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">Empty适用场景</h4>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• 列表无数据时</li>
                <li>• 搜索无结果时</li>
                <li>• 筛选无匹配时</li>
                <li>• 权限不足时</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 最佳实践 */}
      <Card>
        <CardHeader>
          <CardTitle>最佳实践</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="p-4 bg-blue-50 rounded-lg">
              <h4 className="font-medium text-blue-900 mb-2">Skeleton最佳实践</h4>
              <ul className="text-sm text-blue-800 space-y-1">
                <li>• 骨架屏应尽可能接近真实内容的布局</li>
                <li>• 避免过度使用，只在真正需要时使用</li>
                <li>• 加载时间较短时可以考虑直接显示内容</li>
                <li>• 使用动画效果提升用户体验</li>
              </ul>
            </div>
            <div className="p-4 bg-green-50 rounded-lg">
              <h4 className="font-medium text-green-900 mb-2">Empty最佳实践</h4>
              <ul className="text-sm text-green-800 space-y-1">
                <li>• 提供清晰的说明文字，告诉用户为什么没有数据</li>
                <li>• 提供明确的操作按钮，引导用户下一步操作</li>
                <li>• 使用友好的图标和文案，避免技术术语</li>
                <li>• 保持空状态设计的一致性</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
