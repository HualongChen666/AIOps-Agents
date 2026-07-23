'use client'

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';

export default function AccessibilityPage() {
  const [highContrast, setHighContrast] = useState(false);
  const [fontSize, setFontSize] = useState(16);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [screenReaderEnabled, setScreenReaderEnabled] = useState(false);
  const [keyboardShortcuts, setKeyboardShortcuts] = useState(true);
  const [pressedKeys, setPressedKeys] = useState<Set<string>>(new Set());

  // 高对比度模式
  useEffect(() => {
    if (highContrast) {
      document.documentElement.classList.add('high-contrast');
    } else {
      document.documentElement.classList.remove('high-contrast');
    }
  }, [highContrast]);

  // 字体大小调整
  useEffect(() => {
    document.documentElement.style.fontSize = `${fontSize}px`;
  }, [fontSize]);

  // 减少动画
  useEffect(() => {
    if (reducedMotion) {
      document.documentElement.classList.add('reduced-motion');
    } else {
      document.documentElement.classList.remove('reduced-motion');
    }
  }, [reducedMotion]);

  // 键盘快捷键监听
  useEffect(() => {
    if (!keyboardShortcuts) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      const keys = new Set(pressedKeys);
      keys.add(e.key.toLowerCase());
      setPressedKeys(keys);

      // 快捷键组合
      if (e.ctrlKey || e.metaKey) {
        switch (e.key.toLowerCase()) {
          case 'k':
            e.preventDefault();
            alert('快捷键: Ctrl+K - 打开搜索');
            break;
          case '/':
            e.preventDefault();
            alert('快捷键: Ctrl+/ - 打开帮助');
            break;
          case 'b':
            e.preventDefault();
            alert('快捷键: Ctrl+B - 切换侧边栏');
            break;
        }
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      const keys = new Set(pressedKeys);
      keys.delete(e.key.toLowerCase());
      setPressedKeys(keys);
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, [keyboardShortcuts, pressedKeys]);

  const increaseFontSize = useCallback(() => {
    setFontSize(prev => Math.min(prev + 2, 24));
  }, []);

  const decreaseFontSize = useCallback(() => {
    setFontSize(prev => Math.max(prev - 2, 12));
  }, []);

  const resetFontSize = useCallback(() => {
    setFontSize(16);
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">可访问性设置</h1>
        <Button onClick={() => setHighContrast(!highContrast)} variant={highContrast ? 'default' : 'outline'}>
          {highContrast ? '关闭高对比度' : '开启高对比度'}
        </Button>
      </div>

      {/* 可访问性概览 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">高对比度</CardTitle>
          </CardHeader>
          <CardContent>
            <p className={`text-2xl font-bold ${highContrast ? 'text-green-600' : 'text-gray-400'}`}>
              {highContrast ? '已启用' : '未启用'}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">字体大小</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{fontSize}px</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">减少动画</CardTitle>
          </CardHeader>
          <CardContent>
            <p className={`text-2xl font-bold ${reducedMotion ? 'text-green-600' : 'text-gray-400'}`}>
              {reducedMotion ? '已启用' : '未启用'}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">键盘快捷键</CardTitle>
          </CardHeader>
          <CardContent>
            <p className={`text-2xl font-bold ${keyboardShortcuts ? 'text-green-600' : 'text-gray-400'}`}>
              {keyboardShortcuts ? '已启用' : '未启用'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* 视觉设置 */}
      <Card>
        <CardHeader>
          <CardTitle>视觉设置</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">高对比度模式</label>
            <div className="flex items-center gap-4">
              <Button
                variant={highContrast ? 'default' : 'outline'}
                onClick={() => setHighContrast(true)}
              >
                启用
              </Button>
              <Button
                variant={!highContrast ? 'default' : 'outline'}
                onClick={() => setHighContrast(false)}
              >
                禁用
              </Button>
            </div>
            <p className="text-sm text-gray-500 mt-2">
              高对比度模式可以提高文字和背景的对比度，帮助视力障碍用户更好地阅读内容。
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">字体大小</label>
            <div className="flex items-center gap-4">
              <Button variant="outline" onClick={decreaseFontSize}>
                减小
              </Button>
              <span className="text-lg font-medium">{fontSize}px</span>
              <Button variant="outline" onClick={increaseFontSize}>
                增大
              </Button>
              <Button variant="outline" onClick={resetFontSize}>
                重置
              </Button>
            </div>
            <p className="text-sm text-gray-500 mt-2">
              调整字体大小以适应不同的阅读需求。范围: 12px - 24px
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">减少动画</label>
            <div className="flex items-center gap-4">
              <Button
                variant={reducedMotion ? 'default' : 'outline'}
                onClick={() => setReducedMotion(true)}
              >
                启用
              </Button>
              <Button
                variant={!reducedMotion ? 'default' : 'outline'}
                onClick={() => setReducedMotion(false)}
              >
                禁用
              </Button>
            </div>
            <p className="text-sm text-gray-500 mt-2">
              减少动画效果可以帮助对运动敏感的用户避免不适。
            </p>
          </div>
        </CardContent>
      </Card>

      {/* 键盘导航 */}
      <Card>
        <CardHeader>
          <CardTitle>键盘导航</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">键盘快捷键</label>
            <div className="flex items-center gap-4">
              <Button
                variant={keyboardShortcuts ? 'default' : 'outline'}
                onClick={() => setKeyboardShortcuts(true)}
              >
                启用
              </Button>
              <Button
                variant={!keyboardShortcuts ? 'default' : 'outline'}
                onClick={() => setKeyboardShortcuts(false)}
              >
                禁用
              </Button>
            </div>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-3">可用快捷键</h3>
            <div className="space-y-2">
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm">打开搜索</span>
                <kbd className="px-2 py-1 bg-white border border-gray-300 rounded text-sm">Ctrl + K</kbd>
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm">打开帮助</span>
                <kbd className="px-2 py-1 bg-white border border-gray-300 rounded text-sm">Ctrl + /</kbd>
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm">切换侧边栏</span>
                <kbd className="px-2 py-1 bg-white border border-gray-300 rounded text-sm">Ctrl + B</kbd>
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm">导航到下一项</span>
                <kbd className="px-2 py-1 bg-white border border-gray-300 rounded text-sm">Tab</kbd>
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm">导航到上一项</span>
                <kbd className="px-2 py-1 bg-white border border-gray-300 rounded text-sm">Shift + Tab</kbd>
              </div>
            </div>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-3">当前按键</h3>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-600">
                按下的键: {pressedKeys.size > 0 ? Array.from(pressedKeys).join(' + ') : '无'}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 屏幕阅读器支持 */}
      <Card>
        <CardHeader>
          <CardTitle>屏幕阅读器支持</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">屏幕阅读器模式</label>
            <div className="flex items-center gap-4">
              <Button
                variant={screenReaderEnabled ? 'default' : 'outline'}
                onClick={() => setScreenReaderEnabled(true)}
              >
                启用
              </Button>
              <Button
                variant={!screenReaderEnabled ? 'default' : 'outline'}
                onClick={() => setScreenReaderEnabled(false)}
              >
                禁用
              </Button>
            </div>
            <p className="text-sm text-gray-500 mt-2">
              启用屏幕阅读器模式会添加额外的ARIA标签和描述，帮助屏幕阅读器用户更好地理解界面。
            </p>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-3">ARIA标签示例</h3>
            <div className="space-y-3">
              <div className="p-4 border border-gray-200 rounded-lg">
                <div role="button" tabIndex={0} aria-label="示例按钮，点击执行操作" className="cursor-pointer hover:bg-gray-50 p-2">
                  <span className="font-medium">示例按钮</span>
                  <span className="sr-only">（带ARIA标签）</span>
                </div>
                <p className="text-xs text-gray-500 mt-2">此按钮包含aria-label属性，屏幕阅读器会读出"示例按钮，点击执行操作"</p>
              </div>

              <div className="p-4 border border-gray-200 rounded-lg">
                <div role="region" aria-label="重要信息区域" aria-live="polite">
                  <p className="font-medium">重要信息区域</p>
                  <p className="text-sm text-gray-600">这是一个使用aria-live的区域，内容变化时会通知屏幕阅读器。</p>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 焦点管理 */}
      <Card>
        <CardHeader>
          <CardTitle>焦点管理</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-3">焦点可见性</h3>
            <p className="text-sm text-gray-600 mb-4">
              所有可交互元素都有清晰的焦点指示器，确保键盘用户可以轻松识别当前焦点位置。
            </p>
            <div className="flex gap-4">
              <Button>示例按钮1</Button>
              <Button variant="outline">示例按钮2</Button>
              <Input placeholder="示例输入框" className="max-w-xs" />
              <Select>
                <option>示例下拉框</option>
              </Select>
            </div>
            <p className="text-xs text-gray-500 mt-2">使用Tab键在这些元素之间导航，观察焦点指示器。</p>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-3">跳过导航链接</h3>
            <p className="text-sm text-gray-600 mb-4">
              为键盘用户提供"跳到主内容"链接，避免每次页面加载时都要导航过重复的导航元素。
            </p>
            <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 px-4 py-2 bg-blue-600 text-white rounded">
              跳到主内容
            </a>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
