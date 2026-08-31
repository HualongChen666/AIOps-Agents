# 移动端优化文档

## 概述

本文档描述了AIOps SRE Agent前端应用的移动端优化方案，旨在提升移动设备的用户体验和性能。

---

## 优化目标

1. **响应式设计**: 确保应用在各种设备尺寸上都能正常显示
2. **触摸优化**: 优化触摸交互，提升移动设备操作体验
3. **性能优化**: 减少移动设备上的加载时间和资源消耗
4. **可访问性**: 确保移动设备上的可访问性符合标准
5. **用户体验**: 提供流畅的移动端用户体验

---

## 响应式设计策略

### 断点系统

```css
/* 移动端断点 */
--breakpoint-xs: 320px;   /* 小型手机 */
--breakpoint-sm: 375px;   /* 标准手机 */
--breakpoint-md: 768px;   /* 平板 */
--breakpoint-lg: 1024px;  /* 桌面 */
--breakpoint-xl: 1280px;  /* 大屏幕 */
--breakpoint-2xl: 1536px; /* 超大屏幕 */
```

### 响应式布局

#### 移动优先策略
```css
/* 基础样式（移动端） */
.container {
  padding: 1rem;
  width: 100%;
}

/* 平板设备 */
@media (min-width: 768px) {
  .container {
    padding: 2rem;
    max-width: 768px;
    margin: 0 auto;
  }
}

/* 桌面设备 */
@media (min-width: 1024px) {
  .container {
    padding: 3rem;
    max-width: 1024px;
  }
}
```

#### 弹性布局
```css
/* 使用Flexbox进行弹性布局 */
.flex-container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

@media (min-width: 768px) {
  .flex-container {
    flex-direction: row;
    flex-wrap: wrap;
  }
}
```

#### 网格布局
```css
/* 使用Grid进行网格布局 */
.grid-container {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
}

@media (min-width: 768px) {
  .grid-container {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (min-width: 1024px) {
  .grid-container {
    grid-template-columns: repeat(3, 1fr);
  }
}
```

### 图片优化

#### 响应式图片
```html
<picture>
  <source media="(max-width: 640px)" srcset="image-small.jpg">
  <source media="(max-width: 1024px)" srcset="image-medium.jpg">
  <img src="image-large.jpg" alt="Responsive image" loading="lazy">
</picture>
```

#### 图片懒加载
```html
<img 
  src="placeholder.jpg" 
  data-src="actual-image.jpg" 
  alt="Lazy loaded image" 
  loading="lazy"
  class="lazy-image"
>
```

#### WebP格式
```html
<picture>
  <source type="image/webp" srcset="image.webp">
  <img src="image.jpg" alt="Optimized image">
</picture>
```

---

## 触摸交互优化

### 触摸目标尺寸

#### 最小触摸目标
```css
/* 最小触摸目标尺寸 44x44px */
.touch-target {
  min-width: 44px;
  min-height: 44px;
  padding: 12px;
}
```

#### 间距优化
```css
/* 触摸目标之间的间距 */
.touch-target {
  margin: 8px;
}

/* 按钮组间距 */
.button-group {
  gap: 16px;
}
```

### 触摸反馈

#### 视觉反馈
```css
/* 按下状态 */
.button:active {
  transform: scale(0.95);
  opacity: 0.8;
}

/* 悬停状态（仅桌面） */
@media (hover: hover) {
  .button:hover {
    background-color: var(--primary-hover);
  }
}
```

#### 触摸优化
```css
/* 减少点击延迟 */
.button {
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}

/* 防止双击缩放 */
.button {
  touch-action: manipulation;
}
```

### 手势支持

#### 滑动手势
```typescript
// 滑动手势检测
const useSwipe = (callback: (direction: 'left' | 'right') => void) => {
  const [touchStart, setTouchStart] = useState(0);
  const [touchEnd, setTouchEnd] = useState(0);

  const onTouchStart = (e: TouchEvent) => {
    setTouchEnd(e.targetTouches[0].clientX);
    setTouchStart(e.targetTouches[0].clientX);
  };

  const onTouchMove = (e: TouchEvent) => {
    setTouchEnd(e.targetTouches[0].clientX);
  };

  const onTouchEnd = () => {
    const distance = touchStart - touchEnd;
    const isLeftSwipe = distance > 50;
    const isRightSwipe = distance < -50;

    if (isLeftSwipe) {
      callback('left');
    } else if (isRightSwipe) {
      callback('right');
    }
  };

  return {
    onTouchStart,
    onTouchMove,
    onTouchEnd
  };
};
```

