# 加载状态优化文档

## 概述

本文档描述了AIOps SRE Agent前端应用的加载状态优化方案，旨在提升用户体验和性能感知。

---

## 优化目标

1. **减少等待感知**: 通过视觉反馈减少用户等待的焦虑感
2. **提供进度信息**: 让用户了解当前操作的进度
3. **优化性能**: 减少不必要的加载时间
4. **提升一致性**: 统一全应用的加载状态样式
5. **增强可访问性**: 确保加载状态对所有用户都可感知

---

## 加载状态类型

### 1. 全局加载

#### 使用场景
- 页面初始化
- 应用启动
- 大型数据加载

#### 实现方案
```typescript
interface GlobalLoadingProps {
  message?: string;
  progress?: number;
  showProgress?: boolean;
}

const GlobalLoading: React.FC<GlobalLoadingProps> = ({
  message = '加载中...',
  progress,
  showProgress = false
}) => {
  return (
    <div className="fixed inset-0 flex items-center justify-center bg-black/50 z-50">
      <div className="bg-white rounded-lg p-8 shadow-xl">
        <LoadingSpinner size="lg" />
        <p className="mt-4 text-center text-gray-700">{message}</p>
        {showProgress && progress !== undefined && (
          <ProgressBar progress={progress} className="mt-4" />
        )}
      </div>
    </div>
  );
};
```

### 2. 局部加载

#### 使用场景
- 按钮点击
- 表单提交
- 数据刷新

#### 实现方案
```typescript
interface LocalLoadingProps {
  size?: 'sm' | 'md' | 'lg';
  inline?: boolean;
  message?: string;
}

const LocalLoading: React.FC<LocalLoadingProps> = ({
  size = 'md',
  inline = false,
  message
}) => {
  if (inline) {
    return (
      <div className="flex items-center gap-2">
        <LoadingSpinner size={size} />
        {message && <span className="text-sm text-gray-600">{message}</span>}
      </div>
    );
  }
  
  return (
    <div className="flex items-center justify-center p-4">
      <LoadingSpinner size={size} />
      {message && <p className="ml-3 text-gray-600">{message}</p>}
    </div>
  );
};
```

### 3. 骨架屏

#### 使用场景
- 列表加载
- 卡片加载
- 图表加载

#### 实现方案
```typescript
interface SkeletonProps {
  variant: 'text' | 'circular' | 'rectangular';
  width?: string | number;
  height?: string | number;
  count?: number;
  animation?: 'pulse' | 'wave' | 'none';
}

const Skeleton: React.FC<SkeletonProps> = ({
  variant = 'text',
  width = '100%',
  height = '1rem',
  count = 1,
  animation = 'pulse'
}) => {
  const baseClasses = 'bg-gray-200 rounded';
  const animationClasses = {
    pulse: 'animate-pulse',
    wave: 'animate-wave',
    none: ''
  };
  
  const variantClasses = {
    text: 'h-4',
    circular: 'rounded-full',
    rectangular: 'rounded'
  };
  
  return (
    <>
      {Array.from({ length: count }).map((_, index) => (
        <div
          key={index}
          className={`${baseClasses} ${variantClasses[variant]} ${animationClasses[animation]}`}
          style={{ width, height }}
        />
      ))}
    </>
  );
};
```

### 4. 进度条

#### 使用场景
- 文件上传
- 数据处理
- 长时间操作

#### 实现方案
```typescript
interface ProgressBarProps {
  progress: number;
  showLabel?: boolean;
  color?: 'primary' | 'success' | 'warning' | 'error';
  size?: 'sm' | 'md' | 'lg';
}

const ProgressBar: React.FC<ProgressBarProps> = ({
  progress,
  showLabel = true,
  color = 'primary',
  size = 'md'
}) => {
  const colorClasses = {
    primary: 'bg-blue-500',
    success: 'bg-green-500',
    warning: 'bg-yellow-500',
    error: 'bg-red-500'
  };
  
  const sizeClasses = {
    sm: 'h-1',
    md: 'h-2',
    lg: 'h-3'
  };
  
  return (
    <div className="w-full">
      {showLabel && (
        <div className="flex justify-between mb-1">
          <span className="text-sm font-medium text-gray-700">进度</span>
          <span className="text-sm font-medium text-gray-700">{progress}%</span>
        </div>
      )}
      <div className={`w-full bg-gray-200 rounded-full ${sizeClasses[size]}`}>
        <div
          className={`${colorClasses[color]} ${sizeClasses[size]} rounded-full transition-all duration-300`}
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
};
```

### 5. 无限滚动

#### 使用场景
- 大数据列表
- 时间线
- 消息列表

