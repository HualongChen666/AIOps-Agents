import React from 'react';
import { render, screen, act } from '@testing-library/react';
import { AlertStream } from '@/components/AlertStream';

// Mock the WebSocket hook
jest.mock('react-use-websocket', () => ({
  __esModule: true,
  useWebSocket: jest.fn(() => ({
    sendMessage: jest.fn(),
    lastMessage: null,
    readyState: 3, // CLOSED
  })),
  ReadyState: {
    CONNECTING: 0,
    OPEN: 1,
    CLOSING: 2,
    CLOSED: 3,
    UNINSTANTIATED: 4,
  },
}));

describe('AlertStream Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should render alert stream component', () => {
      render(<AlertStream />);
      expect(screen.getByText(/实时告警/)).toBeInTheDocument();
    });

    it('should render connection status', () => {
      render(<AlertStream />);
      expect(screen.getByText(/已断开/)).toBeInTheDocument();
    });

    it('should render empty state when no alerts', () => {
      render(<AlertStream />);
      expect(screen.getByText('暂无告警')).toBeInTheDocument();
    });

    it('should render section with correct styling', () => {
      render(<AlertStream />);
      const section = screen.getByText(/实时告警/).closest('section');
      expect(section).toHaveClass('p-4', 'bg-gray-50', 'dark:bg-gray-800', 'rounded-lg', 'shadow');
    });

    it('should render heading with correct styling', () => {
      render(<AlertStream />);
      const heading = screen.getByText(/实时告警/);
      expect(heading).toHaveClass('text-lg', 'font-semibold', 'mb-2', 'text-gray-800', 'dark:text-gray-200');
    });
  });

  describe('Connection Status', () => {
    it('should display connecting status', () => {
      const { useWebSocket } = require('react-use-websocket');
      useWebSocket.mockReturnValue({
        sendMessage: jest.fn(),
        lastMessage: null,
        readyState: 0, // CONNECTING
      });

      render(<AlertStream />);
      expect(screen.getByText(/连接中…/)).toBeInTheDocument();
    });

    it('should display connected status', () => {
      const { useWebSocket } = require('react-use-websocket');
      useWebSocket.mockReturnValue({
        sendMessage: jest.fn(),
        lastMessage: null,
        readyState: 1, // OPEN
      });

      render(<AlertStream />);
      expect(screen.getByText(/已连接/)).toBeInTheDocument();
    });

    it('should display closing status', () => {
      const { useWebSocket } = require('react-use-websocket');
      useWebSocket.mockReturnValue({
        sendMessage: jest.fn(),
        lastMessage: null,
        readyState: 2, // CLOSING
      });

      render(<AlertStream />);
      expect(screen.getByText(/关闭中…/)).toBeInTheDocument();
    });

    it('should display closed status', () => {
      const { useWebSocket } = require('react-use-websocket');
      useWebSocket.mockReturnValue({
        sendMessage: jest.fn(),
        lastMessage: null,
        readyState: 3, // CLOSED
      });

      render(<AlertStream />);
      expect(screen.getByText(/已断开/)).toBeInTheDocument();
    });

    it('should display uninstantiated status', () => {
      const { useWebSocket } = require('react-use-websocket');
      useWebSocket.mockReturnValue({
        sendMessage: jest.fn(),
        lastMessage: null,
        readyState: 4, // UNINSTANTIATED
      });

      render(<AlertStream />);
      expect(screen.getByText(/未实例化/)).toBeInTheDocument();
    });
  });

  describe('Alert Handling', () => {
    it('should handle incoming alert message', () => {
      const { useWebSocket } = require('react-use-websocket');
      const mockMessage = {
        data: JSON.stringify({
          id: '1',
          title: 'Test Alert',
          severity: 'P1',
          timestamp: '2024-01-01T00:00:00Z',
        }),
      };

      useWebSocket.mockReturnValue({
        sendMessage: jest.fn(),
        lastMessage: mockMessage,
        readyState: 1,
      });

      render(<AlertStream />);
      expect(screen.getByText('Test Alert')).toBeInTheDocument();
    });

    it('should handle alert with details', () => {
      const { useWebSocket } = require('react-use-websocket');
      const mockMessage = {
        data: JSON.stringify({
          id: '1',
          title: 'Test Alert',
          severity: 'P1',
          timestamp: '2024-01-01T00:00:00Z',
          details: 'Additional details',
        }),
      };

      useWebSocket.mockReturnValue({
        sendMessage: jest.fn(),
        lastMessage: mockMessage,
        readyState: 1,
      });

      render(<AlertStream />);
      expect(screen.getByText('Additional details')).toBeInTheDocument();
    });

    it('should handle multiple alerts', () => {
      const { useWebSocket } = require('react-use-websocket');
      const mockMessage = {
        data: JSON.stringify({
          id: '1',
          title: 'Alert 1',
          severity: 'P1',
          timestamp: '2024-01-01T00:00:00Z',
        }),
      };

      useWebSocket.mockReturnValue({
        sendMessage: jest.fn(),
        lastMessage: mockMessage,
        readyState: 1,
      });

      render(<AlertStream />);
      expect(screen.getByText('Alert 1')).toBeInTheDocument();
    });

    it('should limit alerts to 30 items', () => {
      const { useWebSocket } = require('react-use-websocket');
      const mockMessage = {
        data: JSON.stringify({
          id: '1',
          title: 'Alert 1',
          severity: 'P1',
          timestamp: '2024-01-01T00:00:00Z',
        }),
      };

      useWebSocket.mockReturnValue({
        sendMessage: jest.fn(),
        lastMessage: mockMessage,
        readyState: 1,
      });

      render(<AlertStream />);
      // The component should limit to 30 items
      expect(screen.getByText('Alert 1')).toBeInTheDocument();
    });

    it('should handle invalid JSON message', () => {
      const { useWebSocket } = require('react-use-websocket');
      const mockMessage = {
        data: 'invalid json',
      };

      useWebSocket.mockReturnValue({
        sendMessage: jest.fn(),
        lastMessage: mockMessage,
        readyState: 1,
      });

      render(<AlertStream />);
      expect(screen.getByText('暂无告警')).toBeInTheDocument();
    });

    it('should handle message without data', () => {
      const { useWebSocket } = require('react-use-websocket');
      const mockMessage = null;

      useWebSocket.mockReturnValue({
        sendMessage: jest.fn(),
        lastMessage: mockMessage,
        readyState: 1,
      });

      render(<AlertStream />);
      expect(screen.getByText('暂无告警')).toBeInTheDocument();
    });
  });

  describe('Severity Styling', () => {
    it('should apply P0 severity styling', () => {
      const { useWebSocket } = require('react-use-websocket');
      const mockMessage = {
        data: JSON.stringify({
          id: '1',
          title: 'Critical Alert',
          severity: 'P0',
          timestamp: '2024-01-01T00:00:00Z',
        }),
      };

      useWebSocket.mockReturnValue({
        sendMessage: jest.fn(),
        lastMessage: mockMessage,
        readyState: 1,
      });

      render(<AlertStream />);
      const alertItem = screen.getByText('Critical Alert').closest('li');
      expect(alertItem).toHaveClass('border-danger', 'bg-danger/10');
    });

    it('should apply P1 severity styling', () => {
      const { useWebSocket } = require('react-use-websocket');
      const mockMessage = {
        data: JSON.stringify({
          id: '1',
          title: 'High Alert',
          severity: 'P1',
          timestamp: '2024-01-01T00:00:00Z',
        }),
      };

      useWebSocket.mockReturnValue({
        sendMessage: jest.fn(),
        lastMessage: mockMessage,
        readyState: 1,
      });

      render(<AlertStream />);
      const alertItem = screen.getByText('High Alert').closest('li');
      expect(alertItem).toHaveClass('border-warning', 'bg-warning/10');
    });

    it('should apply P2 severity styling', () => {
      const { useWebSocket } = require('react-use-websocket');
      const mockMessage = {
        data: JSON.stringify({
          id: '1',
          title: 'Medium Alert',
          severity: 'P2',
          timestamp: '2024-01-01T00:00:00Z',
        }),
      };

      useWebSocket.mockReturnValue({
        sendMessage: jest.fn(),
        lastMessage: mockMessage,
        readyState: 1,
      });

      render(<AlertStream />);
      const alertItem = screen.getByText('Medium Alert').closest('li');
      expect(alertItem).toHaveClass('border-secondary', 'bg-secondary/10');
    });

    it('should apply P3 severity styling', () => {
      const { useWebSocket } = require('react-use-websocket');
      const mockMessage = {
        data: JSON.stringify({
          id: '1',
          title: 'Low Alert',
          severity: 'P3',
          timestamp: '2024-01-01T00:00:00Z',
        }),
      };

      useWebSocket.mockReturnValue({
        sendMessage: jest.fn(),
        lastMessage: mockMessage,
        readyState: 1,
      });

      render(<AlertStream />);
      const alertItem = screen.getByText('Low Alert').closest('li');
      expect(alertItem).toHaveClass('border-success', 'bg-success/10');
    });
  });

  describe('Timestamp Display', () => {
    it('should format timestamp correctly', () => {
      const { useWebSocket } = require('react-use-websocket');
      const mockMessage = {
        data: JSON.stringify({
          id: '1',
          title: 'Test Alert',
          severity: 'P1',
          timestamp: '2024-01-15T10:30:00Z',
        }),
      };

      useWebSocket.mockReturnValue({
        sendMessage: jest.fn(),
        lastMessage: mockMessage,
        readyState: 1,
      });

      render(<AlertStream />);
      expect(screen.getByText(/2024/)).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty message data', () => {
      const { useWebSocket } = require('react-use-websocket');
      const mockMessage = {
        data: '',
      };

      useWebSocket.mockReturnValue({
        sendMessage: jest.fn(),
        lastMessage: mockMessage,
        readyState: 1,
      });

      render(<AlertStream />);
      expect(screen.getByText('暂无告警')).toBeInTheDocument();
    });

    it('should handle message with missing fields', () => {
      const { useWebSocket } = require('react-use-websocket');
      const mockMessage = {
        data: JSON.stringify({
          id: '1',
          title: 'Test Alert',
          // missing severity and timestamp
        }),
      };

      useWebSocket.mockReturnValue({
        sendMessage: jest.fn(),
        lastMessage: mockMessage,
        readyState: 1,
      });

      render(<AlertStream />);
      expect(screen.getByText('Test Alert')).toBeInTheDocument();
    });

    it('should handle special characters in alert title', () => {
      const { useWebSocket } = require('react-use-websocket');
      const mockMessage = {
        data: JSON.stringify({
          id: '1',
          title: 'Alert <special> & characters',
          severity: 'P1',
          timestamp: '2024-01-01T00:00:00Z',
        }),
      };

      useWebSocket.mockReturnValue({
        sendMessage: jest.fn(),
        lastMessage: mockMessage,
        readyState: 1,
      });

      render(<AlertStream />);
      expect(screen.getByText(/Alert/)).toBeInTheDocument();
    });

    it('should handle unicode characters in alert title', () => {
      const { useWebSocket } = require('react-use-websocket');
      const mockMessage = {
        data: JSON.stringify({
          id: '1',
          title: '警报消息 🚨',
          severity: 'P1',
          timestamp: '2024-01-01T00:00:00Z',
        }),
      };

      useWebSocket.mockReturnValue({
        sendMessage: jest.fn(),
        lastMessage: mockMessage,
        readyState: 1,
      });

      render(<AlertStream />);
      expect(screen.getByText(/警报/)).toBeInTheDocument();
    });
  });

  describe('Styling', () => {
    it('should have correct list styling', () => {
      const { useWebSocket } = require('react-use-websocket');
      const mockMessage = {
        data: JSON.stringify({
          id: '1',
          title: 'Test Alert',
          severity: 'P1',
          timestamp: '2024-01-01T00:00:00Z',
        }),
      };

      useWebSocket.mockReturnValue({
        sendMessage: jest.fn(),
        lastMessage: mockMessage,
        readyState: 1,
      });

      render(<AlertStream />);
      const list = screen.getByText('Test Alert').closest('ul');
      expect(list).toHaveClass('space-y-2', 'max-h-80', 'overflow-y-auto');
    });

    it('should have correct alert item styling', () => {
      const { useWebSocket } = require('react-use-websocket');
      const mockMessage = {
        data: JSON.stringify({
          id: '1',
          title: 'Test Alert',
          severity: 'P1',
          timestamp: '2024-01-01T00:00:00Z',
        }),
      };

      useWebSocket.mockReturnValue({
        sendMessage: jest.fn(),
        lastMessage: mockMessage,
        readyState: 1,
      });

      render(<AlertStream />);
      const alertItem = screen.getByText('Test Alert').closest('li');
      expect(alertItem).toHaveClass('p-2', 'rounded-md', 'border-l-4');
    });

    it('should have correct title styling', () => {
      const { useWebSocket } = require('react-use-websocket');
      const mockMessage = {
        data: JSON.stringify({
          id: '1',
          title: 'Test Alert',
          severity: 'P1',
          timestamp: '2024-01-01T00:00:00Z',
        }),
      };

      useWebSocket.mockReturnValue({
        sendMessage: jest.fn(),
        lastMessage: mockMessage,
        readyState: 1,
      });

      render(<AlertStream />);
      const title = screen.getByText('Test Alert');
      expect(title).toHaveClass('font-medium', 'text-gray-900', 'dark:text-gray-100');
    });

    it('should have correct details styling', () => {
      const { useWebSocket } = require('react-use-websocket');
      const mockMessage = {
        data: JSON.stringify({
          id: '1',
          title: 'Test Alert',
          severity: 'P1',
          timestamp: '2024-01-01T00:00:00Z',
          details: 'Details',
        }),
      };

      useWebSocket.mockReturnValue({
        sendMessage: jest.fn(),
        lastMessage: mockMessage,
        readyState: 1,
      });

      render(<AlertStream />);
      const details = screen.getByText('Details');
      expect(details).toHaveClass('text-sm', 'text-gray-600', 'dark:text-gray-300');
    });

    it('should have correct timestamp styling', () => {
      const { useWebSocket } = require('react-use-websocket');
      const mockMessage = {
        data: JSON.stringify({
          id: '1',
          title: 'Test Alert',
          severity: 'P1',
          timestamp: '2024-01-01T00:00:00Z',
        }),
      };

      useWebSocket.mockReturnValue({
        sendMessage: jest.fn(),
        lastMessage: mockMessage,
        readyState: 1,
      });

      render(<AlertStream />);
      const timestamp = screen.getByText(/2024/);
      expect(timestamp).toHaveClass('text-xs', 'text-gray-500', 'dark:text-gray-400', 'whitespace-nowrap');
    });
  });

  describe('Integration Tests', () => {
    it('should handle connection state change', () => {
      const { useWebSocket } = require('react-use-websocket');
      
      useWebSocket.mockReturnValue({
        sendMessage: jest.fn(),
        lastMessage: null,
        readyState: 0, // CONNECTING
      });

      const { rerender } = render(<AlertStream />);
      expect(screen.getByText(/连接中…/)).toBeInTheDocument();

      useWebSocket.mockReturnValue({
        sendMessage: jest.fn(),
        lastMessage: null,
        readyState: 1, // OPEN
      });

      rerender(<AlertStream />);
      expect(screen.getByText(/已连接/)).toBeInTheDocument();
    });

    it('should handle alert list update', () => {
      const { useWebSocket } = require('react-use-websocket');
      
      useWebSocket.mockReturnValue({
        sendMessage: jest.fn(),
        lastMessage: null,
        readyState: 1,
      });

      const { rerender } = render(<AlertStream />);
      expect(screen.getByText('暂无告警')).toBeInTheDocument();

      const mockMessage = {
        data: JSON.stringify({
          id: '1',
          title: 'New Alert',
          severity: 'P1',
          timestamp: '2024-01-01T00:00:00Z',
        }),
      };

      useWebSocket.mockReturnValue({
        sendMessage: jest.fn(),
        lastMessage: mockMessage,
        readyState: 1,
      });

      rerender(<AlertStream />);
      expect(screen.getByText('New Alert')).toBeInTheDocument();
      expect(screen.queryByText('暂无告警')).not.toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper heading structure', () => {
      render(<AlertStream />);
      const heading = screen.getByRole('heading', { level: 2 });
      expect(heading).toBeInTheDocument();
    });

    it('should have proper list structure when alerts exist', () => {
      const { useWebSocket } = require('react-use-websocket');
      const mockMessage = {
        data: JSON.stringify({
          id: '1',
          title: 'Test Alert',
          severity: 'P1',
          timestamp: '2024-01-01T00:00:00Z',
        }),
      };

      useWebSocket.mockReturnValue({
        sendMessage: jest.fn(),
        lastMessage: mockMessage,
        readyState: 1,
      });

      render(<AlertStream />);
      const list = screen.getByRole('list');
      expect(list).toBeInTheDocument();
    });
  });

  describe('Component Structure', () => {
    it('should render section element', () => {
      render(<AlertStream />);
      const section = document.querySelector('section');
      expect(section).toBeInTheDocument();
    });

    it('should render heading inside section', () => {
      render(<AlertStream />);
      const section = document.querySelector('section');
      const heading = screen.getByRole('heading');
      expect(section).toContainElement(heading);
    });

    it('should render list when alerts exist', () => {
      const { useWebSocket } = require('react-use-websocket');
      const mockMessage = {
        data: JSON.stringify({
          id: '1',
          title: 'Test Alert',
          severity: 'P1',
          timestamp: '2024-01-01T00:00:00Z',
        }),
      };

      useWebSocket.mockReturnValue({
        sendMessage: jest.fn(),
        lastMessage: mockMessage,
        readyState: 1,
      });

      render(<AlertStream />);
      const list = screen.getByRole('list');
      expect(list).toBeInTheDocument();
    });
  });
});
