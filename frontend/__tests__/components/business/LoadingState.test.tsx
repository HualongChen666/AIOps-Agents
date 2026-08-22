import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LoadingState } from '@/components/LoadingState';

describe('LoadingState Component', () => {
  describe('Loading State', () => {
    it('should render loading spinner when isLoading is true', () => {
      render(
        <LoadingState isLoading={true}>
          <div>Content</div>
        </LoadingState>
      );

      expect(screen.getByText('加载中...')).toBeInTheDocument();
    });

    it('should render custom loading message', () => {
      render(
        <LoadingState isLoading={true} loadingMessage="Custom loading...">
          <div>Content</div>
        </LoadingState>
      );

      expect(screen.getByText('Custom loading...')).toBeInTheDocument();
    });

    it('should not render children when loading', () => {
      render(
        <LoadingState isLoading={true}>
          <div>Content</div>
        </LoadingState>
    );

      expect(screen.queryByText('Content')).not.toBeInTheDocument();
    });

    it('should render loading spinner with large size', () => {
      render(
        <LoadingState isLoading={true}>
          <div>Content</div>
        </LoadingState>
      );

      const spinner = document.querySelector('.animate-spin');
      expect(spinner).toBeInTheDocument();
    });
  });

  describe('Error State', () => {
    it('should render error message when error is provided', () => {
      render(
        <LoadingState
          isLoading={false}
          error={new Error('Test error')}
        >
          <div>Content</div>
        </LoadingState>
      );

      expect(screen.getByText('加载失败')).toBeInTheDocument();
    });

    it('should render custom error message', () => {
      render(
        <LoadingState
          isLoading={false}
          error={new Error('Test error')}
          errorMessage="Custom error message"
        >
          <div>Content</div>
        </LoadingState>
      );

      expect(screen.getByText('Custom error message')).toBeInTheDocument();
    });

    it('should render retry button when onRetry is provided', () => {
      render(
        <LoadingState
          isLoading={false}
          error={new Error('Test error')}
          onRetry={jest.fn()}
        >
          <div>Content</div>
        </LoadingState>
      );

      expect(screen.getByText('重试')).toBeInTheDocument();
    });

    it('should not render retry button when onRetry is not provided', () => {
      render(
        <LoadingState
          isLoading={false}
          error={new Error('Test error')}
        >
          <div>Content</div>
        </LoadingState>
      );

      expect(screen.queryByText('重试')).not.toBeInTheDocument();
    });

    it('should call onRetry when retry button is clicked', async () => {
      const user = userEvent.setup();
      const handleRetry = jest.fn();
      
      render(
        <LoadingState
          isLoading={false}
          error={new Error('Test error')}
          onRetry={handleRetry}
        >
          <div>Content</div>
        </LoadingState>
      );

      const retryButton = screen.getByText('重试');
      await user.click(retryButton);

      expect(handleRetry).toHaveBeenCalledTimes(1);
    });

    it('should not render children when error', () => {
      render(
        <LoadingState
          isLoading={false}
          error={new Error('Test error')}
        >
          <div>Content</div>
        </LoadingState>
      );

      expect(screen.queryByText('Content')).not.toBeInTheDocument();
    });
  });

  describe('Success State', () => {
    it('should render children when not loading and no error', () => {
      render(
        <LoadingState isLoading={false}>
          <div>Content</div>
        </LoadingState>
      );

      expect(screen.getByText('Content')).toBeInTheDocument();
    });

    it('should not render loading spinner', () => {
      render(
        <LoadingState isLoading={false}>
          <div>Content</div>
        </LoadingState>
      );

      expect(screen.queryByText('加载中...')).not.toBeInTheDocument();
    });

    it('should not render error message', () => {
      render(
        <LoadingState isLoading={false}>
          <div>Content</div>
        </LoadingState>
      );

      expect(screen.queryByText('加载失败')).not.toBeInTheDocument();
    });
  });

  describe('Styling', () => {
    it('should apply correct container styles in loading state', () => {
      render(
        <LoadingState isLoading={true}>
          <div>Content</div>
        </LoadingState>
      );

      const container = screen.getByText('加载中...').closest('div');
      expect(container).toHaveClass('flex');
      expect(container).toHaveClass('flex-col');
      expect(container).toHaveClass('items-center');
    });

    it('should apply correct container styles in error state', () => {
      render(
        <LoadingState
          isLoading={false}
          error={new Error('Test error')}
        >
          <div>Content</div>
        </LoadingState>
      );

      const container = screen.getByText('加载失败').closest('div');
      expect(container).toHaveClass('flex');
      expect(container).toHaveClass('flex-col');
    });
  });

  describe('Edge Cases', () => {
    it('should handle null error', () => {
      render(
        <LoadingState isLoading={false} error={null}>
          <div>Content</div>
        </LoadingState>
      );

      expect(screen.getByText('Content')).toBeInTheDocument();
    });

    it('should handle undefined error', () => {
      render(
        <LoadingState isLoading={false} error={undefined}>
          <div>Content</div>
        </LoadingState>
    );

      expect(screen.getByText('Content')).toBeInTheDocument();
    });

    it('should handle complex children', () => {
      render(
        <LoadingState isLoading={false}>
          <div>
            <span>Complex</span>
            <span>Content</span>
          </div>
        </LoadingState>
      );

      expect(screen.getByText('Complex')).toBeInTheDocument();
      expect(screen.getByText('Content')).toBeInTheDocument();
    });

    it('should handle state transitions', async () => {
      const { rerender } = render(
        <LoadingState isLoading={true}>
          <div>Content</div>
        </LoadingState>
      );

      expect(screen.getByText('加载中...')).toBeInTheDocument();

      rerender(
        <LoadingState isLoading={false}>
          <div>Content</div>
        </LoadingState>
      );

      expect(screen.getByText('Content')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have accessible loading message', () => {
      render(
        <LoadingState isLoading={true}>
          <div>Content</div>
        </LoadingState>
      );

      expect(screen.getByText('加载中...')).toBeVisible();
    });

    it('should have accessible error message', () => {
      render(
        <LoadingState
          isLoading={false}
          error={new Error('Test error')}
        >
          <div>Content</div>
        </LoadingState>
      );

      expect(screen.getByText('加载失败')).toBeVisible();
    });

    it('should have accessible retry button', () => {
      render(
        <LoadingState
          isLoading={false}
          error={new Error('Test error')}
          onRetry={jest.fn()}
        >
          <div>Content</div>
        </LoadingState>
      );

      const retryButton = screen.getByText('重试');
      expect(retryButton).toBeInstanceOf(HTMLButtonElement);
    });
  });

  describe('Integration', () => {
    it('should work with LoadingSpinner component', () => {
      render(
        <LoadingState isLoading={true}>
          <div>Content</div>
        </LoadingState>
      );

      // LoadingSpinner should be rendered
      expect(screen.getByText('加载中...')).toBeInTheDocument();
    });

    it('should handle rapid state changes', () => {
      const { rerender } = render(
        <LoadingState isLoading={true}>
          <div>Content</div>
        </LoadingState>
      );

      rerender(
        <LoadingState isLoading={false} error={new Error('Error')}>
          <div>Content</div>
        </LoadingState>
      );

      rerender(
        <LoadingState isLoading={false}>
          <div>Content</div>
        </LoadingState>
      );

      expect(screen.getByText('Content')).toBeInTheDocument();
    });
  });
});