#### 实现方案
```typescript
interface InfiniteScrollProps {
  loadMore: () => Promise<void>;
  hasMore: boolean;
  loading: boolean;
  children: React.ReactNode;
}

const InfiniteScroll: React.FC<InfiniteScrollProps> = ({
  loadMore,
  hasMore,
  loading,
  children
}) => {
  const [observer, setObserver] = useState<IntersectionObserver | null>(null);
  const loaderRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    const options = {
      root: null,
      rootMargin: '20px',
      threshold: 1.0
    };
    
    const obs = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting && hasMore && !loading) {
        loadMore();
      }
    }, options);
    
    setObserver(obs);
    
    return () => {
      obs.disconnect();
    };
  }, [hasMore, loading, loadMore]);
  
  useEffect(() => {
    if (observer && loaderRef.current) {
      observer.observe(loaderRef.current);
    }
    
    return () => {
      if (observer && loaderRef.current) {
        observer.unobserve(loaderRef.current);
      }
    };
  }, [observer]);
  
  return (
    <div>
      {children}
      {hasMore && (
        <div ref={loaderRef} className="flex justify-center p-4">
          {loading ? <LoadingSpinner /> : <p>加载更多...</p>}
        </div>
      )}
    </div>
  );
};
```

---

## 加载状态最佳实践

### 1. 提供有意义的加载信息

```typescript
// ❌ 不好的做法
<LoadingSpinner />

// ✅ 好的做法
<LocalLoading message="正在分析告警数据..." />
```

### 2. 显示预估时间

```typescript
interface LoadingWithETAProps {
  startTime: number;
  estimatedDuration: number;
}

const LoadingWithETA: React.FC<LoadingWithETAProps> = ({
  startTime,
  estimatedDuration
}) => {
  const [elapsed, setElapsed] = useState(0);
  
  useEffect(() => {
    const interval = setInterval(() => {
      setElapsed(Date.now() - startTime);
    }, 100);
    
    return () => clearInterval(interval);
  }, [startTime]);
  
  const progress = Math.min((elapsed / estimatedDuration) * 100, 100);
  const remaining = Math.max(estimatedDuration - elapsed, 0);
  
  return (
    <div>
      <ProgressBar progress={progress} />
      <p className="text-sm text-gray-600 mt-2">
        预计剩余时间: {formatTime(remaining)}
      </p>
    </div>
  );
};
```

### 3. 使用骨架屏替代空白

```typescript
// ❌ 不好的做法
{loading ? <div /> : <DataList />}

// ✅ 好的做法
{loading ? <SkeletonList /> : <DataList />}
```

### 4. 提供取消操作

```typescript
interface CancellableLoadingProps {
  onCancel: () => void;
  message: string;
}

const CancellableLoading: React.FC<CancellableLoadingProps> = ({
  onCancel,
  message
}) => {
  return (
    <div className="flex items-center justify-between p-4 bg-white rounded-lg shadow">
      <div className="flex items-center gap-3">
        <LoadingSpinner />
        <span>{message}</span>
      </div>
      <Button variant="ghost" onClick={onCancel}>
        取消
      </Button>
    </div>
  );
};
```

### 5. 分阶段加载

```typescript
interface ProgressiveLoadingProps {
  stages: Array<{
    name: string;
    load: () => Promise<void>;
  }>;
}

const ProgressiveLoading: React.FC<ProgressiveLoadingProps> = ({ stages }) => {
  const [currentStage, setCurrentStage] = useState(0);
  const [completed, setCompleted] = useState<string[]>([]);
  
  useEffect(() => {
    const loadStage = async () => {
      if (currentStage < stages.length) {
        await stages[currentStage].load();
        setCompleted([...completed, stages[currentStage].name]);
        setCurrentStage(currentStage + 1);
      }
    };
    
    loadStage();
  }, [currentStage, stages, completed]);
  
  return (
    <div>
      {stages.map((stage, index) => (
        <div key={index} className="flex items-center gap-3 mb-2">
          {index < currentStage ? (
            <CheckCircle className="text-green-500" />
          ) : index === currentStage ? (
            <LoadingSpinner size="sm" />
          ) : (
            <Circle className="text-gray-300" />
          )}
          <span className={index < currentStage ? 'text-gray-700' : 'text-gray-400'}>
            {stage.name}
          </span>
        </div>
      ))}
    </div>
  );
};
```

---

## 加载状态优化策略

### 1. 预加载

```typescript
// 预加载关键数据
const usePreloadData = () => {
  useEffect(() => {
    // 预加载用户信息
    preloadUserInfo();
    // 预加载常用配置
    preloadCommonConfig();
    // 预加载最近告警
    preloadRecentAlerts();
  }, []);
};
```

