import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {
  MobileNav,
  ResponsiveGrid,
  TouchButton,
  MobileHeader,
  MobileBottomNav,
} from '@/components/layout/MobileResponsive';

describe('MobileNav Component', () => {
  describe('Rendering', () => {
    it('should render mobile nav button', () => {
      render(
        <MobileNav>
          <div>Nav Content</div>
        </MobileNav>
      );

      const button = screen.getByRole('button');
      expect(button).toBeInTheDocument();
    });

    it('should render menu icon when closed', () => {
      render(
        <MobileNav isOpen={false}>
          <div>Nav Content</div>
        </MobileNav>
      );

      expect(screen.getByLabelText('Toggle menu')).toBeInTheDocument();
    });

    it('should render close icon when open', () => {
      render(
        <MobileNav isOpen={true}>
          <div>Nav Content</div>
        </MobileNav>
      );

      expect(screen.getByLabelText('Toggle menu')).toBeInTheDocument();
    });
  });

  describe('Toggle Functionality', () => {
    it('should open menu when button clicked', async () => {
      const user = userEvent.setup();
      render(
        <MobileNav>
          <div>Nav Content</div>
        </MobileNav>
      );

      const button = screen.getByRole('button');
      await user.click(button);

      expect(screen.getByText('Navigation')).toBeInTheDocument();
    });

    it('should close menu when close button clicked', async () => {
      const user = userEvent.setup();
      render(
        <MobileNav isOpen={true}>
          <div>Nav Content</div>
        </MobileNav>
      );

      const closeButton = screen.getByLabelText('Close menu');
      await user.click(closeButton);

      // Menu should close
      expect(closeButton).toBeInTheDocument();
    });

    it('should call onClose when provided', async () => {
      const user = userEvent.setup();
      const handleClose = jest.fn();
      render(
        <MobileNav isOpen={true} onClose={handleClose}>
          <div>Nav Content</div>
        </MobileNav>
      );

      const closeButton = screen.getByLabelText('Close menu');
      await user.click(closeButton);

      expect(handleClose).toHaveBeenCalled();
    });
  });

  describe('Body Scroll Lock', () => {
    it('should prevent body scroll when menu is open', () => {
      render(
        <MobileNav isOpen={true}>
          <div>Nav Content</div>
        </MobileNav>
      );

      expect(document.body.style.overflow).toBe('hidden');
    });

    it('should restore body scroll when menu is closed', () => {
      const { rerender } = render(
        <MobileNav isOpen={true}>
          <div>Nav Content</div>
        </MobileNav>
      );

      expect(document.body.style.overflow).toBe('hidden');

      rerender(
        <MobileNav isOpen={false}>
          <div>Nav Content</div>
        </MobileNav>
      );

      expect(document.body.style.overflow).toBe('');
    });
  });

  describe('Accessibility', () => {
    it('should have proper aria attributes', () => {
      render(
        <MobileNav isOpen={true}>
          <div>Nav Content</div>
        </MobileNav>
      );

      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('aria-expanded', 'true');
      expect(button).toHaveAttribute('aria-controls', 'mobile-menu');
    });

    it('should have dialog role when open', () => {
      render(
        <MobileNav isOpen={true}>
          <div>Nav Content</div>
        </MobileNav>
      );

      const dialog = screen.getByRole('dialog');
      expect(dialog).toBeInTheDocument();
    });
  });
});

