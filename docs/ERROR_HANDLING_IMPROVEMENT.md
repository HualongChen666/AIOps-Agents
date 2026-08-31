# 错误提示改进文档

## 概述

本文档描述了AIOps SRE Agent前端应用的错误提示改进方案，旨在提升用户体验和错误处理能力。

---

## 优化目标

1. **清晰的错误信息**: 提供用户能理解的错误描述
2. **可操作的解决方案**: 为每个错误提供解决建议
3. **一致的错误样式**: 统一全应用的错误提示样式
4. **友好的错误语气**: 使用友好的语言，避免技术术语
5. **智能错误恢复**: 提供自动或半自动的错误恢复机制

---

## 错误类型分类

### 1. 网络错误

#### 错误场景
- 网络连接失败
- 请求超时
- 服务器无响应

#### 错误提示
```typescript
interface NetworkErrorProps {
  error: Error;
  onRetry?: () => void;
  onOfflineMode?: () => void;
}

const NetworkError: React.FC<NetworkErrorProps> = ({
  error,
  onRetry,
  onOfflineMode
}) => {
  const isOffline = !navigator.onLine;
  
  return (
    <Alert variant="error" className="mb-4">
      <AlertCircle className="h-5 w-5" />
      <AlertTitle>网络连接错误</AlertTitle>
      <AlertDescription>
        {isOffline 
          ? '当前网络不可用，请检查网络连接后重试。'
          : '无法连接到服务器，请稍后重试。'
        }
      </AlertDescription>
      <div className="mt-4 flex gap-2">
        {onRetry && (
          <Button size="sm" onClick={onRetry}>
            重试
          </Button>
        )}
        {onOfflineMode && (
          <Button size="sm" variant="outline" onClick={onOfflineMode}>
            离线模式
          </Button>
        )}
      </div>
    </Alert>
  );
};
```

### 2. 验证错误

#### 错误场景
- 表单验证失败
- 数据格式错误
- 必填字段缺失

#### 错误提示
```typescript
interface ValidationErrorProps {
  field: string;
  message: string;
  onFix?: () => void;
}

const ValidationError: React.FC<ValidationErrorProps> = ({
  field,
  message,
  onFix
}) => {
  return (
    <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-md">
      <AlertCircle className="h-5 w-5 text-red-500 mt-0.5" />
      <div className="flex-1">
        <p className="font-medium text-red-800">{field}验证失败</p>
        <p className="text-sm text-red-600 mt-1">{message}</p>
        {onFix && (
          <Button 
            size="sm" 
            variant="link" 
            className="mt-2 p-0 h-auto text-red-700"
            onClick={onFix}
          >
            修复此问题
          </Button>
        )}
      </div>
    </div>
  );
};
```

### 3. 权限错误

#### 错误场景
- 用户无权限访问
- 会话过期
- 令牌无效

#### 错误提示
```typescript
interface PermissionErrorProps {
  action: string;
  resource: string;
  onLogin?: () => void;
  onRequestPermission?: () => void;
}

const PermissionError: React.FC<PermissionErrorProps> = ({
  action,
  resource,
  onLogin,
  onRequestPermission
}) => {
  return (
    <Alert variant="warning" className="mb-4">
      <Lock className="h-5 w-5" />
      <AlertTitle>权限不足</AlertTitle>
      <AlertDescription>
        您没有权限{action} {resource}。请联系管理员获取相应权限。
      </AlertDescription>
      <div className="mt-4 flex gap-2">
        {onLogin && (
          <Button size="sm" onClick={onLogin}>
            重新登录
          </Button>
        )}
        {onRequestPermission && (
          <Button size="sm" variant="outline" onClick={onRequestPermission}>
            申请权限
          </Button>
        )}
      </div>
    </Alert>
  );
};
```

### 4. 服务器错误

#### 错误场景
- 服务器内部错误
- 服务不可用
- 数据库错误

