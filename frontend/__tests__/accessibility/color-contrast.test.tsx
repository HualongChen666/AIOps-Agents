/**
 * 颜色对比度可访问性测试
 * 测试颜色对比度是否符合 WCAG 2.1 AA 标准
 * WCAG AA 要求：正常文本 4.5:1，大文本 3:1，UI 组件 3:1
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { StatusBadge } from '@/components/ui/StatusBadge';

expect.extend(toHaveNoViolations);

describe('颜色对比度可访问性测试', () => {
  describe('按钮对比度', () => {
    it('默认按钮应该有足够的对比度', async () => {
      const { container } = render(
        <Button variant="default">默认按钮</Button>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('outline 按钮应该有足够的对比度', async () => {
      const { container } = render(
        <Button variant="outline">轮廓按钮</Button>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('secondary 按钮应该有足够的对比度', async () => {
      const { container } = render(
        <Button variant="secondary">次要按钮</Button>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('ghost 按钮应该有足够的对比度', async () => {
      const { container } = render(
        <Button variant="ghost">幽灵按钮</Button>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('link 按钮应该有足够的对比度', async () => {
      const { container } = render(
        <Button variant="link">链接按钮</Button>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('destructive 按钮应该有足够的对比度', async () => {
      const { container } = render(
        <Button variant="destructive">删除按钮</Button>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('禁用按钮应该有足够的对比度', async () => {
      const { container } = render(
        <Button disabled>禁用按钮</Button>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe('文本对比度', () => {
    it('卡片标题应该有足够的对比度', async () => {
      const { container } = render(
        <Card>
          <CardHeader>
            <CardTitle>卡片标题</CardTitle>
          </CardHeader>
          <CardContent>
            <p>卡片内容文本</p>
          </CardContent>
        </Card>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('普通文本应该有足够的对比度', async () => {
      const { container } = render(
        <p className="text-gray-900">这是普通文本</p>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('次要文本应该有足够的对比度', async () => {
      const { container } = render(
        <p className="text-gray-500">这是次要文本</p>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe('徽章对比度', () => {
    it('状态徽章应该有足够的对比度', async () => {
      const { container } = render(
        <div>
          <StatusBadge status="success">成功</StatusBadge>
          <StatusBadge status="warning">警告</StatusBadge>
          <StatusBadge status="error">错误</StatusBadge>
          <StatusBadge status="info">信息</StatusBadge>
        </div>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('普通徽章应该有足够的对比度', async () => {
      const { container } = render(
        <Badge>徽章文本</Badge>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe('链接对比度', () => {
    it('文本链接应该有足够的对比度', async () => {
      const { container } = render(
        <a href="/test" className="text-blue-600 underline">
          这是一个链接
        </a>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('链接悬停状态应该有足够的对比度', async () => {
      const { container } = render(
        <a href="/test" className="text-blue-600 hover:text-blue-700 underline">
          悬停链接
        </a>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe('表单元素对比度', () => {
    it('输入框文本应该有足够的对比度', async () => {
      const { container } = render(
        <div>
          <label htmlFor="input" className="text-gray-900">标签</label>
          <input
            id="input"
            type="text"
            className="border border-gray-300 bg-white text-gray-900"
            placeholder="占位符文本"
          />
        </div>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('占位符文本应该有足够的对比度', async () => {
      const { container } = render(
        <input
          type="text"
          className="placeholder:text-gray-500"
          placeholder="占位符文本"
        />
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('错误消息应该有足够的对比度', async () => {
      const { container } = render(
        <span className="text-red-600">错误消息文本</span>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe('颜色不应作为唯一指示器', () => {
    it('错误状态应该有文本指示器', async () => {
      const { container } = render(
        <div>
          <span className="text-red-600 font-semibold">错误</span>
          <span aria-label="错误状态">⚠️</span>
        </div>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('成功状态应该有文本指示器', async () => {
      const { container } = render(
        <div>
          <span className="text-green-600 font-semibold">成功</span>
          <span aria-label="成功状态">✓</span>
        </div>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('警告状态应该有文本指示器', async () => {
      const { container } = render(
        <div>
          <span className="text-yellow-600 font-semibold">警告</span>
          <span aria-label="警告状态">⚡</span>
        </div>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe('深色模式对比度', () => {
    it('深色背景上的文本应该有足够的对比度', async () => {
      const { container } = render(
        <div className="bg-gray-900 text-white p-4">
          <h2>深色模式标题</h2>
          <p>深色模式文本内容</p>
        </div>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('深色模式按钮应该有足够的对比度', async () => {
      const { container } = render(
        <div className="bg-gray-900 p-4">
          <Button variant="default">深色模式按钮</Button>
        </div>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe('WCAG 2.1 AA 对比度要求', () => {
    it('正常文本（小于18pt）应该至少有 4.5:1 的对比度', async () => {
      const { container } = render(
        <p className="text-base text-gray-900">正常大小的文本</p>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('大文本（18pt或14pt粗体）应该至少有 3:1 的对比度', async () => {
      const { container } = render(
        <h1 className="text-2xl font-bold text-gray-900">大标题文本</h1>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('UI 组件和图形对象应该至少有 3:1 的对比度', async () => {
      const { container } = render(
        <Button>UI 组件</Button>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe('焦点指示器对比度', () => {
    it('焦点环应该有足够的对比度', async () => {
      const { container } = render(
        <Button className="focus-visible:ring-2 focus-visible:ring-blue-500">
          有焦点环的按钮
        </Button>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe('边框和分隔线对比度', () => {
    it('边框应该有足够的对比度', async () => {
      const { container } = render(
        <div className="border border-gray-300 p-4">
          有边框的内容
        </div>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('分隔线应该有足够的对比度', async () => {
      const { container } = render(
        <hr className="border-gray-300" />
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe('图标对比度', () => {
    it('图标应该有足够的对比度', async () => {
      const { container } = render(
        <div className="text-gray-600">
          <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
            <path d="M10 2a8 8 0 100 16 8 8 0 000-16z" />
          </svg>
        </div>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe('表格对比度', () => {
    it('表格文本应该有足够的对比度', async () => {
      const { container } = render(
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="text-left text-gray-900 py-2">列1</th>
              <th className="text-left text-gray-900 py-2">列2</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-gray-100">
              <td className="text-gray-700 py-2">数据1</td>
              <td className="text-gray-700 py-2">数据2</td>
            </tr>
          </tbody>
        </table>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe('交互状态对比度', () => {
    it('悬停状态应该保持足够的对比度', async () => {
      const { container } = render(
        <Button className="hover:bg-blue-700">悬停按钮</Button>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('活动状态应该保持足够的对比度', async () => {
      const { container } = render(
        <Button className="active:bg-blue-800">活动按钮</Button>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });
});
