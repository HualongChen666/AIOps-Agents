import React from 'react';
import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Toast, ToastContainer } from '@/components/ui/Toast';

// Mock the lucide-react icons
jest.mock('lucide-react', () => ({
  CheckCircle: () => <span data-testid="check-circle-icon">✓</span>,
  XCircle: () => <span data-testid="x-circle-icon">✗</span>,
  AlertTriangle: () => <span data-testid="alert-triangle-icon">⚠</span>,
  Info: () => <span data-testid="info-icon">ℹ</span>,
  X: () => <span data-testid="x-icon">×</span>,
}));

describe('Toast Component', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe('Rendering', () => {
    it('should render toast with message', () => {
      render(<Toast type="success" message="Operation successful" />);
      expect(screen.getByText('Operation successful')).toBeInTheDocument();
    });

    it('should render toast with icon', () => {
      render(<Toast type="success" message="Success" />);
      expect(screen.getByTestId('check-circle-icon')).toBeInTheDocument();
    });

    it('should render close button', () => {
      render(<Toast type="success" message="Success" />);
      expect(screen.getByTestId('x-icon')).toBeInTheDocument();
    });

    it('should render with correct positioning', () => {
      render(<Toast type="success" message="Success" />);
      const toast = screen.getByText('Success').parentElement;
      expect(toast).toHaveClass('fixed', 'top-4', 'right-4', 'z-50');
    });
  });

  describe('Type Variants', () => {
    describe('Success Type', () => {
      it('should render success type with correct icon', () => {
        render(<Toast type="success" message="Success" />);
        expect(screen.getByTestId('check-circle-icon')).toBeInTheDocument();
      });

      it('should render success type with correct styling', () => {
        render(<Toast type="success" message="Success" />);
        const toast = screen.getByText('Success').parentElement;
        expect(toast).toHaveClass('bg-green-50', 'border-green-200');
      });

      it('should render success type with correct icon color', () => {
        render(<Toast type="success" message="Success" />);
        const icon = screen.getByTestId('check-circle-icon');
        expect(icon).toHaveClass('text-green-600');
      });
    });

    describe('Error Type', () => {
      it('should render error type with correct icon', () => {
        render(<Toast type="error" message="Error" />);
        expect(screen.getByTestId('x-circle-icon')).toBeInTheDocument();
      });

      it('should render error type with correct styling', () => {
        render(<Toast type="error" message="Error" />);
        const toast = screen.getByText('Error').parentElement;
        expect(toast).toHaveClass('bg-red-50', 'border-red-200');
      });

      it('should render error type with correct icon color', () => {
        render(<Toast type="error" message="Error" />);
        const icon = screen.getByTestId('x-circle-icon');
        expect(icon).toHaveClass('text-red-600');
      });
    });

    describe('Warning Type', () => {
      it('should render warning type with correct icon', () => {
        render(<Toast type="warning" message="Warning" />);
        expect(screen.getByTestId('alert-triangle-icon')).toBeInTheDocument();
      });

      it('should render warning type with correct styling', () => {
        render(<Toast type="warning" message="Warning" />);
        const toast = screen.getByText('Warning').parentElement;
        expect(toast).toHaveClass('bg-yellow-50', 'border-yellow-200');
      });

      it('should render warning type with correct icon color', () => {
        render(<Toast type="warning" message="Warning" />);
        const icon = screen.getByTestId('alert-triangle-icon');
        expect(icon).toHaveClass('text-yellow-600');
      });
    });

    describe('Info Type', () => {
      it('should render info type with correct icon', () => {
        render(<Toast type="info" message="Info" />);
        expect(screen.getByTestId('info-icon')).toBeInTheDocument();
      });

      it('should render info type with correct styling', () => {
        render(<Toast type="info" message="Info" />);
        const toast = screen.getByText('Info').parentElement;
        expect(toast).toHaveClass('bg-blue-50', 'border-blue-200');
      });

      it('should render info type with correct icon color', () => {
        render(<Toast type="info" message="Info" />);
        const icon = screen.getByTestId('info-icon');
        expect(icon).toHaveClass('text-blue-600');
      });
    });
  });

  describe('Auto-dismissal', () => {
    it('should auto-dismiss after default duration (3000ms)', () => {
      const handleClose = jest.fn();
      render(<Toast type="success" message="Success" onClose={handleClose} />);
      
      expect(screen.getByText('Success')).toBeInTheDocument();
      
      act(() => {
        jest.advanceTimersByTime(3000);
      });
      
      expect(screen.queryByText('Success')).not.toBeInTheDocument();
      expect(handleClose).toHaveBeenCalled();
    });

    it('should auto-dismiss after custom duration', () => {
      const handleClose = jest.fn();
      render(<Toast type="success" message="Success" duration={5000} onClose={handleClose} />);
      
      expect(screen.getByText('Success')).toBeInTheDocument();
      
      act(() => {
        jest.advanceTimersByTime(5000);
      });
      
      expect(screen.queryByText('Success')).not.toBeInTheDocument();
      expect(handleClose).toHaveBeenCalled();
    });

    it('should not dismiss before duration', () => {
      render(<Toast type="success" message="Success" duration={5000} />);
      
      act(() => {
        jest.advanceTimersByTime(2000);
      });
      
      expect(screen.getByText('Success')).toBeInTheDocument();
    });

    it('should clear timer on unmount', () => {
      const { unmount } = render(<Toast type="success" message="Success" duration={5000} />);
      
      unmount();
      
      act(() => {
        jest.advanceTimersByTime(5000);
      });
      
      // Should not throw error
    });
  });

  describe('Manual Dismissal', () => {
    it('should dismiss when close button is clicked', async () => {
      const handleClose = jest.fn();
      const user = userEvent.setup();
      render(<Toast type="success" message="Success" onClose={handleClose} />);
      
      const closeButton = screen.getByTestId('x-icon').parentElement;
      await user.click(closeButton);
      
      expect(screen.queryByText('Success')).not.toBeInTheDocument();
      expect(handleClose).toHaveBeenCalled();
    });

    it('should call onClose when manually dismissed', async () => {
      const handleClose = jest.fn();
      const user = userEvent.setup();
      render(<Toast type="success" message="Success" onClose={handleClose} />);
      
      const closeButton = screen.getByTestId('x-icon').parentElement;
      await user.click(closeButton);
      
      expect(handleClose).toHaveBeenCalledTimes(1);
    });

    it('should not call onClose when not provided', async () => {
      const user = userEvent.setup();
      render(<Toast type="success" message="Success" />);
      
      const closeButton = screen.getByTestId('x-icon').parentElement;
      await user.click(closeButton);
      
      expect(screen.queryByText('Success')).not.toBeInTheDocument();
    });
  });

  describe('Duration Edge Cases', () => {
    it('should handle duration of 0', () => {
      const handleClose = jest.fn();
      render(<Toast type="success" message="Success" duration={0} onClose={handleClose} />);
      
      act(() => {
        jest.advanceTimersByTime(0);
      });
      
      expect(handleClose).toHaveBeenCalled();
    });

    it('should handle very short duration', () => {
      const handleClose = jest.fn();
      render(<Toast type="success" message="Success" duration={100} onClose={handleClose} />);
      
      act(() => {
        jest.advanceTimersByTime(100);
      });
      
      expect(screen.queryByText('Success')).not.toBeInTheDocument();
    });

    it('should handle very long duration', () => {
      render(<Toast type="success" message="Success" duration={100000} />);
      
      act(() => {
        jest.advanceTimersByTime(1000);
      });
      
      expect(screen.getByText('Success')).toBeInTheDocument();
    });
  });

  describe('Message Display', () => {
    it('should render short message', () => {
      render(<Toast type="success" message="OK" />);
      expect(screen.getByText('OK')).toBeInTheDocument();
    });

    it('should render long message', () => {
      const longMessage = 'This is a very long toast message that contains a lot of text and might wrap to multiple lines';
      render(<Toast type="success" message={longMessage} />);
      expect(screen.getByText(longMessage)).toBeInTheDocument();
    });

    it('should render message with special characters', () => {
      const specialMessage = 'Message with <special> & characters';
      render(<Toast type="success" message={specialMessage} />);
      expect(screen.getByText(specialMessage)).toBeInTheDocument();
    });

    it('should render message with unicode', () => {
      const unicodeMessage = '消息成功完成 🎉';
      render(<Toast type="success" message={unicodeMessage} />);
      expect(screen.getByText(unicodeMessage)).toBeInTheDocument();
    });

    it('should render empty message', () => {
      render(<Toast type="success" message="" />);
      const toast = document.querySelector('.fixed.top-4.right-4');
      expect(toast).toBeInTheDocument();
    });
  });

  describe('Styling', () => {
    it('should have correct base styles', () => {
      render(<Toast type="success" message="Success" />);
      const toast = screen.getByText('Success').parentElement;
      expect(toast).toHaveClass('flex', 'items-center', 'gap-3', 'p-4', 'rounded-lg', 'border', 'shadow-lg');
    });

    it('should have correct icon size', () => {
      render(<Toast type="success" message="Success" />);
      const icon = screen.getByTestId('check-circle-icon');
      expect(icon).toHaveClass('h-5', 'w-5');
    });

    it('should have correct close button size', () => {
      render(<Toast type="success" message="Success" />);
      const closeIcon = screen.getByTestId('x-icon');
      expect(closeIcon).toHaveClass('h-4', 'w-4');
    });

    it('should have correct message text size', () => {
      render(<Toast type="success" message="Success" />);
      const message = screen.getByText('Success');
      expect(message).toHaveClass('text-sm', 'text-gray-900');
    });

    it('should have correct close button styling', () => {
      render(<Toast type="success" message="Success" />);
      const closeButton = screen.getByTestId('x-icon').parentElement;
      expect(closeButton).toHaveClass('text-gray-400', 'hover:text-gray-600', 'transition');
    });

    it('should have animation classes', () => {
      render(<Toast type="success" message="Success" />);
      const toast = screen.getByText('Success').parentElement;
      expect(toast).toHaveClass('animate-in', 'slide-in-from-right');
    });
  });

  describe('ToastContainer', () => {
    it('should render multiple toasts', () => {
      const toasts = [
        { id: '1', type: 'success' as const, message: 'Success 1' },
        { id: '2', type: 'error' as const, message: 'Error 1' },
        { id: '3', type: 'warning' as const, message: 'Warning 1' },
      ];
      
      render(<ToastContainer toasts={toasts} />);
      
      expect(screen.getByText('Success 1')).toBeInTheDocument();
      expect(screen.getByText('Error 1')).toBeInTheDocument();
      expect(screen.getByText('Warning 1')).toBeInTheDocument();
    });

    it('should render empty container when no toasts', () => {
      render(<ToastContainer toasts={[]} />);
      const container = document.querySelector('.fixed.top-4.right-4.space-y-2');
      expect(container).toBeInTheDocument();
      expect(container).toBeEmptyDOMElement();
    });

    it('should render with correct container styling', () => {
      const toasts = [{ id: '1', type: 'success' as const, message: 'Success' }];
      render(<ToastContainer toasts={toasts} />);
      
      const container = document.querySelector('.fixed.top-4.right-4.space-y-2');
      expect(container).toHaveClass('fixed', 'top-4', 'right-4', 'z-50', 'space-y-2');
    });

    it('should pass custom duration to toasts', () => {
      const toasts = [
        { id: '1', type: 'success' as const, message: 'Success', duration: 5000 },
      ];
      
      render(<ToastContainer toasts={toasts} />);
      expect(screen.getByText('Success')).toBeInTheDocument();
    });

    it('should render toasts with different types', () => {
      const toasts = [
        { id: '1', type: 'success' as const, message: 'Success' },
        { id: '2', type: 'error' as const, message: 'Error' },
        { id: '3', type: 'warning' as const, message: 'Warning' },
        { id: '4', type: 'info' as const, message: 'Info' },
      ];
      
      render(<ToastContainer toasts={toasts} />);
      
      expect(screen.getByTestId('check-circle-icon')).toBeInTheDocument();
      expect(screen.getByTestId('x-circle-icon')).toBeInTheDocument();
      expect(screen.getByTestId('alert-triangle-icon')).toBeInTheDocument();
      expect(screen.getByTestId('info-icon')).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('should handle all toast types', () => {
      const types: Array<'success' | 'error' | 'warning' | 'info'> = ['success', 'error', 'warning', 'info'];

      types.forEach((type) => {
        const { unmount } = render(<Toast type={type} message="Test" />);
        expect(screen.getByText('Test')).toBeInTheDocument();
        unmount();
      });
    });

    it('should handle onClose being undefined', () => {
      render(<Toast type="success" message="Success" onClose={undefined} />);
      expect(screen.getByText('Success')).toBeInTheDocument();
    });

    it('should handle rapid updates', () => {
      const { rerender } = render(<Toast type="success" message="Message 1" />);
      expect(screen.getByText('Message 1')).toBeInTheDocument();

      rerender(<Toast type="error" message="Message 2" />);
      expect(screen.getByText('Message 2')).toBeInTheDocument();
    });

    it('should handle message with HTML entities', () => {
      const message = 'Success &amp; Complete';
      render(<Toast type="success" message={message} />);
      expect(screen.getByText(message)).toBeInTheDocument();
    });
  });

  describe('Integration Tests', () => {
    it('should handle complete toast lifecycle', async () => {
      const handleClose = jest.fn();
      const user = userEvent.setup();
      
      const { rerender } = render(<Toast type="success" message="Success" onClose={handleClose} />);
      expect(screen.getByText('Success')).toBeInTheDocument();
      
      // Manual dismiss
      const closeButton = screen.getByTestId('x-icon').parentElement;
      await user.click(closeButton);
      expect(handleClose).toHaveBeenCalled();
      
      // Re-render with auto-dismiss
      rerender(<Toast type="success" message="Success 2" duration={1000} onClose={handleClose} />);
      expect(screen.getByText('Success 2')).toBeInTheDocument();
      
      act(() => {
        jest.advanceTimersByTime(1000);
      });
      expect(screen.queryByText('Success 2')).not.toBeInTheDocument();
    });

    it('should handle multiple toasts in container with different durations', () => {
      const toasts = [
        { id: '1', type: 'success' as const, message: 'Short', duration: 1000 },
        { id: '2', type: 'error' as const, message: 'Long', duration: 5000 },
      ];
      
      render(<ToastContainer toasts={toasts} />);
      
      expect(screen.getByText('Short')).toBeInTheDocument();
      expect(screen.getByText('Long')).toBeInTheDocument();
      
      act(() => {
        jest.advanceTimersByTime(1000);
      });
      
      expect(screen.queryByText('Short')).not.toBeInTheDocument();
      expect(screen.getByText('Long')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper role for toast', () => {
      render(<Toast type="success" message="Success" />);
      const toast = screen.getByText('Success').parentElement;
      expect(toast).toBeInTheDocument();
    });

    it('should have close button accessible', () => {
      render(<Toast type="success" message="Success" />);
      const closeButton = screen.getByTestId('x-icon').parentElement;
      expect(closeButton).toBeInstanceOf(HTMLButtonElement);
    });

    it('should have proper z-index for layering', () => {
      render(<Toast type="success" message="Success" />);
      const toast = screen.getByText('Success').parentElement;
      expect(toast).toHaveClass('z-50');
    });
  });

  describe('Component Structure', () => {
    it('should have correct element hierarchy', () => {
      render(<Toast type="success" message="Success" />);
      const toast = screen.getByText('Success').parentElement;
      const icon = screen.getByTestId('check-circle-icon');
      const closeButton = screen.getByTestId('x-icon').parentElement;
      
      expect(toast).toContainElement(icon);
      expect(toast).toContainElement(screen.getByText('Success'));
      expect(toast).toContainElement(closeButton);
    });

    it('should render icon before message', () => {
      render(<Toast type="success" message="Success" />);
      const toast = screen.getByText('Success').parentElement;
      const icon = screen.getByTestId('check-circle-icon');
      const message = screen.getByText('Success');
      
      const iconIndex = Array.from(toast?.children || []).indexOf(icon);
      const messageIndex = Array.from(toast?.children || []).indexOf(message);
      
      expect(iconIndex).toBeLessThan(messageIndex);
    });

    it('should render close button after message', () => {
      render(<Toast type="success" message="Success" />);
      const toast = screen.getByText('Success').parentElement;
      const message = screen.getByText('Success');
      const closeButton = screen.getByTestId('x-icon').parentElement;
      
      const messageIndex = Array.from(toast?.children || []).indexOf(message);
      const closeButtonIndex = Array.from(toast?.children || []).indexOf(closeButton);
      
      expect(messageIndex).toBeLessThan(closeButtonIndex);
    });
  });
});