#### 错误提示
```typescript
interface ServerErrorProps {
  error: Error;
  onReport?: () => void;
  onContactSupport?: () => void;
}

const ServerError: React.FC<ServerErrorProps> = ({
  error,
  onReport,
  onContactSupport
}) => {
  const errorId = generateErrorId();
  
  return (
    <Alert variant="error" className="mb-4">
      <Server className="h-5 w-5" />
      <AlertTitle>服务器错误</AlertTitle>
      <AlertDescription>
        服务器处理请求时发生错误。错误ID: {errorId}
      </AlertDescription>
      <div className="mt-4 flex gap-2">
        {onReport && (
          <Button size="sm" onClick={() => onReport()}>
            报告问题
          </Button>
        )}
        {onContactSupport && (
          <Button size="sm" variant="outline" onClick={onContactSupport}>
            联系支持
          </Button>
        )}
      </div>
    </Alert>
  );
};
```

### 5. 数据错误

#### 错误场景
- 数据格式错误
- 数据损坏
- 数据不一致

#### 错误提示
```typescript
interface DataErrorProps {
  dataType: string;
  error: Error;
  onRefresh?: () => void;
  onRecover?: () => void;
}

const DataError: React.FC<DataErrorProps> = ({
  dataType,
  error,
  onRefresh,
  onRecover
}) => {
  return (
    <Alert variant="warning" className="mb-4">
      <Database className="h-5 w-5" />
      <AlertTitle>数据错误</AlertTitle>
      <AlertDescription>
        {dataType}数据存在问题，无法正常显示。
      </AlertDescription>
      <div className="mt-4 flex gap-2">
        {onRefresh && (
          <Button size="sm" onClick={onRefresh}>
            刷新数据
          </Button>
        )}
        {onRecover && (
          <Button size="sm" variant="outline" onClick={onRecover}>
            数据恢复
          </Button>
        )}
      </div>
    </Alert>
  );
};
```

---

## 错误提示组件

### 基础组件

#### ErrorAlert
```typescript
interface ErrorAlertProps {
  title: string;
  message: string;
  variant?: 'error' | 'warning' | 'info';
  dismissible?: boolean;
  onDismiss?: () => void;
  actions?: React.ReactNode;
}

export const ErrorAlert: React.FC<ErrorAlertProps> = ({
  title,
  message,
  variant = 'error',
  dismissible = true,
  onDismiss,
  actions
}) => {
  const icons = {
    error: <AlertCircle className="h-5 w-5" />,
    warning: <AlertTriangle className="h-5 w-5" />,
    info: <Info className="h-5 w-5" />
  };
  
  return (
    <Alert variant={variant} className="mb-4">
      {icons[variant]}
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription>{message}</AlertDescription>
      {actions && <div className="mt-4">{actions}</div>}
      {dismissible && onDismiss && (
        <Button 
          size="sm" 
          variant="ghost" 
          className="absolute top-2 right-2"
          onClick={onDismiss}
        >
          <X className="h-4 w-4" />
        </Button>
      )}
    </Alert>
  );
};
```

#### ErrorBoundary
```typescript
interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends React.Component<
  { children: React.ReactNode; fallback?: React.ReactNode },
  ErrorBoundaryState
> {
  constructor(props: any) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null
    };
  }
  
  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return {
      hasError: true,
      error,
      errorInfo: null
    };
  }
  
  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({
      error,
      errorInfo
    });
    
    // 记录错误
    logErrorToService(error, errorInfo);
  }
  
  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      
      return (
        <div className="p-8 text-center">
          <AlertCircle className="h-16 w-16 mx-auto text-red-500 mb-4" />
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            出现了错误
          </h2>
          <p className="text-gray-600 mb-4">
            应用遇到了意外错误，请刷新页面重试。
          </p>
          <Button onClick={() => window.location.reload()}>
            刷新页面
          </Button>
        </div>
      );
    }
    
    return this.props.children;
  }
}
```

### 高级组件