#### 捏合缩放
```typescript
// 捏合缩放检测
const usePinch = (callback: (scale: number) => void) => {
  const [initialDistance, setInitialDistance] = useState(0);

  const onTouchStart = (e: TouchEvent) => {
    if (e.touches.length === 2) {
      const distance = Math.hypot(
        e.touches[0].clientX - e.touches[1].clientX,
        e.touches[0].clientY - e.touches[1].clientY
      );
      setInitialDistance(distance);
    }
  };

  const onTouchMove = (e: TouchEvent) => {
    if (e.touches.length === 2) {
      const distance = Math.hypot(
        e.touches[0].clientX - e.touches[1].clientX,
        e.touches[0].clientY - e.touches[1].clientY
      );
      const scale = distance / initialDistance;
      callback(scale);
    }
  };

  return {
    onTouchStart,
    onTouchMove
  };
};
```

---

## 移动端性能优化

### 资源优化

#### 代码分割
```typescript
// 动态导入组件
const HeavyComponent = React.lazy(() => import('./HeavyComponent'));

// 路由级别代码分割
const Dashboard = React.lazy(() => import('./pages/Dashboard'));
const Settings = React.lazy(() => import('./pages/Settings'));
```

#### 懒加载
```typescript
// 图片懒加载
const LazyImage = ({ src, alt }: { src: string; alt: string }) => {
  const [isLoaded, setIsLoaded] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setIsLoaded(true);
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.1 }
    );

    if (imgRef.current) {
      observer.observe(imgRef.current);
    }

    return () => observer.disconnect();
  }, []);

  return (
    <img
      ref={imgRef}
      src={isLoaded ? src : 'placeholder.jpg'}
      alt={alt}
      loading="lazy"
    />
  );
};
```

#### 虚拟滚动
```typescript
// 虚拟滚动组件
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

### 网络优化

#### HTTP/2
```nginx
# Nginx配置
server {
    listen 443 ssl http2;
    # 其他配置
}
```

#### 缓存策略
```typescript
// Service Worker缓存
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open('v1').then((cache) => {
      return cache.addAll([
        '/',
        '/styles/main.css',
        '/scripts/main.js'
      ]);
    })
  );
});

self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request);
    })
  );
});
```

#### 预加载
```html
<!-- 预加载关键资源 -->
<link rel="preload" href="critical.css" as="style">
<link rel="preload" href="critical.js" as="script">
<link rel="preconnect" href="https://api.example.com">
```

### 渲染优化

#### 避免布局抖动
```typescript
// 使用requestAnimationFrame优化动画
const animate = () => {
  requestAnimationFrame(() => {
    // 动画逻辑
  });
};
```

#### 减少重绘
```css
/* 使用transform代替top/left */
.element {
  transform: translateX(100px);
  /* 而不是 */
  /* left: 100px; */
}
```

#### GPU加速
```css
/* 启用GPU加速 */
.accelerated {
  transform: translateZ(0);
  will-change: transform;
}
```

---

## 移动端可访问性

### 屏幕阅读器支持

#### ARIA属性
```html
<!-- 添加ARIA属性 -->
<button
  aria-label="Close menu"
  aria-expanded="false"
  aria-controls="mobile-menu"
>
  <MenuIcon />