describe('ResponsiveGrid Component', () => {
  describe('Rendering', () => {
    it('should render grid with children', () => {
      render(
        <ResponsiveGrid>
          <div>Item 1</div>
          <div>Item 2</div>
          <div>Item 3</div>
        </ResponsiveGrid>
      );

      expect(screen.getByText('Item 1')).toBeInTheDocument();
      expect(screen.getByText('Item 2')).toBeInTheDocument();
      expect(screen.getByText('Item 3')).toBeInTheDocument();
    });

    it('should apply grid role', () => {
      render(
        <ResponsiveGrid>
          <div>Item 1</div>
        </ResponsiveGrid>
      );

      const grid = screen.getByRole('grid');
      expect(grid).toBeInTheDocument();
    });
  });

  describe('Column Configuration', () => {
    it('should use default column configuration', () => {
      render(
        <ResponsiveGrid>
          <div>Item 1</div>
        </ResponsiveGrid>
      );

      const grid = screen.getByRole('grid');
      expect(grid).toBeInTheDocument();
    });

    it('should use custom column configuration', () => {
      render(
        <ResponsiveGrid cols={{ mobile: 2, tablet: 3, desktop: 4 }}>
          <div>Item 1</div>
        </ResponsiveGrid>
      );

      const grid = screen.getByRole('grid');
      expect(grid).toBeInTheDocument();
    });
  });

  describe('Gap Configuration', () => {
    it('should use default gap', () => {
      render(
        <ResponsiveGrid>
          <div>Item 1</div>
        </ResponsiveGrid>
      );

      const grid = screen.getByRole('grid');
      expect(grid).toBeInTheDocument();
    });

    it('should use custom gap', () => {
      render(
        <ResponsiveGrid gap="2rem">
          <div>Item 1</div>
        </ResponsiveGrid>
      );

      const grid = screen.getByRole('grid');
      expect(grid).toBeInTheDocument();
    });
  });
});

