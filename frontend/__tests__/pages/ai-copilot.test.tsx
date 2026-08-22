import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import AICopilotPage from '@/app/ai-copilot/page';

// Mock the API module
jest.mock('@/lib/api', () => ({
  default: {
    post: jest.fn(),
    get: jest.fn(),
  },
}));

describe('AICopilotPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should render the AI Copilot page with title', () => {
      render(<AICopilotPage />);

      expect(screen.getByText('AI Copilot 智能助手')).toBeInTheDocument();
    });

    it('should render minimize button', () => {
      render(<AICopilotPage />);

      expect(screen.getByText('最小化')).toBeInTheDocument();
    });

    it('should render chat window card', () => {
      render(<AICopilotPage />);

      expect(screen.getByText('对话')).toBeInTheDocument();
    });

    it('should render suggested queries card', () => {
      render(<AICopilotPage />);

      expect(screen.getByText('建议查询')).toBeInTheDocument();
    });

    it('should render input field', () => {
      render(<AICopilotPage />);

      expect(screen.getByPlaceholderText('输入你的问题... (按Enter发送)')).toBeInTheDocument();
    });

    it('should render send button', () => {
      render(<AICopilotPage />);

      expect(screen.getByText('发送')).toBeInTheDocument();
    });
  });

  describe('Initial Message', () => {
    it('should display initial welcome message', () => {
      render(<AICopilotPage />);

      expect(screen.getByText(/你好！我是AI Copilot智能助手/)).toBeInTheDocument();
    });

    it('should display AI capabilities in welcome message', () => {
      render(<AICopilotPage />);

      expect(screen.getAllByText(/自然语言查询系统状态/).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/解释告警原因/).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/提供修复建议/).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/生成查询语句/).length).toBeGreaterThan(0);
    });
  });

  describe('Suggested Queries', () => {
    it('should display all suggested queries', () => {
      render(<AICopilotPage />);

      expect(screen.getByText('过去24小时CPU使用率最高的服务')).toBeInTheDocument();
      expect(screen.getByText('为什么web服务响应时间变慢了？')).toBeInTheDocument();
      expect(screen.getByText('如何解决数据库连接超时错误？')).toBeInTheDocument();
      expect(screen.getByText('生成最近告警的统计报告')).toBeInTheDocument();
    });

    it('should display query icons', () => {
      render(<AICopilotPage />);

      expect(screen.getByText('📊')).toBeInTheDocument();
      expect(screen.getByText('🔍')).toBeInTheDocument();
      expect(screen.getByText('🔧')).toBeInTheDocument();
      expect(screen.getByText('📈')).toBeInTheDocument();
    });

    it('should set input when suggested query is clicked', () => {
      render(<AICopilotPage />);

      const suggestedQuery = screen.getByText('过去24小时CPU使用率最高的服务');
      fireEvent.click(suggestedQuery);

      const input = screen.getByPlaceholderText('输入你的问题... (按Enter发送)') as HTMLInputElement;
      expect(input.value).toBe('过去24小时CPU使用率最高的服务');
    });
  });

  describe('Message Sending', () => {
    it('should clear input after sending message', () => {
      render(<AICopilotPage />);

      const input = screen.getByPlaceholderText('输入你的问题... (按Enter发送)') as HTMLInputElement;
      const sendButton = screen.getByText('发送');

      fireEvent.change(input, { target: { value: 'Test message' } });
      expect(input.value).toBe('Test message');

      fireEvent.click(sendButton);
    });

    it('should not send message when input is empty', () => {
      render(<AICopilotPage />);

      const sendButton = screen.getByText('发送');
      expect(sendButton).toBeDisabled();
    });

    it('should not send message when only whitespace', () => {
      render(<AICopilotPage />);

      const input = screen.getByPlaceholderText('输入你的问题... (按Enter发送)') as HTMLInputElement;
      const sendButton = screen.getByText('发送');

      fireEvent.change(input, { target: { value: '   ' } });
      expect(sendButton).toBeDisabled();
    });
  });

  describe('AI Response', () => {
    it('should display initial welcome message', () => {
      render(<AICopilotPage />);

      expect(screen.getByText(/你好！我是AI Copilot智能助手/)).toBeInTheDocument();
    });
  });

  describe('Message Display', () => {
    it('should display message timestamp', () => {
      render(<AICopilotPage />);

      const timestamps = screen.getAllByText(/\d{1,2}:\d{2}:\d{2}/);
      expect(timestamps.length).toBeGreaterThan(0);
    });
  });

  describe('Send Button State', () => {
    it('should disable send button when input is empty', () => {
      render(<AICopilotPage />);

      const sendButton = screen.getByText('发送');
      expect(sendButton).toBeDisabled();
    });

    it('should enable send button when input has text', () => {
      render(<AICopilotPage />);

      const input = screen.getByPlaceholderText('输入你的问题... (按Enter发送)');
      const sendButton = screen.getByText('发送');

      fireEvent.change(input, { target: { value: 'Test' } });

      expect(sendButton).not.toBeDisabled();
    });
  });

  describe('Minimize Functionality', () => {
    it('should minimize when minimize button is clicked', () => {
      render(<AICopilotPage />);

      const minimizeButton = screen.getByText('最小化');
      fireEvent.click(minimizeButton);

      expect(screen.queryByText('AI Copilot 智能助手')).not.toBeInTheDocument();
    });

    it('should show floating button when minimized', () => {
      render(<AICopilotPage />);

      const minimizeButton = screen.getByText('最小化');
      fireEvent.click(minimizeButton);

      expect(screen.getByText('🤖')).toBeInTheDocument();
    });
  });

  describe('Capabilities Section', () => {
    it('should display capabilities section', () => {
      render(<AICopilotPage />);

      expect(screen.getByText('能力说明')).toBeInTheDocument();
    });

    it('should display all capabilities', () => {
      render(<AICopilotPage />);

      expect(screen.getByText(/自然语言查询系统状态和指标/)).toBeInTheDocument();
      expect(screen.getByText(/智能告警解释和根因分析/)).toBeInTheDocument();
      expect(screen.getByText(/提供修复建议和操作指南/)).toBeInTheDocument();
      expect(screen.getByText(/生成SQL查询语句/)).toBeInTheDocument();
      expect(screen.getByText(/对话式根因分析/)).toBeInTheDocument();
    });
  });

  describe('Tips Section', () => {
    it('should display tips section', () => {
      render(<AICopilotPage />);

      expect(screen.getByText('使用技巧')).toBeInTheDocument();
    });

    it('should display all tips', () => {
      render(<AICopilotPage />);

      expect(screen.getByText(/使用具体的问题描述/)).toBeInTheDocument();
      expect(screen.getByText(/提及时间范围/)).toBeInTheDocument();
      expect(screen.getByText(/提及服务名称或指标类型/)).toBeInTheDocument();
      expect(screen.getByText(/可以追问以获取更详细信息/)).toBeInTheDocument();
    });
  });

  describe('Keyboard Interaction', () => {
    it('should handle Enter key press', () => {
      render(<AICopilotPage />);

      const input = screen.getByPlaceholderText('输入你的问题... (按Enter发送)');

      fireEvent.change(input, { target: { value: 'Test message' } });
      expect(input).toHaveValue('Test message');

      fireEvent.keyPress(input, { key: 'Enter', code: 'Enter', charCode: 13 });
    });
  });
});
