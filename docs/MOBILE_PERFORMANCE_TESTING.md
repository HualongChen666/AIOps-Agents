# 移动端性能测试文档

## 概述

本文档描述了AIOps SRE Agent前端应用的移动端性能测试方案，包括测试工具、测试方法、性能指标和优化建议。

---

## 性能测试工具

### Lighthouse

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

#### Lighthouse命令行
```bash
# 运行Lighthouse测试
lighthouse https://your-app.com --view --preset=mobile --output html --output-path=./lighthouse-report.html

# 运行Lighthouse CI
lighthouse https://your-app.com --preset=mobile --output json --output-path=./lighthouse-report.json
```

#### Lighthouse目标指标
- 性能: ≥90
- 可访问性: ≥90
- 最佳实践: ≥90
- SEO: ≥90
- PWA: ≥80

### WebPageTest

#### WebPageTest配置
```bash
# 运行WebPageTest测试
webpagetest --location "Dulles:Chrome" --mobile --url https://your-app.com

# 运行WebPageTest CI
webpagetest --server https://www.webpagetest.org --location "Dulles:Chrome" --mobile --url https://your-app.com --key YOUR_API_KEY
```

#### WebPageTest指标
- First Byte Time (TTFB): <600ms
- Start Render: <1s
- Speed Index: <3s
- Time to Interactive: <5s

### Chrome DevTools

#### 性能分析
```typescript
// 使用Performance API
const measurePerformance = () => {
  // 页面加载时间
  const pageLoadTime = performance.timing.loadEventEnd - performance.timing.navigationStart;
  console.log('Page load time:', pageLoadTime);

  // DOM加载时间
  const domLoadTime = performance.timing.domContentLoadedEventEnd - performance.timing.navigationStart;
  console.log('DOM load time:', domLoadTime);

  // 首次内容绘制
  const paintEntries = performance.getEntriesByType('paint');
  const fcp = paintEntries.find(entry => entry.name === 'first-contentful-paint');
  console.log('FCP:', fcp?.startTime);
};
```

#### 网络分析
```typescript
// 网络性能分析
const analyzeNetwork = () => {
  const resourceEntries = performance.getEntriesByType('resource');
  
  resourceEntries.forEach(entry => {
    console.log(`${entry.name}:`, {
      duration: entry.duration,
      size: entry.transferSize,
      cached: entry.transferSize === 0
    });
  });
};
```

---

## Core Web Vitals

### LCP (Largest Contentful Paint)

#### LCP测量
```typescript
// LCP测量
const measureLCP = () => {
  new PerformanceObserver((list) => {
    const entries = list.getEntries();
    const lastEntry = entries[entries.length - 1];
    const lcp = lastEntry.startTime;
    
    console.log('LCP:', lcp);
    
    // 发送到监控服务
    analytics.track('lcp', { value: lcp });
    
    // LCP目标: <2.5s
    if (lcp > 2500) {
      console.warn('LCP exceeds target:', lcp);
    }
  }).observe({ entryTypes: ['largest-contentful-paint'] });
};
```

#### LCP优化
```typescript
// LCP优化策略
const optimizeLCP = () => {
  // 1. 优化关键CSS
  const criticalCSS = extractCriticalCSS();
  injectCriticalCSS(criticalCSS);

  // 2. 延迟加载非关键资源
  lazyLoadNonCriticalResources();

  // 3. 优化图片
  optimizeImages();

  // 4. 预加载关键资源
  preloadCriticalResources();
};
```

### FID (First Input Delay)

#### FID测量
```typescript
// FID测量
const measureFID = () => {
  new PerformanceObserver((list) => {
    const entries = list.getEntries();
    entries.forEach((entry) => {
      const fid = entry.processingStart - entry.startTime;
      
      console.log('FID:', fid);
      
      // 发送到监控服务
      analytics.track('fid', { value: fid });
      
      // FID目标: <100ms
      if (fid > 100) {
        console.warn('FID exceeds target:', fid);
      }
    });
  }).observe({ entryTypes: ['first-input'] });
};
```