### 2. 懒加载

```typescript
// 懒加载组件
const LazyComponent = React.lazy(() => import('./HeavyComponent'));

// 使用Suspense包裹
<Suspense fallback={<LoadingSpinner />}>
  <LazyComponent />
</Suspense>
```

### 3. 缓存策略

```typescript
// 使用SWR进行数据缓存
const useCachedData = (key: string, fetcher: () => Promise<any>) => {
  const { data, error, isLoading } = useSWR(key, fetcher, {
    revalidateOnFocus: false,
    revalidateOnReconnect: false,
    dedupingInterval: 60000 // 1分钟内不重复请求
  });
  
  return { data, error, isLoading };
};
```

### 4. 乐观更新

```typescript
// 乐观更新UI
const useOptimisticUpdate = () => {
  const [data, setData] = useState(initialData);
  
  const update = async (newData: any) => {
    // 立即更新UI
    const optimisticData = { ...data, ...newData };
    setData(optimisticData);
    
    try {
      // 实际更新
      await api.update(newData);
    } catch (error) {
      // 回滚UI
      setData(data);
      throw error;
    }
  };
  
  return { data, update };
};
```

### 5. 渐进式加载

```typescript
// 渐进式加载图片
const ProgressiveImage = ({ src, placeholder, alt }: any) => {
  const [imgSrc, setImgSrc] = useState(placeholder);
  
  useEffect(() => {
    const img = new Image();
    img.src = src;
    img.onload = () => setImgSrc(src);
  }, [src, placeholder]);
  
  return <img src={imgSrc} alt={alt} />;
};
```

---

## 加载状态组件库

### 基础组件

#### LoadingSpinner
```typescript
export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'md',
  color = 'currentColor',
  className = ''
}) => {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12'
  };
  
  return (
    <div className={`animate-spin ${sizeClasses[size]} ${className}`}>
      <svg className="w-full h-full" fill="none" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke={color} strokeWidth="4" />
        <path className="opacity-75" fill={color} d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
      </svg>
    </div>
  );
};
```

#### Skeleton
```typescript
export const Skeleton: React.FC<SkeletonProps> = ({
  variant = 'text',
  width = '100%',
  height = '1rem',
  count = 1,
  animation = 'pulse'
}) => {
  const baseClasses = 'bg-gray-200 rounded';
  const animationClasses = {
    pulse: 'animate-pulse',
    wave: 'animate-wave',
    none: ''
  };
  
  const variantClasses = {
    text: 'h-4',
    circular: 'rounded-full',
    rectangular: 'rounded'
  };
  
  return (
    <>
      {Array.from({ length: count }).map((_, index) => (
        <div
          key={index}
          className={`${baseClasses} ${variantClasses[variant]} ${animationClasses[animation]}`}
          style={{ width, height }}
        />
      ))}
    </>
  );
};
```

#### ProgressBar
```typescript
export const ProgressBar: React.FC<ProgressBarProps> = ({
  progress,
  showLabel = true,
  color = 'primary',
  size = 'md'
}) => {
  const colorClasses = {
    primary: 'bg-blue-500',
    success: 'bg-green-500',
    warning: 'bg-yellow-500',
    error: 'bg-red-500'
  };
  
  const sizeClasses = {
    sm: 'h-1',
    md: 'h-2',
    lg: 'h-3'
  };
  
  return (
    <div className="w-full">
      {showLabel && (
        <div className="flex justify-between mb-1">
          <span className="text-sm font-medium text-gray-700">进度</span>
          <span className="text-sm font-medium text-gray-700">{progress}%</span>
        </div>
      )}
      <div className={`w-full bg-gray-200 rounded-full ${sizeClasses[size]}`}>
        <div
          className={`${colorClasses[color]} ${sizeClasses[size]} rounded-full transition-all duration-300`}
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
};
```

### 高级组件

#### DataLoader
```typescript
interface DataLoaderProps<T> {
  loadData: () => Promise<T>;
  render: (data: T) => React.ReactNode;
  fallback?: React.ReactNode;
  error?: (error: Error) => React.ReactNode;
}

export const DataLoader = <T,>({
  loadData,
  render,
  fallback = <LoadingSpinner />,
  error: ErrorComponent
}: DataLoaderProps<T>) => {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  
  useEffect(() => {
    loadData()
      .then(setData)
      .catch(setError)
      .finally(() => setLoading(false));
  }, [loadData]);
  
  if (loading) return fallback;
  if (error) return ErrorComponent ? <ErrorComponent error={error} /> : <ErrorAlert />;
  if (data) return <>{render(data)}</>;
  
  return null;
};
```

