import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import {
  LoadingSpinner,
  EmptyState,
  ErrorBoundary,
  StatusBadge,
  Card,
  ProgressBar,
  Tooltip,
  Breadcrumb,
  SearchInput,
} from '@/components/CommonUI';

describe('LoadingSpinner', () => {
  it('should render with default size', () => {
    render(<LoadingSpinner />);
    const spinner = document.querySelector('.animate-spin');
    expect(spinner).toHaveClass('w-8', 'h-8');
  });

  it('should render with small size', () => {
    render(<LoadingSpinner size="sm" />);
    const spinner = document.querySelector('.animate-spin');
    expect(spinner).toHaveClass('w-4', 'h-4');
  });

  it('should render with large size', () => {
    render(<LoadingSpinner size="lg" />);
    const spinner = document.querySelector('.animate-spin');
    expect(spinner).toHaveClass('w-12', 'h-12');
  });

  it('should render with custom color', () => {
    render(<LoadingSpinner color="#ff0000" />);
    const circles = document.querySelectorAll('circle, path');
    expect(circles[0]).toHaveAttribute('stroke', '#ff0000');
  });

  it('should render with custom className', () => {
    render(<LoadingSpinner className="custom-class" />);
    const spinner = document.querySelector('.animate-spin');
    expect(spinner).toHaveClass('custom-class');
  });
});

describe('EmptyState', () => {
  it('should render with title', () => {
    render(<EmptyState title="No Data" />);
    expect(screen.getByText('No Data')).toBeInTheDocument();
  });

  it('should render with description', () => {
    render(<EmptyState title="No Data" description="There is no data to display" />);
    expect(screen.getByText('There is no data to display')).toBeInTheDocument();
  });

  it('should render with icon', () => {
    render(<EmptyState title="No Data" icon={<span data-testid="icon">📭</span>} />);
    expect(screen.getByTestId('icon')).toBeInTheDocument();
  });

  it('should render with action button', () => {
    render(<EmptyState title="No Data" action={<button>Retry</button>} />);
    expect(screen.getByText('Retry')).toBeInTheDocument();
  });

  it('should render with custom className', () => {
    const { container } = render(<EmptyState title="No Data" className="custom-class" />);
    expect(container.firstChild).toHaveClass('custom-class');
  });
});

describe('ErrorBoundary', () => {
  it('should render children when no error', () => {
    const ThrowError = () => {
      throw new Error('Test error');
    };

    const { container } = render(
      <ErrorBoundary>
        <div>No Error</div>
      </ErrorBoundary>
    );

    expect(screen.getByText('No Error')).toBeInTheDocument();
  });

  it('should catch and display error', () => {
    const ThrowError = () => {
      throw new Error('Test error');
    };

    const { container } = render(
      <ErrorBoundary>
        <ThrowError />
      </ErrorBoundary>
    );

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });

  it('should use custom fallback when provided', () => {
    const ThrowError = () => {
      throw new Error('Test error');
    };

    render(
      <ErrorBoundary fallback={<div>Custom Error</div>}>
        <ThrowError />
      </ErrorBoundary>
    );

    expect(screen.getByText('Custom Error')).toBeInTheDocument();
  });

  it('should display error message from error object', () => {
    const ThrowError = () => {
      throw new Error('Specific error message');
    };

    render(
      <ErrorBoundary>
        <ThrowError />
      </ErrorBoundary>
    );

    expect(screen.getByText('Specific error message')).toBeInTheDocument();
  });
});

describe('StatusBadge', () => {
  it('should render success badge', () => {
    render(<StatusBadge status="success">Success</StatusBadge>);
    const badge = screen.getByText('Success');
    expect(badge).toHaveClass('bg-green-100', 'text-green-800');
  });

  it('should render warning badge', () => {
    render(<StatusBadge status="warning">Warning</StatusBadge>);
    const badge = screen.getByText('Warning');
    expect(badge).toHaveClass('bg-yellow-100', 'text-yellow-800');
  });

  it('should render error badge', () => {
    render(<StatusBadge status="error">Error</StatusBadge>);
    const badge = screen.getByText('Error');
    expect(badge).toHaveClass('bg-red-100', 'text-red-800');
  });

  it('should render info badge', () => {
    render(<StatusBadge status="info">Info</StatusBadge>);
    const badge = screen.getByText('Info');
    expect(badge).toHaveClass('bg-blue-100', 'text-blue-800');
  });

  it('should render neutral badge', () => {
    render(<StatusBadge status="neutral">Neutral</StatusBadge>);
    const badge = screen.getByText('Neutral');
    expect(badge).toHaveClass('bg-gray-100', 'text-gray-800');
  });

  it('should render with custom className', () => {
    render(<StatusBadge status="success" className="custom-class">
      Success
    </StatusBadge>);
    const badge = screen.getByText('Success');
    expect(badge).toHaveClass('custom-class');
  });
});