#### FID优化
```typescript
// FID优化策略
const optimizeFID = () => {
  // 1. 减少JavaScript执行时间
  reduceJavaScriptExecution();

  // 2. 分割长任务
  splitLongTasks();

  // 3. 使用Web Workers
  useWebWorkers();

  // 4. 优化第三方脚本
  optimizeThirdPartyScripts();
};
```

### CLS (Cumulative Layout Shift)

#### CLS测量
```typescript
// CLS测量
const measureCLS = () => {
  let clsValue = 0;
  
  new PerformanceObserver((list) => {
    const entries = list.getEntries();
    entries.forEach((entry) => {
      if (!entry.hadRecentInput) {
        clsValue += entry.value;
        
        console.log('CLS:', clsValue);
        
        // 发送到监控服务
        analytics.track('cls', { value: clsValue });
        
        // CLS目标: <0.1
        if (clsValue > 0.1) {
          console.warn('CLS exceeds target:', clsValue);
        }
      }
    });
  }).observe({ entryTypes: ['layout-shift'] });
};
```

#### CLS优化
```typescript
// CLS优化策略
const optimizeCLS = () => {
  // 1. 为图片和视频设置尺寸
  setDimensionsForMedia();

  // 2. 预留广告空间
  reserveSpaceForAds();

  // 3. 避免动态插入内容
  avoidDynamicContentInsertion();

  // 4. 使用CSS transitions
  useCSSTransitions();
};
```

---

## 移动端性能测试

### iOS设备测试

#### 测试设备
- iPhone 12 Pro (iOS 15)
- iPhone 13 Pro (iOS 16)
- iPad Pro (iOS 15)

#### 测试方法
```typescript
// iOS性能测试
const testiOSPerformance = async () => {
  // 1. 使用Safari Web Inspector
  const safariInspector = await connectSafariInspector();
  
  // 2. 运行性能分析
  const performanceData = await safariInspector.runPerformanceAnalysis();
  
  // 3. 分析结果
  analyzePerformanceData(performanceData);
  
  // 4. 生成报告
  generatePerformanceReport(performanceData);
};
```

#### iOS特定优化
```typescript
// iOS特定优化
const optimizeForIOS = () => {
  // 1. 启用硬件加速
  enableHardwareAcceleration();

  // 2. 优化滚动性能
  optimizeScrolling();

  // 3. 减少重绘
  reduceRepaints();

  // 4. 使用CSS transforms
  useCSSTransforms();
};
```

### Android设备测试

#### 测试设备
- Samsung Galaxy S21 (Android 11)
- Google Pixel 6 (Android 12)
- OnePlus 9 Pro (Android 11)

#### 测试方法
```typescript
// Android性能测试
const testAndroidPerformance = async () => {
  // 1. 使用Chrome DevTools
  const chromeDevTools = await connectChromeDevTools();
  
  // 2. 运行性能分析
  const performanceData = await chromeDevTools.runPerformanceAnalysis();
  
  // 3. 分析结果
  analyzePerformanceData(performanceData);
  
  // 4. 生成报告
  generatePerformanceReport(performanceData);
};
```

#### Android特定优化
```typescript
// Android特定优化
const optimizeForAndroid = () => {
  // 1. 启用GPU加速
  enableGPUAcceleration();

  // 2. 优化触摸响应
  optimizeTouchResponse();

  // 3. 减少内存使用
  reduceMemoryUsage();

  // 4. 使用硬件层
  useHardwareLayers();
};
```

---

## 性能监控

### 实时监控

