import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AICopilot } from '@/components/ai/AICopilot';
import api from '@/lib/api';

// Mock the API module
jest.mock('@/lib/api');
const mockedApi = api as jest.Mocked<typeof api>;

// Mock UI components
jest.mock('@/components/ui/button', () => ({
  Button: ({ children, onClick, disabled, variant, size, className }: any) => (
    <button
      onClick={onClick}
      disabled={disabled}
      className={className}
      data-variant={variant}
      data-size={size}
    >
      {children}
    </button>
  ),
}));

jest.mock('@/components/ui/card', () => ({
  Card: ({ children, className }: any) => <div className={className}>{children}</div>,
  CardContent: ({ children, className }: any) => <div className={className}>{children}</div>,
  CardHeader: ({ children, className }: any) => <div className={className}>{children}</div>,
  CardTitle: ({ children, className }: any) => <div className={className}>{children}</div>,
}));

jest.mock('@/components/ui/input', () => ({
  Input: ({ value, onChange, onKeyPress, disabled, placeholder }: any) => (
    <input
      value={value}
      onChange={onChange}
      onKeyDown={onKeyPress}
      disabled={disabled}
      placeholder={placeholder}
    />
  ),
}));

// Mock react-query
const createTestQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});

const renderWithQueryClient = (component: React.ReactElement) => {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      {component}
    </QueryClientProvider>
  );
};