#### AsyncButton
```typescript
interface AsyncButtonProps extends ButtonProps {
  onClick: () => Promise<void>;
  loadingText?: string;
}

export const AsyncButton: React.FC<AsyncButtonProps> = ({
  onClick,
  loadingText = '处理中...',
  children,
  ...props
}) => {
  const [loading, setLoading] = useState(false);
  
  const handleClick = async () => {
    setLoading(true);
    try {
      await onClick();
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <Button onClick={handleClick} disabled={loading} {...props}>
      {loading ? (
        <>
          <LoadingSpinner size="sm" className="mr-2" />
          {loadingText}
        </>
      ) : (
        children
      )}
    </Button>
  );
};
```

---

## 性能优化

### 1. 减少加载时间

```typescript
// 使用代码分割
const HeavyComponent = React.lazy(() => import('./HeavyComponent'));

// 使用动态导入
const loadModule = async () => {
  const module = await import('./heavyModule');
  return module.default;
};
```

### 2. 优化渲染性能

```typescript
// 使用React.memo
const MemoizedComponent = React.memo(({ data }: { data: any }) => {
  return <div>{data}</div>;
});

// 使用useMemo
const expensiveValue = useMemo(() => {
  return computeExpensiveValue(data);
}, [data]);
```

### 3. 虚拟滚动

```typescript
// 使用react-window
import { FixedSizeList } from 'react-window';

const VirtualList = ({ items }: { items: any[] }) => {
  return (
    <FixedSizeList
      height={400}
      itemCount={items.length}
      itemSize={50}
      width="100%"
    >
      {({ index, style }) => (
        <div style={style}>
          {items[index]}
        </div>
      )}
    </FixedSizeList>
  );
};
```

---

## 可访问性

### 1. ARIA属性

```typescript
// 为加载状态添加ARIA属性
<div role="status" aria-live="polite" aria-busy={loading}>
  {loading ? <LoadingSpinner /> : <Content />}
</div>
```

### 2. 屏幕阅读器支持

```typescript
// 为屏幕阅读器提供加载信息
<div aria-label="正在加载，请稍候" role="status">
  <LoadingSpinner />
  <span className="sr-only">正在加载数据...</span>
</div>
```

### 3. 键盘导航

```typescript
// 支持键盘取消加载
const CancellableLoading = ({ onCancel }: { onCancel: () => void }) => {
  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      onCancel();
    }
  };
  
  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onCancel]);
  
  return (
    <div>
      <LoadingSpinner />
      <p>按ESC取消</p>
    </div>
  );
};
```

---

## 测试策略

### 1. 单元测试

```typescript
describe('LoadingSpinner', () => {
  it('should render with default props', () => {
    render(<LoadingSpinner />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });
  
  it('should render with custom size', () => {
    render(<LoadingSpinner size="lg" />);
    const spinner = screen.getByRole('status');
    expect(spinner).toHaveClass('w-12');
  });
});
```

### 2. 集成测试

```typescript
describe('DataLoader', () => {
  it('should show loading state initially', () => {
    render(<DataLoader loadData={mockLoadData} render={mockRender} />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });
  
  it('should show data after loading', async () => {
    render(<DataLoader loadData={mockLoadData} render={mockRender} />);
    await waitFor(() => {
      expect(screen.getByText('Data loaded')).toBeInTheDocument();
    });
  });
});
```

### 3. 性能测试

```typescript
describe('Loading Performance', () => {
  it('should render skeleton within 100ms', () => {
    const start = performance.now();
    render(<Skeleton count={10} />);
    const end = performance.now();
    expect(end - start).toBeLessThan(100);
  });
});
```

---

## 监控和分析

### 1. 加载时间监控

```typescript
// 监控加载时间
const useLoadTimeMonitor = (operation: string) => {
  const startTime = useRef(Date.now());
  
  useEffect(() => {
    return () => {
      const loadTime = Date.now() - startTime.current;
      analytics.track('load_time', {
        operation,
        duration: loadTime
      });
    };
  }, [operation]);
};
```

### 2. 加载失败监控

```typescript
// 监控加载失败
const useLoadErrorMonitor = () => {
  const handleError = (error: Error) => {
    analytics.track('load_error', {
      error: error.message,
      stack: error.stack
    });
  };
  
  return { handleError };
};
```

---

**文档版本**: 1.0  
**创建日期**: 2026-08-31  
**最后更新**: 2026-08-31  
**维护团队**: AIOps SRE Agent 前端团队