#### 性能监控Hook
```typescript
// 性能监控Hook
const usePerformanceMonitor = () => {
  const [metrics, setMetrics] = useState({
    lcp: 0,
    fid: 0,
    cls: 0,
    ttfb: 0
  });

  useEffect(() => {
    // LCP监控
    const lcpObserver = new PerformanceObserver((list) => {
      const entries = list.getEntries();
      const lastEntry = entries[entries.length - 1];
      setMetrics(prev => ({ ...prev, lcp: lastEntry.startTime }));
    });
    lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] });

    // FID监控
    const fidObserver = new PerformanceObserver((list) => {
      const entries = list.getEntries();
      entries.forEach((entry) => {
        const fid = entry.processingStart - entry.startTime;
        setMetrics(prev => ({ ...prev, fid }));
      });
    });
    fidObserver.observe({ entryTypes: ['first-input'] });

    // CLS监控
    let clsValue = 0;
    const clsObserver = new PerformanceObserver((list) => {
      const entries = list.getEntries();
      entries.forEach((entry) => {
        if (!entry.hadRecentInput) {
          clsValue += entry.value;
          setMetrics(prev => ({ ...prev, cls: clsValue }));
        }
      });
    });
    clsObserver.observe({ entryTypes: ['layout-shift'] });

    return () => {
      lcpObserver.disconnect();
      fidObserver.disconnect();
      clsObserver.disconnect();
    };
  }, []);

  return metrics;
};
```

#### 性能监控组件
```typescript
// 性能监控组件
const PerformanceMonitor = () => {
  const metrics = usePerformanceMonitor();

  return (
    <div className="fixed bottom-4 right-4 bg-white p-4 rounded-lg shadow-lg">
      <h3>Performance Metrics</h3>
      <div>LCP: {metrics.lcp.toFixed(0)}ms</div>
      <div>FID: {metrics.fid.toFixed(0)}ms</div>
      <div>CLS: {metrics.cls.toFixed(3)}</div>
    </div>
  );
};
```

### 性能报告

#### 性能报告生成
```typescript
// 性能报告生成
const generatePerformanceReport = async () => {
  const metrics = {
    lcp: await measureLCP(),
    fid: await measureFID(),
    cls: await measureCLS(),
    ttfb: await measureTTFB(),
    fcp: await measureFCP(),
    tti: await measureTTI()
  };

  const report = {
    timestamp: new Date().toISOString(),
    metrics,
    device: getDeviceInfo(),
    network: getNetworkInfo(),
    score: calculatePerformanceScore(metrics)
  };

  // 发送到监控服务
  await sendPerformanceReport(report);

  return report;
};
```

#### 性能评分计算
```typescript
// 性能评分计算
const calculatePerformanceScore = (metrics: PerformanceMetrics) => {
  let score = 100;

  // LCP评分
  if (metrics.lcp > 2500) {
    score -= (metrics.lcp - 2500) / 100;
  }

  // FID评分
  if (metrics.fid > 100) {
    score -= (metrics.fid - 100) / 10;
  }

  // CLS评分
  if (metrics.cls > 0.1) {
    score -= (metrics.cls - 0.1) * 100;
  }

  return Math.max(0, Math.min(100, score));
};
```

---

## 性能优化策略

### 资源优化

#### 代码分割
```typescript
// 路由级别代码分割
const Dashboard = React.lazy(() => import('./pages/Dashboard'));
const Settings = React.lazy(() => import('./pages/Settings'));
const Profile = React.lazy(() => import('./pages/Profile'));

// 组件级别代码分割
const HeavyComponent = React.lazy(() => import('./components/HeavyComponent'));
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
# Nginx HTTP/2配置
server {
    listen 443 ssl http2;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
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
        '/scripts/main.js',
        '/images/logo.png'
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
<link rel="dns-prefetch" href="https://cdn.example.com">
```

### 渲染优化

#### GPU加速
```css
/* 启用GPU加速 */
.accelerated {
  transform: translateZ(0);
  will-change: transform;
}

/* 使用transform代替top/left */
.element {
  transform: translateX(100px);
  /* 而不是 */
  /* left: 100px; */
}
```

#### 减少重绘
```typescript
// 使用requestAnimationFrame优化动画
const animate = () => {
  requestAnimationFrame(() => {
    // 动画逻辑
  });
};
```

#### 批量DOM操作
```typescript
// 批量DOM操作
const batchDOMUpdates = (updates: Array<() => void>) => {
  requestAnimationFrame(() => {
    updates.forEach(update => update());
  });
};
```

---

## 性能测试自动化

### CI/CD集成