describe('Card', () => {
  it('should render children', () => {
    render(<Card>Card Content</Card>);
    expect(screen.getByText('Card Content')).toBeInTheDocument();
  });

  it('should render with custom className', () => {
    const { container } = render(<Card className="custom-class">Content</Card>);
    expect(container.firstChild).toHaveClass('custom-class');
  });

  it('should not be hoverable by default', () => {
    const { container } = render(<Card>Content</Card>);
    expect(container.firstChild).not.toHaveClass('hover:shadow-lg');
  });

  it('should be hoverable when hoverable prop is true', () => {
    const { container } = render(<Card hoverable>Content</Card>);
    expect(container.firstChild).toHaveClass('hover:shadow-lg', 'cursor-pointer');
  });

  it('should call onClick when clicked', () => {
    const handleClick = jest.fn();
    render(<Card onClick={handleClick}>Content</Card>);
    fireEvent.click(screen.getByText('Content'));
    expect(handleClick).toHaveBeenCalled();
  });
});

describe('ProgressBar', () => {
  it('should render with default value', () => {
    render(<ProgressBar value={50} />);
    const bar = document.querySelector('.bg-blue-500');
    expect(bar).toHaveStyle({ width: '50%' });
  });

  it('should render with custom max value', () => {
    render(<ProgressBar value={75} max={150} />);
    const bar = document.querySelector('.bg-blue-500');
    expect(bar).toHaveStyle({ width: '50%' });
  });

  it('should render with custom color', () => {
    render(<ProgressBar value={50} color="bg-red-500" />);
    const bar = document.querySelector('.bg-red-500');
    expect(bar).toBeInTheDocument();
  });

  it('should show label when showLabel is true', () => {
    render(<ProgressBar value={50} max={100} showLabel />);
    expect(screen.getByText('50 / 100')).toBeInTheDocument();
  });

  it('should cap value at 100%', () => {
    render(<ProgressBar value={150} max={100} />);
    const bar = document.querySelector('.bg-blue-500');
    expect(bar).toHaveStyle({ width: '100%' });
  });

  it('should render with custom className', () => {
    const { container } = render(<ProgressBar value={50} className="custom-class" />);
    expect(container.firstChild).toHaveClass('custom-class');
  });
});

describe('Tooltip', () => {
  it('should not show tooltip initially', () => {
    render(<Tooltip content="Tooltip content">Trigger</Tooltip>);
    expect(screen.queryByText('Tooltip content')).not.toBeInTheDocument();
  });

  it('should show tooltip on mouse enter', () => {
    render(<Tooltip content="Tooltip content">Trigger</Tooltip>);
    fireEvent.mouseEnter(screen.getByText('Trigger'));
    expect(screen.getByText('Tooltip content')).toBeInTheDocument();
  });

  it('should hide tooltip on mouse leave', () => {
    render(<Tooltip content="Tooltip content">Trigger</Tooltip>);
    fireEvent.mouseEnter(screen.getByText('Trigger'));
    fireEvent.mouseLeave(screen.getByText('Trigger'));
    expect(screen.queryByText('Tooltip content')).not.toBeInTheDocument();
  });

  it('should position tooltip at top by default', () => {
    render(<Tooltip content="Tooltip content">Trigger</Tooltip>);
    fireEvent.mouseEnter(screen.getByText('Trigger'));
    const tooltip = screen.getByText('Tooltip content').parentElement;
    expect(tooltip).toHaveClass('bottom-full', 'mb-2');
  });

  it('should position tooltip at bottom when specified', () => {
    render(<Tooltip content="Tooltip content" position="bottom">Trigger</Tooltip>);
    fireEvent.mouseEnter(screen.getByText('Trigger'));
    const tooltip = screen.getByText('Tooltip content').parentElement;
    expect(tooltip).toHaveClass('top-full', 'mt-2');
  });

  it('should position tooltip at left when specified', () => {
    render(<Tooltip content="Tooltip content" position="left">Trigger</Tooltip>);
    fireEvent.mouseEnter(screen.getByText('Trigger'));
    const tooltip = screen.getByText('Tooltip content').parentElement;
    expect(tooltip).toHaveClass('right-full', 'mr-2');
  });

  it('should position tooltip at right when specified', () => {
    render(<Tooltip content="Tooltip content" position="right">Trigger</Tooltip>);
    fireEvent.mouseEnter(screen.getByText('Trigger'));
    const tooltip = screen.getByText('Tooltip content').parentElement;
    expect(tooltip).toHaveClass('left-full', 'ml-2');
  });

  it('should render with custom className', () => {
    render(<Tooltip content="Tooltip content" className="custom-class">Trigger</Tooltip>);
    const wrapper = screen.getByText('Trigger').parentElement;
    expect(wrapper).toHaveClass('custom-class');
  });
});

