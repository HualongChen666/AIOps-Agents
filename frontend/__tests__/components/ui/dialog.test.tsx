import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';

describe('Dialog Component', () => {
  describe('Dialog', () => {
    describe('Rendering', () => {
      it('should not render when open is false', () => {
        render(
          <Dialog open={false}>
            <DialogContent>Content</DialogContent>
          </Dialog>
        );
        expect(screen.queryByText('Content')).not.toBeInTheDocument();
      });

      it('should render when open is true', () => {
        render(
          <Dialog open={true}>
            <DialogContent>Content</DialogContent>
          </Dialog>
        );
        expect(screen.getByText('Content')).toBeInTheDocument();
      });

      it('should render with default open state', () => {
        render(
          <Dialog>
            <DialogContent>Content</DialogContent>
          </Dialog>
        );
        expect(screen.queryByText('Content')).not.toBeInTheDocument();
      });

      it('should render backdrop overlay', () => {
        render(
          <Dialog open={true}>
            <DialogContent>Content</DialogContent>
          </Dialog>
        );
        const backdrop = document.querySelector('.bg-black\\/50');
        expect(backdrop).toBeInTheDocument();
      });

      it('should render dialog centered', () => {
        render(
          <Dialog open={true}>
            <DialogContent>Content</DialogContent>
          </Dialog>
        );
        const container = document.querySelector('.fixed.inset-0');
        expect(container).toHaveClass('flex', 'items-center', 'justify-center');
      });
    });

    describe('State Management', () => {
      it('should update open state when prop changes', () => {
        const { rerender } = render(
          <Dialog open={false}>
            <DialogContent>Content</DialogContent>
          </Dialog>
        );
        expect(screen.queryByText('Content')).not.toBeInTheDocument();

        rerender(
          <Dialog open={true}>
            <DialogContent>Content</DialogContent>
          </Dialog>
        );
        expect(screen.getByText('Content')).toBeInTheDocument();
      });

      it('should call onOpenChange when backdrop is clicked', async () => {
        const handleOpenChange = jest.fn();
        const user = userEvent.setup();
        render(
          <Dialog open={true} onOpenChange={handleOpenChange}>
            <DialogContent>Content</DialogContent>
          </Dialog>
        );

        const backdrop = document.querySelector('.bg-black\\/50') as HTMLElement;
        await user.click(backdrop);

        expect(handleOpenChange).toHaveBeenCalledWith(false);
      });

      it('should call onOpenChange when close button is clicked', async () => {
        const handleOpenChange = jest.fn();
        const user = userEvent.setup();
        render(
          <Dialog open={true} onOpenChange={handleOpenChange}>
            <DialogContent>Content</DialogContent>
          </Dialog>
        );

        const closeButton = screen.getByRole('button');
        await user.click(closeButton);

        expect(handleOpenChange).toHaveBeenCalledWith(false);
      });

      it('should handle controlled state', () => {
        const TestComponent = () => {
          const [open, setOpen] = React.useState(false);
          return (
            <>
              <button onClick={() => setOpen(true)}>Open</button>
              <Dialog open={open} onOpenChange={setOpen}>
                <DialogContent>Content</DialogContent>
              </Dialog>
            </>
          );
        };

        render(<TestComponent />);
        expect(screen.queryByText('Content')).not.toBeInTheDocument();

        fireEvent.click(screen.getByRole('button', { name: 'Open' }));
        expect(screen.getByText('Content')).toBeInTheDocument();
      });
    });

    describe('Edge Cases', () => {
      it('should handle null children', () => {
        render(
          <Dialog open={true}>
            {null}
          </Dialog>
        );
        const container = document.querySelector('.fixed.inset-0');
        expect(container).toBeInTheDocument();
      });

      it('should handle undefined children', () => {
        render(
          <Dialog open={true}>
            {undefined}
          </Dialog>
        );
        const container = document.querySelector('.fixed.inset-0');
        expect(container).toBeInTheDocument();
      });

      it('should handle multiple children', () => {
        render(
          <Dialog open={true}>
            <DialogContent>Content 1</DialogContent>
            <DialogContent>Content 2</DialogContent>
          </Dialog>
        );
        expect(screen.getByText('Content 1')).toBeInTheDocument();
        expect(screen.getByText('Content 2')).toBeInTheDocument();
      });

      it('should handle non-ReactElement children', () => {
        render(
          <Dialog open={true}>
            <div>Plain div</div>
          </Dialog>
        );
        expect(screen.getByText('Plain div')).toBeInTheDocument();
      });
    });
  });

  describe('DialogContent', () => {
    describe('Rendering', () => {
      it('should render content with default styles', () => {
        render(
          <Dialog open={true}>
            <DialogContent>Content</DialogContent>
          </Dialog>
        );
        const content = screen.getByText('Content').parentElement;
        expect(content).toHaveClass('relative', 'z-50', 'w-full', 'max-w-lg', 'rounded-lg', 'border', 'border-gray-200', 'bg-white', 'p-6', 'shadow-lg');
      });

      it('should render content with custom className', () => {
        render(
          <Dialog open={true}>
            <DialogContent className="custom-class">Content</DialogContent>
          </Dialog>
        );
        const content = screen.getByText('Content').parentElement;
        expect(content).toHaveClass('custom-class');
      });

      it('should render close button', () => {
        render(
          <Dialog open={true}>
            <DialogContent>Content</DialogContent>
          </Dialog>
        );
        const closeButton = screen.getByRole('button');
        expect(closeButton).toBeInTheDocument();
        expect(closeButton).toHaveClass('absolute', 'right-4', 'top-4');
      });

      it('should render close button with X icon', () => {
        render(
          <Dialog open={true}>
            <DialogContent>Content</DialogContent>
          </Dialog>
        );
        const closeButton = screen.getByRole('button');
        const svg = closeButton.querySelector('svg');
        expect(svg).toBeInTheDocument();
        expect(svg).toHaveClass('h-4', 'w-4');
      });

      it('should render complex children', () => {
        render(
          <Dialog open={true}>
            <DialogContent>
              <p>Paragraph 1</p>
              <p>Paragraph 2</p>
              <button>Action</button>
            </DialogContent>
          </Dialog>
        );
        expect(screen.getByText('Paragraph 1')).toBeInTheDocument();
        expect(screen.getByText('Paragraph 2')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Action' })).toBeInTheDocument();
      });
    });

    describe('Event Handling', () => {
      it('should call onClose when close button is clicked', async () => {
        const handleClose = jest.fn();
        const user = userEvent.setup();
        render(
          <Dialog open={true}>
            <DialogContent onClose={handleClose}>Content</DialogContent>
          </Dialog>
        );

        const closeButton = screen.getByRole('button');
        await user.click(closeButton);

        expect(handleClose).toHaveBeenCalledTimes(1);
      });

      it('should not propagate click from close button to content', async () => {
        const handleContentClick = jest.fn();
        const user = userEvent.setup();
        render(
          <Dialog open={true}>
            <DialogContent onClick={handleContentClick}>Content</DialogContent>
          </Dialog>
        );

        const closeButton = screen.getByRole('button');
        await user.click(closeButton);

        expect(handleContentClick).not.toHaveBeenCalled();
      });
    });

    describe('Edge Cases', () => {
      it('should render with empty children', () => {
        render(
          <Dialog open={true}>
            <DialogContent></DialogContent>
          </Dialog>
        );
        const content = document.querySelector('.max-w-lg');
        expect(content).toBeInTheDocument();
      });

      it('should render with null children', () => {
        render(
          <Dialog open={true}>
            <DialogContent>{null}</DialogContent>
          </Dialog>
        );
        const content = document.querySelector('.max-w-lg');
        expect(content).toBeInTheDocument();
      });
    });
  });

  describe('DialogHeader', () => {
    describe('Rendering', () => {
      it('should render header with default styles', () => {
        render(
          <Dialog open={true}>
            <DialogContent>
              <DialogHeader>Header</DialogHeader>
            </DialogContent>
          </Dialog>
        );
        const header = screen.getByText('Header').parentElement;
        expect(header).toHaveClass('mb-4');
      });

      it('should render header with custom className', () => {
        render(
          <Dialog open={true}>
            <DialogContent>
              <DialogHeader className="custom-class">Header</DialogHeader>
            </DialogContent>
          </Dialog>
        );
        const header = screen.getByText('Header').parentElement;
        expect(header).toHaveClass('custom-class');
      });

      it('should render header with title', () => {
        render(
          <Dialog open={true}>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Title</DialogTitle>
              </DialogHeader>
            </DialogContent>
          </Dialog>
        );
        expect(screen.getByText('Title')).toBeInTheDocument();
      });
    });
  });

  describe('DialogTitle', () => {
    describe('Rendering', () => {
      it('should render title with default styles', () => {
        render(
          <Dialog open={true}>
            <DialogContent>
              <DialogTitle>Dialog Title</DialogTitle>
            </DialogContent>
          </Dialog>
        );
        const title = screen.getByText('Dialog Title');
        expect(title).toHaveClass('text-lg', 'font-semibold', 'text-gray-900');
        expect(title.tagName).toBe('H2');
      });

      it('should render title with custom className', () => {
        render(
          <Dialog open={true}>
            <DialogContent>
              <DialogTitle className="custom-class">Title</DialogTitle>
            </DialogContent>
          </Dialog>
        );
        const title = screen.getByText('Title');
        expect(title).toHaveClass('custom-class');
      });

      it('should render title with long text', () => {
        const longTitle = 'This is a very long dialog title that might wrap to multiple lines';
        render(
          <Dialog open={true}>
            <DialogContent>
              <DialogTitle>{longTitle}</DialogTitle>
            </DialogContent>
          </Dialog>
        );
        const title = screen.getByText(longTitle);
        expect(title).toBeInTheDocument();
      });
    });
  });

  describe('DialogFooter', () => {
    describe('Rendering', () => {
      it('should render footer with default styles', () => {
        render(
          <Dialog open={true}>
            <DialogContent>
              <DialogFooter>
                <button>Cancel</button>
                <button>Confirm</button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        );
        const footer = screen.getByRole('button', { name: 'Cancel' }).parentElement;
        expect(footer).toHaveClass('mt-6', 'flex', 'justify-end', 'space-x-2');
      });

      it('should render footer with custom className', () => {
        render(
          <Dialog open={true}>
            <DialogContent>
              <DialogFooter className="custom-class">
                <button>Cancel</button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        );
        const footer = screen.getByRole('button', { name: 'Cancel' }).parentElement;
        expect(footer).toHaveClass('custom-class');
      });

      it('should render footer with multiple buttons', () => {
        render(
          <Dialog open={true}>
            <DialogContent>
              <DialogFooter>
                <button>Cancel</button>
                <button>Save</button>
                <button>Delete</button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        );
        expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Save' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Delete' })).toBeInTheDocument();
      });
    });
  });

  describe('Integration Tests', () => {
    it('should render complete dialog structure', () => {
      render(
        <Dialog open={true}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Title</DialogTitle>
            </DialogHeader>
            <p>Content</p>
            <DialogFooter>
              <button>Cancel</button>
              <button>Confirm</button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      );

      expect(screen.getByText('Title')).toBeInTheDocument();
      expect(screen.getByText('Content')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Confirm' })).toBeInTheDocument();
    });

    it('should close dialog when clicking backdrop', async () => {
      const handleOpenChange = jest.fn();
      const user = userEvent.setup();
      render(
        <Dialog open={true} onOpenChange={handleOpenChange}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Title</DialogTitle>
            </DialogHeader>
            <p>Content</p>
          </DialogContent>
        </Dialog>
      );

      const backdrop = document.querySelector('.bg-black\\/50') as HTMLElement;
      await user.click(backdrop);

      expect(handleOpenChange).toHaveBeenCalledWith(false);
    });

    it('should close dialog when clicking close button', async () => {
      const handleOpenChange = jest.fn();
      const user = userEvent.setup();
      render(
        <Dialog open={true} onOpenChange={handleOpenChange}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Title</DialogTitle>
            </DialogHeader>
            <p>Content</p>
          </DialogContent>
        </Dialog>
      );

      const closeButton = screen.getAllByRole('button')[0];
      await user.click(closeButton);

      expect(handleOpenChange).toHaveBeenCalledWith(false);
    });

    it('should not close when clicking content', async () => {
      const handleOpenChange = jest.fn();
      const user = userEvent.setup();
      render(
        <Dialog open={true} onOpenChange={handleOpenChange}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Title</DialogTitle>
            </DialogHeader>
            <p>Content</p>
          </DialogContent>
        </Dialog>
      );

      const content = screen.getByText('Content');
      await user.click(content);

      expect(handleOpenChange).not.toHaveBeenCalled();
    });
  });

  describe('Accessibility', () => {
    it('should have proper z-index for layering', () => {
      render(
        <Dialog open={true}>
          <DialogContent>Content</DialogContent>
        </Dialog>
      );
      const content = screen.getByText('Content').parentElement;
      expect(content).toHaveClass('z-50');
    });

    it('should have close button accessible', () => {
      render(
        <Dialog open={true}>
          <DialogContent>Content</DialogContent>
        </Dialog>
      );
      const closeButton = screen.getByRole('button');
      expect(closeButton).toBeInTheDocument();
    });

    it('should support aria-label on dialog', () => {
      render(
        <Dialog open={true}>
          <DialogContent aria-label="Dialog content">Content</DialogContent>
        </Dialog>
      );
      const content = screen.getByLabelText('Dialog content');
      expect(content).toBeInTheDocument();
    });

    it('should support role attribute', () => {
      render(
        <Dialog open={true}>
          <DialogContent role="dialog">Content</DialogContent>
        </Dialog>
      );
      const content = screen.getByRole('dialog');
      expect(content).toBeInTheDocument();
    });
  });
});
