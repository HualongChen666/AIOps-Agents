# AIOps SRE Agent 设计系统文档

## 目录

1. [设计原则](#设计原则)
2. [色彩系统](#色彩系统)
3. [排版系统](#排版系统)
4. [间距系统](#间距系统)
5. [组件库](#组件库)
6. [交互模式](#交互模式)
7. [响应式设计](#响应式设计)
8. [无障碍设计](#无障碍设计)
9. [主题系统](#主题系统)
10. [图标系统](#图标系统)

---

## 设计原则

### 核心原则

1. **一致性**: 整个应用保持统一的视觉和交互模式
2. **可访问性**: 确保所有用户都能使用应用
3. **性能**: 优化加载和渲染性能
4. **可维护性**: 设计系统易于维护和扩展
5. **用户中心**: 以用户需求为中心进行设计

### 设计价值观

- **简洁**: 去除不必要的元素，保持界面简洁
- **清晰**: 信息层次清晰，易于理解
- **高效**: 用户能够快速完成任务
- **美观**: 视觉设计专业且现代

---

## 色彩系统

### 主色调

```css
/* 主色 - 蓝色系 */
--primary-50: #eff6ff;
--primary-100: #dbeafe;
--primary-200: #bfdbfe;
--primary-300: #93c5fd;
--primary-400: #60a5fa;
--primary-500: #3b82f6;  /* 主色 */
--primary-600: #2563eb;
--primary-700: #1d4ed8;
--primary-800: #1e40af;
--primary-900: #1e3a8a;
```

### 功能色

```css
/* 成功色 - 绿色系 */
--success-50: #f0fdf4;
--success-100: #dcfce7;
--success-200: #bbf7d0;
--success-300: #86efac;
--success-400: #4ade80;
--success-500: #22c55e;  /* 成功色 */
--success-600: #16a34a;
--success-700: #15803d;
--success-800: #166534;
--success-900: #14532d;

/* 警告色 - 黄色系 */
--warning-50: #fefce8;
--warning-100: #fef9c3;
--warning-200: #fef08a;
--warning-300: #fde047;
--warning-400: #facc15;
--warning-500: #eab308;  /* 警告色 */
--warning-600: #ca8a04;
--warning-700: #a16207;
--warning-800: #854d0e;
--warning-900: #713f12;

/* 错误色 - 红色系 */
--error-50: #fef2f2;
--error-100: #fee2e2;
--error-200: #fecaca;
--error-300: #fca5a5;
--error-400: #f87171;
--error-500: #ef4444;  /* 错误色 */
--error-600: #dc2626;
--error-700: #b91c1c;
--error-800: #991b1b;
--error-900: #7f1d1d;

/* 信息色 - 青色系 */
--info-50: #ecfeff;
--info-100: #cffafe;
--info-200: #a5f3fc;
--info-300: #67e8f9;
--info-400: #22d3ee;
--info-500: #06b6d4;  /* 信息色 */
--info-600: #0891b2;
--info-700: #0e7490;
--info-800: #155e75;
--info-900: #164e63;
```

### 中性色

```css
/* 灰色系 */
--gray-50: #f9fafb;
--gray-100: #f3f4f6;
--gray-200: #e5e7eb;
--gray-300: #d1d5db;
--gray-400: #9ca3af;
--gray-500: #6b7280;
--gray-600: #4b5563;
--gray-700: #374151;
--gray-800: #1f2937;
--gray-900: #111827;
```

### 色彩使用指南

- **主色**: 用于主要操作、重要信息、品牌元素
- **成功色**: 用于成功状态、完成操作
- **警告色**: 用于警告状态、需要注意的信息
- **错误色**: 用于错误状态、失败操作
- **信息色**: 用于信息提示、帮助信息
- **中性色**: 用于文本、边框、背景等

---

## 排版系统

### 字体家族

```css
/* 主字体 */
--font-family-base: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;

/* 等宽字体 */
--font-family-mono: 'JetBrains Mono', 'Fira Code', Consolas, 'Courier New', monospace;

/* 标题字体 */
--font-family-heading: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
```

### 字体大小

```css
/* 字体大小 */
--text-xs: 0.75rem;      /* 12px */
--text-sm: 0.875rem;     /* 14px */
--text-base: 1rem;       /* 16px */
--text-lg: 1.125rem;     /* 18px */
--text-xl: 1.25rem;      /* 20px */
--text-2xl: 1.5rem;      /* 24px */
--text-3xl: 1.875rem;    /* 30px */
--text-4xl: 2.25rem;     /* 36px */
--text-5xl: 3rem;        /* 48px */
--text-6xl: 3.75rem;     /* 60px */
```

### 字重

```css
/* 字重 */
--font-light: 300;
--font-normal: 400;
--font-medium: 500;
--font-semibold: 600;
--font-bold: 700;
--font-extrabold: 800;
```

### 行高

```css
/* 行高 */
--leading-none: 1;
--leading-tight: 1.25;
--leading-snug: 1.375;
--leading-normal: 1.5;
--leading-relaxed: 1.625;
--leading-loose: 2;
```

### 排版使用指南

- **标题**: 使用更大的字体和更粗的字重
- **正文**: 使用基础字体大小和正常字重
- **辅助文本**: 使用较小的字体和较浅的颜色
- **代码**: 使用等宽字体
- **强调**: 使用加粗或颜色变化

---

## 间距系统

### 基础间距

```css
/* 间距单位 */
--space-0: 0;
--space-1: 0.25rem;   /* 4px */
--space-2: 0.5rem;    /* 8px */
--space-3: 0.75rem;   /* 12px */
--space-4: 1rem;      /* 16px */
--space-5: 1.25rem;   /* 20px */
--space-6: 1.5rem;    /* 24px */
--space-8: 2rem;      /* 32px */
--space-10: 2.5rem;   /* 40px */
--space-12: 3rem;     /* 48px */
--space-16: 4rem;     /* 64px */
--space-20: 5rem;     /* 80px */
--space-24: 6rem;     /* 96px */
```

### 间距使用指南

- **紧密元素**: 使用 space-1 到 space-2
- **正常间距**: 使用 space-3 到 space-4
- **宽松间距**: 使用 space-6 到 space-8
- **大间距**: 使用 space-12 到 space-16
- **特大间距**: 使用 space-20 到 space-24

---

## 组件库

### 基础组件

#### 按钮

```typescript
interface ButtonProps {
  variant: 'primary' | 'secondary' | 'outline' | 'ghost';
  size: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  loading?: boolean;
  icon?: React.ReactNode;
  children: React.ReactNode;
}
```

#### 输入框

```typescript
interface InputProps {
  type: 'text' | 'email' | 'password' | 'number';
  size: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  error?: boolean;
  placeholder?: string;
  value: string;
  onChange: (value: string) => void;
}
```

#### 卡片

```typescript
interface CardProps {
  variant: 'default' | 'elevated' | 'outlined';
  padding?: 'sm' | 'md' | 'lg';
  children: React.ReactNode;
}
```

### 业务组件

#### 告警卡片

```typescript
interface AlertCardProps {
  severity: 'critical' | 'high' | 'medium' | 'low';
  title: string;
  description: string;
  timestamp: string;
  actions?: React.ReactNode;
}
```

#### 仪表板卡片

```typescript
interface DashboardCardProps {
  title: string;
  value: string | number;
  trend?: 'up' | 'down' | 'stable';
  trendValue?: string;
  icon?: React.ReactNode;
}
```

#### 拓扑图

```typescript
interface TopologyGraphProps {
  nodes: Node[];
  edges: Edge[];
  onNodeClick?: (node: Node) => void;
  onEdgeClick?: (edge: Edge) => void;
}
```

---

## 交互模式

### 加载状态

#### 骨架屏

```typescript
interface SkeletonProps {
  variant: 'text' | 'circular' | 'rectangular';
  width?: string | number;
  height?: string | number;
  animation?: 'pulse' | 'wave' | 'none';
}
```

#### 加载指示器

```typescript
interface LoadingSpinnerProps {
  size: 'sm' | 'md' | 'lg';
  color?: string;
  message?: string;
}
```

### 错误处理

#### 错误边界

```typescript
interface ErrorBoundaryProps {
  fallback: React.ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  children: React.ReactNode;
}
```

#### 错误提示

```typescript
interface ErrorAlertProps {
  title: string;
  message: string;
  onRetry?: () => void;
  onDismiss?: () => void;
}
```

### 表单验证

#### 验证规则

```typescript
interface ValidationRule {
  required?: boolean;
  minLength?: number;
  maxLength?: number;
  pattern?: RegExp;
  custom?: (value: any) => boolean | string;
}
```

#### 表单状态

```typescript
interface FormState {
  values: Record<string, any>;
  errors: Record<string, string>;
  touched: Record<string, boolean>;
  isValid: boolean;
  isDirty: boolean;
}
```

---

## 响应式设计

### 断点系统

```css
/* 断点 */
--breakpoint-sm: 640px;   /* 小屏幕 */
--breakpoint-md: 768px;   /* 中等屏幕 */
--breakpoint-lg: 1024px;  /* 大屏幕 */
--breakpoint-xl: 1280px;  /* 超大屏幕 */
--breakpoint-2xl: 1536px; /* 超超大屏幕 */
```

### 响应式策略

- **移动优先**: 从小屏幕开始设计，逐步增强
- **弹性布局**: 使用flexbox和grid布局
- **相对单位**: 使用rem、em、vw、vh等相对单位
- **图片优化**: 使用响应式图片和懒加载

---

## 无障碍设计

### WCAG 2.1 AA标准

- **色彩对比度**: 文本对比度至少4.5:1，大文本至少3:1
- **键盘导航**: 所有功能都可以通过键盘访问
- **屏幕阅读器**: 提供适当的ARIA属性
- **焦点管理**: 清晰的焦点指示器和合理的焦点顺序

### ARIA属性

```typescript
// 常用ARIA属性
aria-label: string;           // 元素标签
aria-describedby: string;     // 描述信息
aria-invalid: boolean;        // 验证状态
aria-expanded: boolean;       // 展开状态
aria-hidden: boolean;         // 隐藏状态
role: string;                 // 元素角色
```

---

## 主题系统

### 亮色主题

```css
:root {
  --bg-primary: #ffffff;
  --bg-secondary: #f3f4f6;
  --bg-tertiary: #e5e7eb;
  --text-primary: #111827;
  --text-secondary: #6b7280;
  --text-tertiary: #9ca3af;
  --border-color: #e5e7eb;
  --shadow-color: rgba(0, 0, 0, 0.1);
}
```

### 暗色主题

```css
[data-theme="dark"] {
  --bg-primary: #111827;
  --bg-secondary: #1f2937;
  --bg-tertiary: #374151;
  --text-primary: #f9fafb;
  --text-secondary: #d1d5db;
  --text-tertiary: #9ca3af;
  --border-color: #374151;
  --shadow-color: rgba(0, 0, 0, 0.3);
}
```

### 主题切换

```typescript
interface ThemeProviderProps {
  defaultTheme: 'light' | 'dark';
  storageKey?: string;
  children: React.ReactNode;
}
```

---

## 图标系统

### 图标库

- **主图标库**: Lucide React
- **备用图标库**: Heroicons
- **自定义图标**: SVG格式

### 图标尺寸

```css
--icon-xs: 0.75rem;   /* 12px */
--icon-sm: 1rem;      /* 16px */
--icon-md: 1.25rem;   /* 20px */
--icon-lg: 1.5rem;    /* 24px */
--icon-xl: 2rem;      /* 32px */
--icon-2xl: 2.5rem;   /* 40px */
```

### 图标使用指南

- **一致性**: 使用统一的图标风格
- **语义化**: 选择符合功能的图标
- **尺寸**: 根据上下文选择合适的尺寸
- **颜色**: 遵循色彩系统的规范

---

## 使用指南

### 组件使用示例

```typescript
// 按钮组件
<Button variant="primary" size="md" loading={isLoading}>
  提交
</Button>

// 输入框组件
<Input
  type="email"
  size="md"
  placeholder="请输入邮箱"
  value={email}
  onChange={setEmail}
  error={hasError}
/>

// 卡片组件
<Card variant="elevated" padding="md">
  <h3>标题</h3>
  <p>内容</p>
</Card>
```

### 样式使用示例

```css
/* 使用设计系统变量 */
.button {
  background-color: var(--primary-500);
  color: var(--text-primary);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  font-size: var(--text-base);
  font-weight: var(--font-medium);
}
```

---

## 维护指南

### 版本控制

- 使用语义化版本控制
- 记录每次变更的内容
- 提供迁移指南

### 文档更新

- 及时更新设计系统文档
- 提供使用示例和最佳实践
- 维护变更日志

### 组件生命周期

- 定期审查组件使用情况
- 移除不常用的组件
- 优化常用组件的性能

---

**文档版本**: 1.0  
**创建日期**: 2026-08-31  
**最后更新**: 2026-08-31  
**维护团队**: AIOps SRE Agent 前端团队