#### Lighthouse CI
```yaml
# GitHub Actions配置
name: Performance Test

on: [push, pull_request]

jobs:
  lighthouse:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Lighthouse CI
        uses: treosh/lighthouse-ci-action@v9
        with:
          uploadArtifacts: true
          temporaryPublicStorage: true
```

#### WebPageTest CI
```yaml
# WebPageTest CI配置
name: WebPageTest

on: [push, pull_request]

jobs:
  webpagetest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run WebPageTest
        run: |
          webpagetest --server https://www.webpagetest.org \
            --location "Dulles:Chrome" \
            --mobile \
            --url https://your-app.com \
            --key ${{ secrets.WEBPAGETEST_API_KEY }}
```

### 性能回归检测

#### 性能基线
```typescript
// 性能基线配置
const performanceBaseline = {
  lcp: 2500,
  fid: 100,
  cls: 0.1,
  ttfb: 600,
  fcp: 1800,
  tti: 3800
};

// 性能回归检测
const detectPerformanceRegression = (currentMetrics: PerformanceMetrics) => {
  const regressions = [];

  for (const [metric, baseline] of Object.entries(performanceBaseline)) {
    const current = currentMetrics[metric];
    const threshold = baseline * 1.1; // 10%阈值

    if (current > threshold) {
      regressions.push({
        metric,
        baseline,
        current,
        threshold,
        regression: (current - baseline) / baseline
      });
    }
  }

  return regressions;
};
```

#### 性能警报
```typescript
// 性能警报
const sendPerformanceAlert = (regressions: Regression[]) => {
  if (regressions.length > 0) {
    const message = `Performance regression detected:\n${regressions.map(r => 
      `${r.metric}: ${r.current}ms (baseline: ${r.baseline}ms)`
    ).join('\n')}`;

    // 发送到Slack
    sendSlackAlert(message);

    // 发送到邮件
    sendEmailAlert(message);

    // 创建GitHub Issue
    createGitHubIssue(message);
  }
};
```

---

## 性能测试报告

### 报告模板

#### 性能测试报告
```typescript
// 性能测试报告生成
const generatePerformanceTestReport = (testResults: TestResults) => {
  const report = {
    summary: {
      overallScore: calculateOverallScore(testResults),
      passedTests: testResults.filter(t => t.passed).length,
      totalTests: testResults.length,
      timestamp: new Date().toISOString()
    },
    metrics: {
      lcp: testResults.lcp,
      fid: testResults.fid,
      cls: testResults.cls,
      ttfb: testResults.ttfb,
      fcp: testResults.fcp,
      tti: testResults.tti
    },
    device: testResults.device,
    network: testResults.network,
    recommendations: generateRecommendations(testResults)
  };

  return report;
};
```

#### 推荐生成
```typescript
// 性能优化推荐生成
const generateRecommendations = (testResults: TestResults) => {
  const recommendations = [];

  if (testResults.lcp > 2500) {
    recommendations.push({
      priority: 'high',
      metric: 'LCP',
      recommendation: '优化关键资源加载，使用懒加载和预加载'
    });
  }

  if (testResults.fid > 100) {
    recommendations.push({
      priority: 'high',
      metric: 'FID',
      recommendation: '减少JavaScript执行时间，分割长任务'
    });
  }

  if (testResults.cls > 0.1) {
    recommendations.push({
      priority: 'medium',
      metric: 'CLS',
      recommendation: '为图片和视频设置尺寸，避免动态插入内容'
    });
  }

  return recommendations;
};
```

---

## 性能测试最佳实践

### 1. 测试环境
- 使用真实设备进行测试
- 模拟真实网络条件
- 测试不同设备和浏览器

### 2. 测试频率
- 每次代码提交后运行测试
- 定期运行完整性能测试
- 监控生产环境性能

### 3. 性能目标
- LCP: <2.5s
- FID: <100ms
- CLS: <0.1
- Lighthouse评分: ≥90

### 4. 持续优化
- 定期审查性能指标
- 实施性能优化措施
- 监控优化效果

---

**文档版本**: 1.0  
**创建日期**: 2026-08-31  
**最后更新**: 2026-08-31  
**维护团队**: AIOps SRE Agent 前端团队