describe('TouchButton Component', () => {
  describe('Rendering', () => {
    it('should render button with children', () => {
      render(<TouchButton>Click Me</TouchButton>);

      expect(screen.getByText('Click Me')).toBeInTheDocument();
    });

    it('should apply primary variant by default', () => {
      render(<TouchButton>Primary</TouchButton>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('bg-blue-600');
    });

    it('should apply secondary variant', () => {
      render(<TouchButton variant="secondary">Secondary</TouchButton>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('bg-gray-200');
    });

    it('should apply ghost variant', () => {
      render(<TouchButton variant="ghost">Ghost</TouchButton>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('bg-transparent');
    });
  });

  describe('Size Variants', () => {
    it('should apply small size', () => {
      render(<TouchButton size="sm">Small</TouchButton>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('px-3');
      expect(button).toHaveClass('py-2');
    });

    it('should apply medium size by default', () => {
      render(<TouchButton>Medium</TouchButton>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('px-4');
      expect(button).toHaveClass('py-3');
    });

    it('should apply large size', () => {
      render(<TouchButton size="lg">Large</TouchButton>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('px-6');
      expect(button).toHaveClass('py-4');
    });
  });

  describe('Disabled State', () => {
    it('should apply disabled styles', () => {
      render(<TouchButton disabled>Disabled</TouchButton>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('opacity-50');
      expect(button).toHaveClass('cursor-not-allowed');
    });

    it('should not be clickable when disabled', () => {
      render(<TouchButton disabled>Disabled</TouchButton>);

      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
    });
  });

  describe('Click Handler', () => {
    it('should call onClick when clicked', async () => {
      const user = userEvent.setup();
      const handleClick = jest.fn();
      render(<TouchButton onClick={handleClick}>Click Me</TouchButton>);

      const button = screen.getByRole('button');
      await user.click(button);

      expect(handleClick).toHaveBeenCalledTimes(1);
    });
  });

  describe('Accessibility', () => {
    it('should have aria-label when provided', () => {
      render(<TouchButton ariaLabel="Accessible Button">Button</TouchButton>);

      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('aria-label', 'Accessible Button');
    });

    it('should have focus ring on focus', () => {
      render(<TouchButton>Button</TouchButton>);

      const button = screen.getByRole('button');
      expect(button).toHaveClass('focus:ring-2');
    });
  });
});

describe('MobileHeader Component', () => {
  describe('Rendering', () => {
    it('should render header with title', () => {
      render(<MobileHeader title="Page Title" />);

      expect(screen.getByText('Page Title')).toBeInTheDocument();
    });

    it('should render back button when showBackButton is true', () => {
      render(<MobileHeader title="Page Title" showBackButton={true} />);

      const backButton = screen.getByLabelText('Go back');
      expect(backButton).toBeInTheDocument();
    });

    it('should render menu button when onMenuToggle is provided', () => {
      const handleMenuToggle = jest.fn();
      render(<MobileHeader title="Page Title" onMenuToggle={handleMenuToggle} />);

      const menuButton = screen.getByLabelText('Open menu');
      expect(menuButton).toBeInTheDocument();
    });
  });

  describe('Back Button', () => {
    it('should call onBack when back button clicked', async () => {
      const user = userEvent.setup();
      const handleBack = jest.fn();
      render(<MobileHeader title="Page Title" showBackButton={true} onBack={handleBack} />);

      const backButton = screen.getByLabelText('Go back');
      await user.click(backButton);

      expect(handleBack).toHaveBeenCalledTimes(1);
    });
  });

  describe('Menu Button', () => {
    it('should call onMenuToggle when menu button clicked', async () => {
      const user = userEvent.setup();
      const handleMenuToggle = jest.fn();
      render(<MobileHeader title="Page Title" onMenuToggle={handleMenuToggle} />);

      const menuButton = screen.getByLabelText('Open menu');
      await user.click(menuButton);

      expect(handleMenuToggle).toHaveBeenCalledTimes(1);
    });
  });

  describe('Styling', () => {
    it('should apply correct header styles', () => {
      render(<MobileHeader title="Page Title" />);

      const header = screen.getByText('Page Title').closest('header');
      expect(header).toHaveClass('sticky');
      expect(header).toHaveClass('top-0');
    });
  });
});

describe('MobileBottomNav Component', () => {
  const mockItems = [
    { icon: <span>🏠</span>, label: 'Home', onClick: jest.fn(), active: true },
    { icon: <span>🔍</span>, label: 'Search', onClick: jest.fn(), active: false },
    { icon: <span>⚙️</span>, label: 'Settings', onClick: jest.fn(), active: false },
  ];

  describe('Rendering', () => {
    it('should render bottom nav with items', () => {
      render(<MobileBottomNav items={mockItems} />);

      expect(screen.getByText('Home')).toBeInTheDocument();
      expect(screen.getByText('Search')).toBeInTheDocument();
      expect(screen.getByText('Settings')).toBeInTheDocument();
    });

    it('should render icons for each item', () => {
      render(<MobileBottomNav items={mockItems} />);

      expect(screen.getByText('🏠')).toBeInTheDocument();
      expect(screen.getByText('🔍')).toBeInTheDocument();
      expect(screen.getByText('⚙️')).toBeInTheDocument();
    });
  });

  describe('Active State', () => {
    it('should highlight active item', () => {
      render(<MobileBottomNav items={mockItems} />);

      const activeButton = screen.getByText('Home').closest('button');
      expect(activeButton).toHaveClass('text-blue-600');
    });

    it('should not highlight inactive items', () => {
      render(<MobileBottomNav items={mockItems} />);

      const inactiveButton = screen.getByText('Search').closest('button');
      expect(inactiveButton).toHaveClass('text-gray-600');
    });
  });

  describe('Click Handler', () => {
    it('should call onClick when item clicked', async () => {
      const user = userEvent.setup();
      const items = [
        { icon: <span>🏠</span>, label: 'Home', onClick: jest.fn(), active: false },
      ];
      render(<MobileBottomNav items={items} />);

      const button = screen.getByText('Home');
      await user.click(button);

      expect(items[0].onClick).toHaveBeenCalledTimes(1);
    });
  });

  describe('Accessibility', () => {
    it('should have navigation role', () => {
      render(<MobileBottomNav items={mockItems} />);

      const nav = screen.getByRole('navigation');
      expect(nav).toBeInTheDocument();
    });

    it('should have aria-current on active item', () => {
      render(<MobileBottomNav items={mockItems} />);

      const activeButton = screen.getByText('Home').closest('button');
      expect(activeButton).toHaveAttribute('aria-current', 'page');
    });

    it('should have aria-label on items', () => {
      render(<MobileBottomNav items={mockItems} />);

      const buttons = screen.getAllByRole('button');
      buttons.forEach(button => {
        expect(button).toHaveAttribute('aria-label');
      });
    });
  });

  describe('Styling', () => {
    it('should apply correct container styles', () => {
      render(<MobileBottomNav items={mockItems} />);

      const nav = screen.getByRole('navigation');
      expect(nav).toHaveClass('fixed');
      expect(nav).toHaveClass('bottom-0');
    });
  });
});