describe('AICopilot Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should render floating button when closed', () => {
      renderWithQueryClient(<AICopilot />);
      
      const button = screen.getByText('🤖');
      expect(button).toBeInTheDocument();
    });

    it('should render chat interface when open', () => {
      renderWithQueryClient(<AICopilot isOpen={true} />);
      
      expect(screen.getByText('AI Copilot')).toBeInTheDocument();
    });

    it('should render initial greeting message', () => {
      renderWithQueryClient(<AICopilot isOpen={true} />);
      
      expect(screen.getByText(/你好！我是AIOps智能助手/)).toBeInTheDocument();
    });

    it('should render close button when open', () => {
      renderWithQueryClient(<AICopilot isOpen={true} />);
      
      const closeButton = screen.getByText('×');
      expect(closeButton).toBeInTheDocument();
    });

    it('should render input field', () => {
      renderWithQueryClient(<AICopilot isOpen={true} />);
      
      const input = screen.getByPlaceholderText('输入问题...');
      expect(input).toBeInTheDocument();
    });

    it('should render send button', () => {
      renderWithQueryClient(<AICopilot isOpen={true} />);
      
      expect(screen.getByText('发送')).toBeInTheDocument();
    });
  });

  describe('Message Display', () => {
    it('should display user messages', async () => {
      const user = userEvent.setup();
      mockedApi.post.mockResolvedValue({ data: { analysis: 'AI response' } });
      
      renderWithQueryClient(<AICopilot isOpen={true} />);
      
      const input = screen.getByPlaceholderText('输入问题...');
      await user.type(input, 'Test message');
      
      const sendButton = screen.getByText('发送');
      await user.click(sendButton);
      
      await waitFor(() => {
        expect(screen.getByText('Test message')).toBeInTheDocument();
      });
    });

    it('should display assistant messages', async () => {
      const user = userEvent.setup();
      mockedApi.post.mockResolvedValue({ data: { analysis: 'AI response' } });
      
      renderWithQueryClient(<AICopilot isOpen={true} />);
      
      const input = screen.getByPlaceholderText('输入问题...');
      await user.type(input, 'Test');
      
      const sendButton = screen.getByText('发送');
      await user.click(sendButton);
      
      await waitFor(() => {
        expect(screen.getByText('AI response')).toBeInTheDocument();
      });
    });

    it('should display message timestamps', () => {
      renderWithQueryClient(<AICopilot isOpen={true} />);
      
      // Initial message should have timestamp
      const messages = screen.getAllByText(/\d{1,2}:\d{2}:\d{2}/);
      expect(messages.length).toBeGreaterThan(0);
    });
  });

  describe('Quick Actions', () => {
    it('should render quick action buttons', () => {
      renderWithQueryClient(<AICopilot isOpen={true} />);
      
      expect(screen.getByText('分析当前告警')).toBeInTheDocument();
      expect(screen.getByText('系统健康度')).toBeInTheDocument();
      expect(screen.getByText('修复建议')).toBeInTheDocument();
      expect(screen.getByText('容量预测')).toBeInTheDocument();
    });

    it('should populate input when quick action clicked', async () => {
      const user = userEvent.setup();
      renderWithQueryClient(<AICopilot isOpen={true} />);
      
      const quickAction = screen.getByText('分析当前告警');
      await user.click(quickAction);
      
      const input = screen.getByPlaceholderText('输入问题...') as HTMLInputElement;
      expect(input.value).toBe('分析当前告警情况');
    });

    it('should hide quick actions after first message', async () => {
      const user = userEvent.setup();
      mockedApi.post.mockResolvedValue({ data: { analysis: 'Response' } });
      
      renderWithQueryClient(<AICopilot isOpen={true} />);
      
      const input = screen.getByPlaceholderText('输入问题...');
      await user.type(input, 'Test');
      
      const sendButton = screen.getByText('发送');
      await user.click(sendButton);
      
      await waitFor(() => {
        expect(screen.queryByText('快捷操作：')).not.toBeInTheDocument();
      });
    });
  });

  describe('Message Sending', () => {
    it('should send message when send button clicked', async () => {
      const user = userEvent.setup();
      mockedApi.post.mockResolvedValue({ data: { analysis: 'Response' } });
      
      renderWithQueryClient(<AICopilot isOpen={true} />);
      
      const input = screen.getByPlaceholderText('输入问题...');
      await user.type(input, 'Test message');
      
      const sendButton = screen.getByText('发送');
      await user.click(sendButton);
      
      await waitFor(() => {
        expect(mockedApi.post).toHaveBeenCalledWith('/api/ai/analyze', {
          query: 'Test message',
          include_metrics: true,
          include_rich_context: true,
        });
      });
    });

    it('should send message when Enter key pressed', async () => {
      const user = userEvent.setup();
      mockedApi.post.mockResolvedValue({ data: { analysis: 'Response' } });
      
      renderWithQueryClient(<AICopilot isOpen={true} />);
      
      const input = screen.getByPlaceholderText('输入问题...');
      await user.type(input, 'Test message');
      
      await user.keyboard('{Enter}');
      
      await waitFor(() => {
        expect(mockedApi.post).toHaveBeenCalled();
      });
    });

    it('should not send empty message', async () => {
      const user = userEvent.setup();
      renderWithQueryClient(<AICopilot isOpen={true} />);
      
      const sendButton = screen.getByText('发送');
      await user.click(sendButton);
      
      expect(mockedApi.post).not.toHaveBeenCalled();
    });

    it('should not send message when loading', async () => {
      const user = userEvent.setup();
      mockedApi.post.mockImplementation(() => new Promise(() => {}));
      
      renderWithQueryClient(<AICopilot isOpen={true} />);
      
      const input = screen.getByPlaceholderText('输入问题...');
      await user.type(input, 'Test');
      
      const sendButton = screen.getByText('发送');
      await user.click(sendButton);
      
      // Try to send again while loading
      await user.click(sendButton);
      
      // Should only call once
      await waitFor(() => {
        expect(mockedApi.post).toHaveBeenCalledTimes(1);
      });
    });
  });

  describe('Loading State', () => {
    it('should show loading indicator while sending', async () => {
      const user = userEvent.setup();
      mockedApi.post.mockImplementation(() => new Promise(() => {}));
      
      renderWithQueryClient(<AICopilot isOpen={true} />);
      
      const input = screen.getByPlaceholderText('输入问题...');
      await user.type(input, 'Test');
      
      const sendButton = screen.getByText('发送');
      await user.click(sendButton);
      
      // Should show loading dots
      const loadingDots = document.querySelectorAll('.animate-bounce');
      expect(loadingDots.length).toBeGreaterThan(0);
    });

    it('should disable input while loading', async () => {
      const user = userEvent.setup();
      mockedApi.post.mockImplementation(() => new Promise(() => {}));
      
      renderWithQueryClient(<AICopilot isOpen={true} />);
      
      const input = screen.getByPlaceholderText('输入问题...');
      await user.type(input, 'Test');
      
      const sendButton = screen.getByText('发送');
      await user.click(sendButton);
      
      const inputAfter = screen.getByPlaceholderText('输入问题...') as HTMLInputElement;
      expect(inputAfter).toBeDisabled();
    });

    it('should disable send button while loading', async () => {
      const user = userEvent.setup();
      mockedApi.post.mockImplementation(() => new Promise(() => {}));
      
      renderWithQueryClient(<AICopilot isOpen={true} />);
      
      const input = screen.getByPlaceholderText('输入问题...');
      await user.type(input, 'Test');
      
      const sendButton = screen.getByText('发送');
      await user.click(sendButton);
      
      expect(sendButton).toBeDisabled();
    });
  });

  describe('Error Handling', () => {
    it('should display error message when API fails', async () => {
      const user = userEvent.setup();
      mockedApi.post.mockRejectedValue(new Error('API Error'));
      
      renderWithQueryClient(<AICopilot isOpen={true} />);
      
      const input = screen.getByPlaceholderText('输入问题...');
      await user.type(input, 'Test');
      
      const sendButton = screen.getByText('发送');
      await user.click(sendButton);
      
      await waitFor(() => {
        expect(screen.getByText(/AI 分析失败/)).toBeInTheDocument();
      });
    });

    it('should display error details from response', async () => {
      const user = userEvent.setup();
      const error = {
        response: {
          data: {
            detail: 'Specific error message',
          },
        },
      };
      mockedApi.post.mockRejectedValue(error);
      
      renderWithQueryClient(<AICopilot isOpen={true} />);
      
      const input = screen.getByPlaceholderText('输入问题...');
      await user.type(input, 'Test');
      
      const sendButton = screen.getByText('发送');
      await user.click(sendButton);
      
      await waitFor(() => {
        expect(screen.getByText('Specific error message')).toBeInTheDocument();
      });
    });
  });

  describe('Response Handling', () => {
    it('should handle string response', async () => {
      const user = userEvent.setup();
      mockedApi.post.mockResolvedValue({ data: { analysis: 'String response' } });
      
      renderWithQueryClient(<AICopilot isOpen={true} />);
      
      const input = screen.getByPlaceholderText('输入问题...');
      await user.type(input, 'Test');
      
      const sendButton = screen.getByText('发送');
      await user.click(sendButton);
      
      await waitFor(() => {
        expect(screen.getByText('String response')).toBeInTheDocument();
      });
    });

    it('should handle object response with recommended_action', async () => {
      const user = userEvent.setup();
      mockedApi.post.mockResolvedValue({
        data: {
          analysis: {
            recommended_action: 'Recommended action text',
          },
        },
      });
      
      renderWithQueryClient(<AICopilot isOpen={true} />);
      
      const input = screen.getByPlaceholderText('输入问题...');
      await user.type(input, 'Test');
      
      const sendButton = screen.getByText('发送');
      await user.click(sendButton);
      
      await waitFor(() => {
        expect(screen.getByText('Recommended action text')).toBeInTheDocument();
      });
    });

    it('should handle object response by stringifying', async () => {
      const user = userEvent.setup();
      mockedApi.post.mockResolvedValue({
        data: {
          analysis: {
            field1: 'value1',
            field2: 'value2',
          },
        },
      });
      
      renderWithQueryClient(<AICopilot isOpen={true} />);
      
      const input = screen.getByPlaceholderText('输入问题...');
      await user.type(input, 'Test');
      
      const sendButton = screen.getByText('发送');
      await user.click(sendButton);
      
      await waitFor(() => {
        expect(screen.getByText(/field1/)).toBeInTheDocument();
      });
    });
  });

  describe('Toggle Functionality', () => {
    it('should open when floating button clicked', async () => {
      const user = userEvent.setup();
      renderWithQueryClient(<AICopilot />);
      
      const floatingButton = screen.getByText('🤖');
      await user.click(floatingButton);
      
      expect(screen.getByText('AI Copilot')).toBeInTheDocument();
    });

    it('should close when close button clicked', async () => {
      const user = userEvent.setup();
      renderWithQueryClient(<AICopilot isOpen={true} />);
      
      const closeButton = screen.getByText('×');
      await user.click(closeButton);
      
      // Should show floating button again
      expect(screen.getByText('🤖')).toBeInTheDocument();
    });
  });

  describe('Styling', () => {
    it('should apply correct floating button styles', () => {
      renderWithQueryClient(<AICopilot />);
      
      const button = screen.getByText('🤖');
      expect(button).toHaveClass('fixed');
      expect(button).toHaveClass('bottom-6');
      expect(button).toHaveClass('right-6');
    });

    it('should apply correct chat interface styles', () => {
      renderWithQueryClient(<AICopilot isOpen={true} />);
      
      const card = screen.getByText('AI Copilot').closest('div');
      expect(card).toHaveClass('fixed');
      expect(card).toHaveClass('bottom-6');
      expect(card).toHaveClass('right-6');
    });
  });

  describe('Accessibility', () => {
    it('should have accessible floating button', () => {
      renderWithQueryClient(<AICopilot />);
      
      const button = screen.getByText('🤖');
      expect(button).toHaveAttribute('title', 'AI Copilot');
    });

    it('should have accessible input', () => {
      renderWithQueryClient(<AICopilot isOpen={true} />);
      
      const input = screen.getByPlaceholderText('输入问题...');
      expect(input).toBeInstanceOf(HTMLInputElement);
    });

    it('should have accessible buttons', () => {
      renderWithQueryClient(<AICopilot isOpen={true} />);
      
      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBeGreaterThan(0);
    });
  });

  describe('Edge Cases', () => {
    it('should handle very long messages', async () => {
      const user = userEvent.setup();
      mockedApi.post.mockResolvedValue({ data: { analysis: 'Response' } });
      
      renderWithQueryClient(<AICopilot isOpen={true} />);
      
      const longMessage = 'A'.repeat(1000);
      const input = screen.getByPlaceholderText('输入问题...');
      await user.type(input, longMessage);
      
      const sendButton = screen.getByText('发送');
      await user.click(sendButton);
      
      await waitFor(() => {
        expect(mockedApi.post).toHaveBeenCalled();
      });
    });

    it('should handle special characters in messages', async () => {
      const user = userEvent.setup();
      mockedApi.post.mockResolvedValue({ data: { analysis: 'Response' } });
      
      renderWithQueryClient(<AICopilot isOpen={true} />);
      
      const input = screen.getByPlaceholderText('输入问题...');
      await user.type(input, 'Test @#$%^&*()');
      
      const sendButton = screen.getByText('发送');
      await user.click(sendButton);
      
      await waitFor(() => {
        expect(mockedApi.post).toHaveBeenCalled();
      });
    });

    it('should handle empty response', async () => {
      const user = userEvent.setup();
      mockedApi.post.mockResolvedValue({ data: { analysis: null } });
      
      renderWithQueryClient(<AICopilot isOpen={true} />);
      
      const input = screen.getByPlaceholderText('输入问题...');
      await user.type(input, 'Test');
      
      const sendButton = screen.getByText('发送');
      await user.click(sendButton);
      
      await waitFor(() => {
        expect(screen.getByText('AI 分析完成')).toBeInTheDocument();
      });
    });
  });
});
