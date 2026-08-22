import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Header } from '@/components/layout/Header';

// Mock dependencies
jest.mock('@/components/ThemeProvider', () => ({
  useTheme: jest.fn(() => ({
    theme: 'light',
    toggleTheme: jest.fn(),
  })),
}));

jest.mock('@/components/ai/AICopilot', () => ({
  AICopilot: () => <div data-testid="ai-copilot">AI Copilot</div>,
}));

jest.mock('@/store/tenant', () => ({
  useTenantStore: jest.fn(() => ({
    currentTenant: { id: '1', name: 'Test Tenant', plan: 'pro', status: 'active' },
    tenants: [
      { id: '1', name: 'Test Tenant', plan: 'pro', status: 'active' },
      { id: '2', name: 'Another Tenant', plan: 'basic', status: 'active' },
    ],
    setCurrentTenant: jest.fn(),
  })),
}));

describe('Header Component', () => {
  describe('Rendering', () => {
    it('should render header with search input', () => {
      render(<Header />);
      
      const searchInput = screen.getByPlaceholderText('搜索...');
      expect(searchInput).toBeInTheDocument();
    });

    it('should render tenant selector', () => {
      render(<Header />);
      
      expect(screen.getByText('Test Tenant')).toBeInTheDocument();
    });

    it('should render AI Copilot button', () => {
      render(<Header />);
      
      expect(screen.getByText('🤖')).toBeInTheDocument();
      expect(screen.getByText('AI Copilot')).toBeInTheDocument();
    });

    it('should render notification button', () => {
      render(<Header />);
      
      expect(screen.getByText('🔔')).toBeInTheDocument();
    });

    it('should render theme toggle button', () => {
      render(<Header />);
      
      const themeButton = screen.getByTitle('切换主题');
      expect(themeButton).toBeInTheDocument();
    });

    it('should render user menu', () => {
      render(<Header />);
      
      expect(screen.getByText('用户')).toBeInTheDocument();
      expect(screen.getByText('管理员')).toBeInTheDocument();
    });
  });

  describe('Tenant Selector', () => {
    it('should show tenant selector dropdown when clicked', async () => {
      const user = userEvent.setup();
      render(<Header />);
      
      const tenantButton = screen.getByText('Test Tenant');
      await user.click(tenantButton);
      
      expect(screen.getByText('切换租户')).toBeInTheDocument();
    });

    it('should display all tenants in dropdown', async () => {
      const user = userEvent.setup();
      render(<Header />);
      
      const tenantButton = screen.getByText('Test Tenant');
      await user.click(tenantButton);
      
      expect(screen.getByText('Test Tenant')).toBeInTheDocument();
      expect(screen.getByText('Another Tenant')).toBeInTheDocument();
    });

    it('should show tenant plan badges', async () => {
      const user = userEvent.setup();
      render(<Header />);
      
      const tenantButton = screen.getByText('Test Tenant');
      await user.click(tenantButton);
      
      expect(screen.getByText('pro')).toBeInTheDocument();
      expect(screen.getByText('basic')).toBeInTheDocument();
    });

    it('should show tenant status badges', async () => {
      const user = userEvent.setup();
      render(<Header />);
      
      const tenantButton = screen.getByText('Test Tenant');
      await user.click(tenantButton);
      
      expect(screen.getByText('活跃')).toBeInTheDocument();
    });

    it('should highlight current tenant', async () => {
      const user = userEvent.setup();
      render(<Header />);
      
      const tenantButton = screen.getByText('Test Tenant');
      await user.click(tenantButton);
      
      // Current tenant should have checkmark
      expect(screen.getByText('✓')).toBeInTheDocument();
    });

    it('should show create new tenant button', async () => {
      const user = userEvent.setup();
      render(<Header />);
      
      const tenantButton = screen.getByText('Test Tenant');
      await user.click(tenantButton);
      
      expect(screen.getByText('+ 创建新租户')).toBeInTheDocument();
    });
  });

  describe('AI Copilot', () => {
    it('should show AI Copilot modal when button clicked', async () => {
      const user = userEvent.setup();
      render(<Header />);
      
      const aiButton = screen.getByText('AI Copilot');
      await user.click(aiButton);
      
      expect(screen.getByTestId('ai-copilot')).toBeInTheDocument();
    });
  });

  describe('Notifications', () => {
    it('should show notification badge', () => {
      render(<Header />);
      
      expect(screen.getByText('3')).toBeInTheDocument();
    });

    it('should show notification dropdown when clicked', async () => {
      const user = userEvent.setup();
      render(<Header />);
      
      const notificationButton = screen.getByText('🔔');
      await user.click(notificationButton);
      
      expect(screen.getByText('通知')).toBeInTheDocument();
    });

    it('should display notification items', async () => {
      const user = userEvent.setup();
      render(<Header />);
      
      const notificationButton = screen.getByText('🔔');
      await user.click(notificationButton);
      
      expect(screen.getByText('新告警: CPU使用率过高')).toBeInTheDocument();
      expect(screen.getByText('修复任务已完成')).toBeInTheDocument();
      expect(screen.getByText('系统健康度更新')).toBeInTheDocument();
    });

    it('should show notification timestamps', async () => {
      const user = userEvent.setup();
      render(<Header />);
      
      const notificationButton = screen.getByText('🔔');
      await user.click(notificationButton);
      
      expect(screen.getByText('2分钟前')).toBeInTheDocument();
      expect(screen.getByText('5分钟前')).toBeInTheDocument();
      expect(screen.getByText('10分钟前')).toBeInTheDocument();
    });
  });

  describe('Theme Toggle', () => {
    it('should show sun icon in light mode', () => {
      render(<Header />);
      
      expect(screen.getByText('🌙')).toBeInTheDocument();
    });
  });

  describe('User Menu', () => {
    it('should display user avatar', () => {
      render(<Header />);
      
      const avatar = screen.getByText('U');
      expect(avatar).toBeInTheDocument();
    });

    it('should display user name', () => {
      render(<Header />);
      
      expect(screen.getByText('用户')).toBeInTheDocument();
    });

    it('should display user role', () => {
      render(<Header />);
      
      expect(screen.getByText('管理员')).toBeInTheDocument();
    });
  });

  describe('Styling', () => {
    it('should apply correct header styles', () => {
      const { container } = render(<Header />);
      
      const header = container.querySelector('header');
      expect(header).toHaveClass('bg-white');
      expect(header).toHaveClass('border-b');
    });

    it('should apply correct search input styles', () => {
      render(<Header />);
      
      const searchInput = screen.getByPlaceholderText('搜索...');
      expect(searchInput).toHaveClass('w-64');
      expect(searchInput).toHaveClass('border');
    });
  });

  describe('Edge Cases', () => {
    it('should handle no current tenant', () => {
      const { useTenantStore } = require('@/store/tenant');
      useTenantStore.mockReturnValue({
        currentTenant: null,
        tenants: [],
        setCurrentTenant: jest.fn(),
      });
      
      render(<Header />);
      
      expect(screen.getByText('选择租户')).toBeInTheDocument();
    });

    it('should handle empty tenants list', () => {
      const { useTenantStore } = require('@/store/tenant');
      useTenantStore.mockReturnValue({
        currentTenant: null,
        tenants: [],
        setCurrentTenant: jest.fn(),
      });
      
      render(<Header />);
      
      expect(screen.getByText('选择租户')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have accessible search input', () => {
      render(<Header />);
      
      const searchInput = screen.getByPlaceholderText('搜索...');
      expect(searchInput).toBeInstanceOf(HTMLInputElement);
    });

    it('should have accessible buttons', () => {
      render(<Header />);
      
      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBeGreaterThan(0);
    });
  });

  describe('Integration', () => {
    it('should work with ThemeProvider', () => {
      const { useTheme } = require('@/components/ThemeProvider');
      useTheme.mockReturnValue({
        theme: 'dark',
        toggleTheme: jest.fn(),
      });
      
      render(<Header />);
      
      expect(screen.getByText('☀️')).toBeInTheDocument();
    });

    it('should work with tenant store', () => {
      const { useTenantStore } = require('@/store/tenant');
      const setCurrentTenant = jest.fn();
      useTenantStore.mockReturnValue({
        currentTenant: { id: '1', name: 'Test', plan: 'pro', status: 'active' },
        tenants: [{ id: '1', name: 'Test', plan: 'pro', status: 'active' }],
        setCurrentTenant,
      });
      
      render(<Header />);
      
      expect(screen.getByText('Test')).toBeInTheDocument();
    });
  });
});