describe('Breadcrumb', () => {
  it('should render breadcrumb items', () => {
    const items = [
      { label: 'Home', href: '/' },
      { label: 'Products', href: '/products' },
      { label: 'Details', active: true },
    ];

    render(<Breadcrumb items={items} />);

    expect(screen.getByText('Home')).toBeInTheDocument();
    expect(screen.getByText('Products')).toBeInTheDocument();
    expect(screen.getByText('Details')).toBeInTheDocument();
  });

  it('should render links for non-active items', () => {
    const items = [
      { label: 'Home', href: '/' },
      { label: 'Products', href: '/products' },
    ];

    render(<Breadcrumb items={items} />);

    const homeLink = screen.getByText('Home').closest('a');
    expect(homeLink).toHaveAttribute('href', '/');
  });

  it('should not render link for active item', () => {
    const items = [
      { label: 'Home', href: '/' },
      { label: 'Details', active: true },
    ];

    render(<Breadcrumb items={items} />);

    const detailsItem = screen.getByText('Details');
    expect(detailsItem.tagName).not.toBe('A');
  });

  it('should render separators between items', () => {
    const items = [
      { label: 'Home', href: '/' },
      { label: 'Products', href: '/products' },
      { label: 'Details', active: true },
    ];

    const { container } = render(<Breadcrumb items={items} />);

    const separators = container.querySelectorAll('svg');
    expect(separators.length).toBe(2);
  });

  it('should render with custom className', () => {
    const items = [{ label: 'Home', href: '/' }];
    const { container } = render(<Breadcrumb items={items} className="custom-class" />);
    expect(container.firstChild).toHaveClass('custom-class');
  });
});

describe('SearchInput', () => {
  it('should render with default placeholder', () => {
    render(<SearchInput value="" onChange={() => {}} />);
    expect(screen.getByPlaceholderText('Search...')).toBeInTheDocument();
  });

  it('should render with custom placeholder', () => {
    render(<SearchInput value="" onChange={() => {}} placeholder="Search items..." />);
    expect(screen.getByPlaceholderText('Search items...')).toBeInTheDocument();
  });

  it('should display current value', () => {
    render(<SearchInput value="test" onChange={() => {}} />);
    const input = screen.getByPlaceholderText('Search...') as HTMLInputElement;
    expect(input.value).toBe('test');
  });

  it('should call onChange when value changes', () => {
    const handleChange = jest.fn();
    render(<SearchInput value="" onChange={handleChange} />);
    const input = screen.getByPlaceholderText('Search...');

    fireEvent.change(input, { target: { value: 'test' } });

    expect(handleChange).toHaveBeenCalledWith('test');
  });

  it('should show clear button when value is present', () => {
    render(<SearchInput value="test" onChange={() => {}} onClear={() => {}} />);
    const clearButton = document.querySelector('button');
    expect(clearButton).toBeInTheDocument();
  });

  it('should not show clear button when value is empty', () => {
    render(<SearchInput value="" onChange={() => {}} onClear={() => {}} />);
    const clearButton = document.querySelector('button');
    expect(clearButton).not.toBeInTheDocument();
  });

  it('should call onClear when clear button is clicked', () => {
    const handleClear = jest.fn();
    render(<SearchInput value="test" onChange={() => {}} onClear={handleClear} />);
    const clearButton = document.querySelector('button');

    fireEvent.click(clearButton);

    expect(handleClear).toHaveBeenCalled();
  });

  it('should render with custom className', () => {
    const { container } = render(
      <SearchInput value="" onChange={() => {}} className="custom-class" />
    );
    expect(container.firstChild).toHaveClass('custom-class');
  });
});