</button>
```

#### 焦点管理
```typescript
// 焦点陷阱
const useFocusTrap = (isActive: boolean) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isActive || !containerRef.current) return;

    const focusableElements = containerRef.current.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const firstElement = focusableElements[0] as HTMLElement;
    const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;

    const handleTab = (e: KeyboardEvent) => {
      if (e.key === 'Tab') {
        if (e.shiftKey) {
          if (document.activeElement === firstElement) {
            lastElement.focus();
            e.preventDefault();
          }
        } else {
          if (document.activeElement === lastElement) {
            firstElement.focus();
            e.preventDefault();
          }
        }
      }
    };

    document.addEventListener('keydown', handleTab);
    firstElement.focus();

    return () => {
      document.removeEventListener('keydown', handleTab);
    };
  }, [isActive]);

  return containerRef;
};
```

### 键盘导航

#### 键盘快捷键
```typescript
// 键盘导航支持
const useKeyboardNavigation = () => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'Escape':
          // 关闭模态框
          break;
        case 'Enter':
          // 确认操作
          break;
        case 'ArrowLeft':
          // 导航到上一个
          break;
        case 'ArrowRight':
          // 导航到下一个
          break;
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);
};
```

---

## 移动端组件优化

### 响应式组件

#### MobileNav
```typescript
// 移动端导航组件
export function MobileNav({ children, isOpen, onClose }: MobileNavProps) {
  useEffect(() => {
    // 防止背景滚动
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  return (
    <div className="md:hidden relative z-50">
      {/* 移动端导航内容 */}
    </div>
  );
}
```

#### ResponsiveGrid
```typescript
// 响应式网格组件
export function ResponsiveGrid({
  children,
  cols = { mobile: 1, tablet: 2, desktop: 3 },
  gap = '1rem'
}: ResponsiveGridProps) {
  return (
    <div
      className="grid"
      style={{
        gridTemplateColumns: `repeat(${cols.mobile}, 1fr)`,
        gap,
      }}
    >
      <style jsx>{`
        @media (min-width: 768px) {
          div {
            grid-template-columns: repeat(${cols.tablet}, 1fr);
          }
        }
        @media (min-width: 1024px) {
          div {
            grid-template-columns: repeat(${cols.desktop}, 1fr);
          }
        }
      `}</style>
      {children}
    </div>
  );
}
```

#### TouchButton
```typescript
// 触摸优化按钮
export function TouchButton({
  children,
  onClick,
  variant = 'primary',
  size = 'md'
}: TouchButtonProps) {
  return (
    <button
      onClick={onClick}
      className="rounded-lg active:scale-95 transition-transform touch-manipulation"
    >
      {children}
    </button>
  );
}
```

### 移动端专用组件

#### MobileHeader
```typescript
// 移动端头部
export function MobileHeader({ title, onMenuToggle, showBackButton, onBack }: MobileHeaderProps) {
  return (
    <header className="md:hidden sticky top-0 bg-white border-b z-40">
      <div className="flex items-center justify-between p-4">
        <div className="flex items-center gap-3">
          {showBackButton && (
            <button onClick={onBack} aria-label="Go back">
              <ChevronRight className="h-6 w-6 rotate-180" />
            </button>
          )}
          <h1 className="text-lg font-semibold">{title}</h1>
        </div>
        {onMenuToggle && (
          <button onClick={onMenuToggle} aria-label="Open menu">
            <Menu className="h-6 w-6" />
          </button>
        )}
      </div>
    </header>
  );
}
```

#### MobileBottomNav
```typescript
// 移动端底部导航
export function MobileBottomNav({ items }: MobileBottomNavProps) {
  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-white border-t z-40">
      <div className="flex justify-around py-2">
        {items.map((item, index) => (
          <button
            key={index}
            onClick={item.onClick}
            className={`flex flex-col items-center p-2 rounded-lg ${
              item.active ? 'text-blue-600 bg-blue-50' : 'text-gray-600'
            }`}
            aria-label={item.label}
          >
            <div className="mb-1">{item.icon}</div>
            <span className="text-xs">{item.label}</span>
          </button>
        ))}
      </div>
    </nav>
  );
}
```

---

## 移动端测试

### Lighthouse测试

#### Lighthouse配置
```json
{
  "extends": "lighthouse:default",
  "settings": {
    "formFactor": "mobile",
    "throttling": {
      "rttMs": 40,
      "throughputKbps": 10240,
      "cpuSlowdownMultiplier": 4,
      "requestLatencyMs": 0,
      "downloadThroughputKbps": 0,
      "uploadThroughputKbps": 0
    },
    "screenEmulation": {
      "mobile": true,
      "width": 375,
      "height": 667,
      "deviceScaleFactor": 2,
      "disabled": false
    },
    "emulatedUserAgent": "Mozilla/5.0 (Linux; Android 10; Pixel 3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Mobile Safari/537.36"
  }
}
```

#### Lighthouse目标
- 性能: ≥90
- 可访问性: ≥90
- 最佳实践: ≥90
- SEO: ≥90
- PWA: ≥80

### 设备测试

#### 测试设备
- iPhone 12 Pro (iOS 15)
- Samsung Galaxy S21 (Android 11)
- iPad Pro (iOS 15)
- Google Pixel 6 (Android 12)

#### 浏览器测试
- Safari (iOS)
- Chrome (Android)
- Firefox (Android)
- Edge (Android)

### 性能测试

#### Core Web Vitals
- LCP (Largest Contentful Paint): <2.5s
- FID (First Input Delay): <100ms
- CLS (Cumulative Layout Shift): <0.1

#### 性能监控
```typescript
// 性能监控
const measurePerformance = () => {
  // LCP
  new PerformanceObserver((list) => {
    const entries = list.getEntries();
    const lastEntry = entries[entries.length - 1];
    console.log('LCP:', lastEntry.startTime);
  }).observe({ entryTypes: ['largest-contentful-paint'] });

  // FID
  new PerformanceObserver((list) => {
    const entries = list.getEntries();
    entries.forEach((entry) => {
      console.log('FID:', entry.processingStart - entry.startTime);
    });
  }).observe({ entryTypes: ['first-input'] });

  // CLS
  let clsValue = 0;
  new PerformanceObserver((list) => {
    const entries = list.getEntries();
    entries.forEach((entry) => {
      if (!entry.hadRecentInput) {
        clsValue += entry.value;
        console.log('CLS:', clsValue);
      }
    });
  }).observe({ entryTypes: ['layout-shift'] });
};
```

---

## 移动端最佳实践

### 1. 视口设置
```html
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
```

### 2. 字体大小
```css
/* 最小字体大小 16px */
body {
  font-size: 16px;
  line-height: 1.5;
}
```

### 3. 输入优化
```html
<!-- 输入类型优化 -->
<input type="email" inputmode="email">
<input type="tel" inputmode="tel">
<input type="number" inputmode="numeric">
```

### 4. 表单优化
```html
<!-- 自动完成 -->
<input autocomplete="name">
<input autocomplete="email">
<input autocomplete="tel">

<!-- 自动填充 -->
<input autocomplete="username">
<input autocomplete="current-password">
```

### 5. 安全区域
```css
/* 适配刘海屏 */
.safe-area {
  padding-top: env(safe-area-inset-top);
  padding-bottom: env(safe-area-inset-bottom);
  padding-left: env(safe-area-inset-left);
  padding-right: env(safe-area-inset-right);
}
```

---

## 实施计划

### 第一阶段：基础优化
1. 视口和字体优化
2. 触摸目标尺寸优化
3. 基础响应式布局

### 第二阶段：交互优化
1. 触摸反馈优化
2. 手势支持
3. 移动端专用组件

### 第三阶段：性能优化
1. 资源优化
2. 网络优化
3. 渲染优化

### 第四阶段：测试验证
1. Lighthouse测试
2. 设备测试
3. 性能监控

---

## 验收标准

### 功能验收
- [ ] 移动端适配审查完成（100+页面）
- [ ] 触摸交互优化完成
- [ ] 移动端性能测试完成（iOS、Android）
- [ ] 移动端测试通过（Lighthouse评分≥90）

### 性能验收
- [ ] Lighthouse性能评分≥90
- [ ] LCP <2.5s
- [ ] FID <100ms
- [ ] CLS <0.1

### 用户体验验收
- [ ] 触摸目标尺寸≥44x44px
- [ ] 页面加载时间<3s
- [ ] 动画流畅度≥60fps

---

**文档版本**: 1.0  
**创建日期**: 2026-08-31  
**最后更新**: 2026-08-31  
**维护团队**: AIOps SRE Agent 前端团队