#### ErrorHandler
```typescript
interface ErrorHandlerProps {
  error: Error;
  context?: string;
  onRetry?: () => void;
  onReport?: () => void;
}

export const ErrorHandler: React.FC<ErrorHandlerProps> = ({
  error,
  context = '操作',
  onRetry,
  onReport
}) => {
  const errorType = classifyError(error);
  const errorMessage = getErrorMessage(error, errorType);
  const solution = getErrorSolution(errorType);
  
  return (
    <div className="p-6 bg-white rounded-lg shadow-md">
      <div className="flex items-start gap-4">
        <div className="flex-shrink-0">
          {getErrorIcon(errorType)}
        </div>
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            {context}失败
          </h3>
          <p className="text-gray-600 mb-4">{errorMessage}</p>
          
          {solution && (
            <div className="mb-4 p-4 bg-blue-50 rounded-md">
              <h4 className="font-medium text-blue-900 mb-2">解决方案</h4>
              <p className="text-sm text-blue-700">{solution}</p>
            </div>
          )}
          
          <div className="flex gap-2">
            {onRetry && (
              <Button size="sm" onClick={onRetry}>
                重试
              </Button>
            )}
            {onReport && (
              <Button size="sm" variant="outline" onClick={onReport}>
                报告问题
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
```

#### ToastError
```typescript
interface ToastErrorProps {
  title: string;
  message: string;
  duration?: number;
  onDismiss?: () => void;
}

export const ToastError: React.FC<ToastErrorProps> = ({
  title,
  message,
  duration = 5000,
  onDismiss
}) => {
  useEffect(() => {
    const timer = setTimeout(() => {
      onDismiss?.();
    }, duration);
    
    return () => clearTimeout(timer);
  }, [duration, onDismiss]);
  
  return (
    <div className="flex items-start gap-3 p-4 bg-white border border-red-200 rounded-lg shadow-lg">
      <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
      <div className="flex-1">
        <p className="font-medium text-red-900">{title}</p>
        <p className="text-sm text-red-700 mt-1">{message}</p>
      </div>
      <Button 
        size="sm" 
        variant="ghost" 
        className="flex-shrink-0"
        onClick={onDismiss}
      >
        <X className="h-4 w-4" />
      </Button>
    </div>
  );
};
```

---

## 错误处理最佳实践

### 1. 错误分类

```typescript
const classifyError = (error: Error): ErrorType => {
  if (error instanceof NetworkError) return 'network';
  if (error instanceof ValidationError) return 'validation';
  if (error instanceof PermissionError) return 'permission';
  if (error instanceof ServerError) return 'server';
  if (error instanceof DataError) return 'data';
  return 'unknown';
};
```

### 2. 错误消息本地化

```typescript
const getErrorMessage = (error: Error, type: ErrorType): string => {
  const messages = {
    network: t('errors.network.message'),
    validation: t('errors.validation.message'),
    permission: t('errors.permission.message'),
    server: t('errors.server.message'),
    data: t('errors.data.message'),
    unknown: t('errors.unknown.message')
  };
  
  return messages[type] || t('errors.unknown.message');
};
```

### 3. 错误恢复策略

```typescript
const getErrorSolution = (type: ErrorType): string => {
  const solutions = {
    network: '请检查网络连接，然后重试。',
    validation: '请检查输入信息，确保格式正确。',
    permission: '请联系管理员获取相应权限。',
    server: '请稍后重试，如果问题持续存在，请联系技术支持。',
    data: '请刷新数据或联系技术支持。',
    unknown: '请刷新页面重试，如果问题持续存在，请联系技术支持。'
  };
  
  return solutions[type] || solutions.unknown;
};
```

### 4. 错误日志记录

```typescript
const logErrorToService = (error: Error, errorInfo?: ErrorInfo) => {
  const errorData = {
    message: error.message,
    stack: error.stack,
    componentStack: errorInfo?.componentStack,
    timestamp: new Date().toISOString(),
    userAgent: navigator.userAgent,
    url: window.location.href
  };
  
  // 发送到错误监控服务
  errorMonitoringService.log(errorData);
};
```

### 5. 错误恢复机制

```typescript
const useErrorRecovery = () => {
  const [error, setError] = useState<Error | null>(null);
  const [isRecovering, setIsRecovering] = useState(false);
  
  const recover = async () => {
    setIsRecovering(true);
    try {
      // 执行恢复操作
      await performRecovery(error);
      setError(null);
    } catch (recoveryError) {
      setError(recoveryError as Error);
    } finally {
      setIsRecovering(false);
    }
  };
  
  return { error, isRecovering, recover, setError };
};
```

---

## 错误提示样式

### 颜色系统

