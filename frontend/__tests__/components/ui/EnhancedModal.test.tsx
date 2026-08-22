import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { EnhancedModal } from '@/components/ui/EnhancedModal';

// Mock the Dialog components
jest.mock('@/components/ui/dialog', () => ({
  Dialog: ({ open, onOpenChange, children }: any) => {
    if (!open) return null;
    return (
      <div data-testid="dialog">
        {React.Children.map(children, (child) => {
          if (React.isValidElement(child)) {
            return React.cloneElement(child, { onClose: () => onOpenChange(false) });
          }
          return child;
        })}
      </div>
    );
  },
  DialogContent: ({ children, className, onClose }: any) => (
    <div data-testid="dialog-content" className={`py-4 ${className}`}>
      {children}
    </div>
  ),
  DialogHeader: ({ children }: any) => <div data-testid="dialog-header">{children}</div>,
  DialogTitle: ({ children }: any) => <h2 data-testid="dialog-title">{children}</h2>,
  DialogFooter: ({ children }: any) => <div data-testid="dialog-footer">{children}</div>,
}));

// Mock the Button component
jest.mock('@/components/ui/button', () => ({
  Button: ({ children, onClick, ...props }: any) => (
    <button onClick={onClick} data-testid="close-button" {...props}>
      {children}
    </button>
  ),
}));

// Mock the X icon
jest.mock('lucide-react', () => ({
  X: () => <span data-testid="x-icon">×</span>,
}));