```css
/* 错误色 */
--error-bg: #fef2f2;
--error-border: #fecaca;
--error-text: #991b1b;
--error-icon: #dc2626;

/* 警告色 */
--warning-bg: #fefce8;
--warning-border: #fef9c3;
--warning-text: #854d0e;
--warning-icon: #ca8a04;

/* 信息色 */
--info-bg: #ecfeff;
--info-border: #cffafe;
--info-text: #155e75;
--info-icon: #0891b2;
```

### 动画效果

```css
/* 错误提示动画 */
@keyframes slideIn {
  from {
    transform: translateY(-100%);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

@keyframes shake {
  0%, 100% {
    transform: translateX(0);
  }
  10%, 30%, 50%, 70%, 90% {
    transform: translateX(-5px);
  }
  20%, 40%, 60%, 80% {
    transform: translateX(5px);
  }
}

.error-alert {
  animation: slideIn 0.3s ease-out;
}

.error-shake {
  animation: shake 0.5s ease-in-out;
}
```

---

## 可访问性

### 1. ARIA属性

```typescript
<div
  role="alert"
  aria-live="assertive"
  aria-atomic="true"
  aria-label={title}
>
  <ErrorAlert title={title} message={message} />
</div>
```

### 2. 键盘导航

```typescript
const ErrorAlertWithKeyboard = ({ onDismiss }: { onDismiss: () => void }) => {
  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      onDismiss();
    }
  };
  
  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onDismiss]);
  
  return (
    <ErrorAlert 
      title="错误" 
      message="发生了错误" 
      onDismiss={onDismiss}
    />
  );
};
```

### 3. 屏幕阅读器支持

```typescript
<div aria-live="polite" aria-atomic="true">
  <span className="sr-only">错误提示已显示</span>
  <ErrorAlert title="错误" message="发生了错误" />
</div>
```

---

## 测试策略

### 1. 单元测试

```typescript
describe('ErrorAlert', () => {
  it('should render error message', () => {
    render(<ErrorAlert title="错误" message="测试错误" />);
    expect(screen.getByText('测试错误')).toBeInTheDocument();
  });
  
  it('should call onDismiss when dismissed', () => {
    const onDismiss = jest.fn();
    render(<ErrorAlert title="错误" message="测试错误" onDismiss={onDismiss} />);
    
    const dismissButton = screen.getByRole('button');
    fireEvent.click(dismissButton);
    
    expect(onDismiss).toHaveBeenCalled();
  });
});
```

### 2. 集成测试

```typescript
describe('Error Handling Integration', () => {
  it('should show error boundary when component crashes', () => {
    render(
      <ErrorBoundary>
        <CrashingComponent />
      </ErrorBoundary>
    );
    
    expect(screen.getByText('出现了错误')).toBeInTheDocument();
  });
});
```

### 3. E2E测试

```typescript
test('error recovery flow', async ({ page }) => {
  await page.goto('/dashboard');
  
  // 触发错误
  await page.click('#trigger-error');
  
  // 验证错误提示显示
  await expect(page.locator('.error-alert')).toBeVisible();
  
  // 点击重试
  await page.click('#retry-button');
  
  // 验证错误消失
  await expect(page.locator('.error-alert')).not.toBeVisible();
});
```

---

## 监控和分析

### 1. 错误率监控

```typescript
const useErrorMonitoring = () => {
  const [errorRate, setErrorRate] = useState(0);
  
  useEffect(() => {
    const interval = setInterval(() => {
      const rate = calculateErrorRate();
      setErrorRate(rate);
    }, 60000); // 每分钟更新
    
    return () => clearInterval(interval);
  }, []);
  
  return { errorRate };
};
```

### 2. 错误趋势分析

```typescript
const analyzeErrorTrends = (errors: Error[]): ErrorTrend => {
  const errorTypes = errors.map(e => classifyError(e));
  const typeCounts = errorTypes.reduce((acc, type) => {
    acc[type] = (acc[type] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);
  
  return {
    total: errors.length,
    byType: typeCounts,
    mostCommon: Object.entries(typeCounts).sort((a, b) => b[1] - a[1])[0]
  };
};
```

---

**文档版本**: 1.0  
**创建日期**: 2026-08-31  
**最后更新**: 2026-08-31  
**维护团队**: AIOps SRE Agent 前端团队