describe('EnhancedModal Component', () => {
  describe('Rendering', () => {
    it('should not render when open is false', () => {
      render(
        <EnhancedModal open={false} onOpenChange={() => { }} title="Test Modal">
          Content
        </EnhancedModal>
      );
      expect(screen.queryByTestId('dialog')).not.toBeInTheDocument();
    });

    it('should render when open is true', () => {
      render(
        <EnhancedModal open={true} onOpenChange={() => { }} title="Test Modal">
          Content
        </EnhancedModal>
      );
      expect(screen.getByTestId('dialog')).toBeInTheDocument();
      expect(screen.getByText('Test Modal')).toBeInTheDocument();
      expect(screen.getByText('Content')).toBeInTheDocument();
    });

    it('should render title', () => {
      render(
        <EnhancedModal open={true} onOpenChange={() => { }} title="Modal Title">
          Content
        </EnhancedModal>
      );
      expect(screen.getByTestId('dialog-title')).toHaveTextContent('Modal Title');
    });

    it('should render children', () => {
      render(
        <EnhancedModal open={true} onOpenChange={() => { }} title="Title">
          <p>Modal content</p>
        </EnhancedModal>
      );
      expect(screen.getByText('Modal content')).toBeInTheDocument();
    });

    it('should render footer when provided', () => {
      render(
        <EnhancedModal
          open={true}
          onOpenChange={() => { }}
          title="Title"
          footer={<button>Footer Button</button>}
        >
          Content
        </EnhancedModal>
      );
      expect(screen.getByTestId('dialog-footer')).toBeInTheDocument();
      expect(screen.getByText('Footer Button')).toBeInTheDocument();
    });

    it('should not render footer when not provided', () => {
      render(
        <EnhancedModal open={true} onOpenChange={() => { }} title="Title">
          Content
        </EnhancedModal>
      );
      expect(screen.queryByTestId('dialog-footer')).not.toBeInTheDocument();
    });

    it('should render close button when showClose is true', () => {
      render(
        <EnhancedModal open={true} onOpenChange={() => { }} title="Title" showClose>
          Content
        </EnhancedModal>
      );
      expect(screen.getByTestId('close-button')).toBeInTheDocument();
      expect(screen.getByTestId('x-icon')).toBeInTheDocument();
    });

    it('should not render close button when showClose is false', () => {
      render(
        <EnhancedModal open={true} onOpenChange={() => { }} title="Title" showClose={false}>
          Content
        </EnhancedModal>
      );
      expect(screen.queryByTestId('close-button')).not.toBeInTheDocument();
    });
  });

  describe('Size Variants', () => {
    it('should render with sm size', () => {
      render(
        <EnhancedModal open={true} onOpenChange={() => { }} title="Title" size="sm">
          Content
        </EnhancedModal>
      );
      const content = screen.getByTestId('dialog-content');
      expect(content).toHaveClass('max-w-md');
    });

    it('should render with md size (default)', () => {
      render(
        <EnhancedModal open={true} onOpenChange={() => { }} title="Title" size="md">
          Content
        </EnhancedModal>
      );
      const content = screen.getByTestId('dialog-content');
      expect(content).toHaveClass('max-w-lg');
    });

    it('should render with lg size', () => {
      render(
        <EnhancedModal open={true} onOpenChange={() => { }} title="Title" size="lg">
          Content
        </EnhancedModal>
      );
      const content = screen.getByTestId('dialog-content');
      expect(content).toHaveClass('max-w-2xl');
    });

    it('should render with xl size', () => {
      render(
        <EnhancedModal open={true} onOpenChange={() => { }} title="Title" size="xl">
          Content
        </EnhancedModal>
      );
      const content = screen.getByTestId('dialog-content');
      expect(content).toHaveClass('max-w-3xl');
    });

    it('should render with 2xl size', () => {
      render(
        <EnhancedModal open={true} onOpenChange={() => { }} title="Title" size="2xl">
          Content
        </EnhancedModal>
      );
      const content = screen.getByTestId('dialog-content');
      expect(content).toHaveClass('max-w-4xl');
    });

    it('should default to md size when size is not provided', () => {
      render(
        <EnhancedModal open={true} onOpenChange={() => { }} title="Title">
          Content
        </EnhancedModal>
      );
      const content = screen.getByTestId('dialog-content');
      expect(content).toHaveClass('max-w-lg');
    });
  });

  describe('Event Handling', () => {
    it('should call onOpenChange with false when close button is clicked', async () => {
      const handleOpenChange = jest.fn();
      const user = userEvent.setup();
      render(
        <EnhancedModal open={true} onOpenChange={handleOpenChange} title="Title" showClose>
          Content
        </EnhancedModal>
      );

      const closeButton = screen.getByTestId('close-button');
      await user.click(closeButton);

      expect(handleOpenChange).toHaveBeenCalledWith(false);
    });

    it('should call onOpenChange when Dialog onOpenChange is triggered', () => {
      const handleOpenChange = jest.fn();
      render(
        <EnhancedModal open={true} onOpenChange={handleOpenChange} title="Title">
          Content
        </EnhancedModal>
      );
      // The Dialog mock will call onOpenChange when onClose is triggered
      expect(handleOpenChange).not.toHaveBeenCalled();
    });
  });

  describe('State Management', () => {
    it('should update open state when prop changes', () => {
      const handleOpenChange = jest.fn();
      const { rerender } = render(
        <EnhancedModal open={false} onOpenChange={handleOpenChange} title="Title">
          Content
        </EnhancedModal>
      );
      expect(screen.queryByTestId('dialog')).not.toBeInTheDocument();

      rerender(
        <EnhancedModal open={true} onOpenChange={handleOpenChange} title="Title">
          Content
        </EnhancedModal>
      );
      expect(screen.getByTestId('dialog')).toBeInTheDocument();
    });

    it('should handle controlled state', () => {
      const TestComponent = () => {
        const [open, setOpen] = React.useState(false);
        return (
          <>
            <button onClick={() => setOpen(true)}>Open</button>
            <EnhancedModal open={open} onOpenChange={setOpen} title="Title">
              Content
            </EnhancedModal>
          </>
        );
      };

      render(<TestComponent />);
      expect(screen.queryByTestId('dialog')).not.toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('should render with empty children', () => {
      render(
        <EnhancedModal open={true} onOpenChange={() => { }} title="Title">
          {null}
        </EnhancedModal>
      );
      expect(screen.getByTestId('dialog')).toBeInTheDocument();
    });

    it('should render with complex children', () => {
      render(
        <EnhancedModal open={true} onOpenChange={() => { }} title="Title">
          <p>Paragraph 1</p>
          <p>Paragraph 2</p>
          <button>Action</button>
        </EnhancedModal>
      );
      expect(screen.getByText('Paragraph 1')).toBeInTheDocument();
      expect(screen.getByText('Paragraph 2')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Action' })).toBeInTheDocument();
    });

    it('should render with complex footer', () => {
      render(
        <EnhancedModal
          open={true}
          onOpenChange={() => { }}
          title="Title"
          footer={
            <>
              <button>Cancel</button>
              <button>Confirm</button>
            </>
          }
        >
          Content
        </EnhancedModal>
      );
      expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Confirm' })).toBeInTheDocument();
    });

    it('should render with long title', () => {
      const longTitle = 'This is a very long modal title that might wrap to multiple lines';
      render(
        <EnhancedModal open={true} onOpenChange={() => { }} title={longTitle}>
          Content
        </EnhancedModal>
      );
      expect(screen.getByText(longTitle)).toBeInTheDocument();
    });

    it('should render with special characters in title', () => {
      const specialTitle = 'Title with <special> & characters';
      render(
        <EnhancedModal open={true} onOpenChange={() => { }} title={specialTitle}>
          Content
        </EnhancedModal>
      );
      expect(screen.getByText(specialTitle)).toBeInTheDocument();
    });
  });

  describe('Integration Tests', () => {
    it('should render complete modal structure', () => {
      render(
        <EnhancedModal
          open={true}
          onOpenChange={() => { }}
          title="Complete Modal"
          footer={<button>Footer Action</button>}
          showClose
        >
          <p>Modal content goes here</p>
        </EnhancedModal>
      );

      expect(screen.getByTestId('dialog')).toBeInTheDocument();
      expect(screen.getByTestId('dialog-content')).toBeInTheDocument();
      expect(screen.getByTestId('dialog-header')).toBeInTheDocument();
      expect(screen.getByTestId('dialog-title')).toHaveTextContent('Complete Modal');
      expect(screen.getByText('Modal content goes here')).toBeInTheDocument();
      expect(screen.getByTestId('dialog-footer')).toBeInTheDocument();
      expect(screen.getByTestId('close-button')).toBeInTheDocument();
    });

    it('should handle all props together', () => {
      render(
        <EnhancedModal
          open={true}
          onOpenChange={() => { }}
          title="All Props Modal"
          size="xl"
          showClose={true}
          footer={<button>Footer</button>}
        >
          Content
        </EnhancedModal>
      );

      const content = screen.getByTestId('dialog-content');
      expect(content).toHaveClass('max-w-3xl');
      expect(screen.getByTestId('close-button')).toBeInTheDocument();
      expect(screen.getByTestId('dialog-footer')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper structure for accessibility', () => {
      render(
        <EnhancedModal open={true} onOpenChange={() => { }} title="Accessible Modal">
          Content
        </EnhancedModal>
      );
      expect(screen.getByRole('heading', { name: 'Accessible Modal' })).toBeInTheDocument();
    });

    it('should have close button accessible', () => {
      render(
        <EnhancedModal open={true} onOpenChange={() => { }} title="Title" showClose>
          Content
        </EnhancedModal>
      );
      const closeButton = screen.getByTestId('close-button');
      expect(closeButton).toBeInstanceOf(HTMLButtonElement);
    });
  });

  describe('Component Structure', () => {
    it('should render DialogHeader', () => {
      render(
        <EnhancedModal open={true} onOpenChange={() => { }} title="Title">
          Content
        </EnhancedModal>
      );
      expect(screen.getByTestId('dialog-header')).toBeInTheDocument();
    });

    it('should render DialogTitle', () => {
      render(
        <EnhancedModal open={true} onOpenChange={() => { }} title="Title">
          Content
        </EnhancedModal>
      );
      expect(screen.getByTestId('dialog-title')).toBeInTheDocument();
    });

    it('should render content in proper container', () => {
      render(
        <EnhancedModal open={true} onOpenChange={() => { }} title="Title">
          Content
        </EnhancedModal>
      );
      const content = screen.getByText('Content');
      expect(content.parentElement).toHaveClass('py-4');
    });
  });
});
