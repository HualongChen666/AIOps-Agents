/**
 * Mobile Responsive Layout Components
 *
 * Provides mobile-first responsive layout components
 * to improve mobile user experience with enhanced accessibility.
 */

import { useState, useEffect } from 'react';
import { Menu, X, ChevronRight, Home, Settings, User, Bell } from 'lucide-react';

interface MobileNavProps {
  children: React.ReactNode;
  isOpen?: boolean;
  onClose?: () => void;
}

export function MobileNav({ children, isOpen: controlledIsOpen, onClose }: MobileNavProps) {
  const [internalIsOpen, setInternalIsOpen] = useState(false);
  const isOpen = controlledIsOpen !== undefined ? controlledIsOpen : internalIsOpen;

  useEffect(() => {
    // Prevent body scroll when menu is open
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  const handleClose = () => {
    if (onClose) {
      onClose();
    } else {
      setInternalIsOpen(false);
    }
  };

  return (
    <div className="md:hidden relative z-50">
      <button
        onClick={() => {
          if (onClose) {
            onClose();
          } else {
            setInternalIsOpen(!internalIsOpen);
          }
        }}
        className="p-2 rounded-md hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
        aria-label="Toggle menu"
        aria-expanded={isOpen}
        aria-controls="mobile-menu"
      >
        {isOpen ? <X className="h-6 w-6" aria-hidden="true" /> : <Menu className="h-6 w-6" aria-hidden="true" />}
      </button>
      {isOpen && (
        <div
          id="mobile-menu"
          className="fixed inset-0 bg-black/50 z-50"
          onClick={handleClose}
          role="dialog"
          aria-modal="true"
          aria-label="Mobile navigation menu"
        >
          <div
            className="absolute right-0 top-0 bottom-0 w-80 bg-white shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-4 border-b flex items-center justify-between">
              <h2 className="text-lg font-semibold">Navigation</h2>
              <button
                onClick={handleClose}
                className="p-2 rounded-md hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                aria-label="Close menu"
              >
                <X className="h-6 w-6" aria-hidden="true" />
              </button>
            </div>
            <nav className="p-4 space-y-2" role="navigation" aria-label="Main navigation">
              {children}
            </nav>
          </div>
        </div>
      )}
    </div>
  );
}

interface ResponsiveGridProps {
  children: React.ReactNode;
  cols?: {
    mobile?: number;
    tablet?: number;
    desktop?: number;
  };
  gap?: string;
}

export function ResponsiveGrid({
  children,
  cols = { mobile: 1, tablet: 2, desktop: 3 },
  gap = '1rem',
}: ResponsiveGridProps) {
  return (
    <div
      className="grid"
      style={{
        gridTemplateColumns: `repeat(${cols.mobile}, 1fr)`,
        gap,
      }}
      role="grid"
      aria-label="Responsive grid layout"
    >
      <style jsx>{`
        @media (min-width: 768px) {
          div {
            grid-template-columns: repeat(${cols.tablet}, 1fr);
          }
        }
        @media (min-width: 1024px) {
          div {
            grid-template-columns: repeat(${cols.desktop}, 1fr);
          }
        }
      `}</style>
      {children}
    </div>
  );
}

interface TouchButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  className?: string;
  disabled?: boolean;
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  ariaLabel?: string;
}

export function TouchButton({
  children,
  onClick,
  className,
  disabled,
  variant = 'primary',
  size = 'md',
  ariaLabel,
}: TouchButtonProps) {
  const baseStyles = 'rounded-lg active:scale-95 transition-transform touch-manipulation focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2';

  const variantStyles = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700',
    secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300',
    ghost: 'bg-transparent text-gray-900 hover:bg-gray-100',
  };

  const sizeStyles = {
    sm: 'px-3 py-2 text-sm',
    md: 'px-4 py-3 text-base',
    lg: 'px-6 py-4 text-lg',
  };

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${disabled ? 'opacity-50 cursor-not-allowed' : ''} ${className}`}
      aria-label={ariaLabel}
    >
      {children}
    </button>
  );
}

interface MobileHeaderProps {
  title: string;
  onMenuToggle?: () => void;
  showBackButton?: boolean;
  onBack?: () => void;
}

export function MobileHeader({ title, onMenuToggle, showBackButton, onBack }: MobileHeaderProps) {
  return (
    <header className="md:hidden sticky top-0 bg-white border-b z-40">
      <div className="flex items-center justify-between p-4">
        <div className="flex items-center gap-3">
          {showBackButton && (
            <button
              onClick={onBack}
              className="p-2 rounded-md hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              aria-label="Go back"
            >
              <ChevronRight className="h-6 w-6 rotate-180" aria-hidden="true" />
            </button>
          )}
          <h1 className="text-lg font-semibold">{title}</h1>
        </div>
        {onMenuToggle && (
          <button
            onClick={onMenuToggle}
            className="p-2 rounded-md hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            aria-label="Open menu"
          >
            <Menu className="h-6 w-6" aria-hidden="true" />
          </button>
        )}
      </div>
    </header>
  );
}

interface MobileBottomNavProps {
  items: Array<{
    icon: React.ReactNode;
    label: string;
    onClick: () => void;
    active?: boolean;
  }>;
}

export function MobileBottomNav({ items }: MobileBottomNavProps) {
  return (
    <nav
      className="md:hidden fixed bottom-0 left-0 right-0 bg-white border-t z-40"
      role="navigation"
      aria-label="Bottom navigation"
    >
      <div className="flex justify-around py-2">
        {items.map((item, index) => (
          <button
            key={index}
            onClick={item.onClick}
            className={`flex flex-col items-center p-2 rounded-lg ${item.active ? 'text-blue-600 bg-blue-50' : 'text-gray-600'
              } focus:outline-none focus:ring-2 focus:ring-blue-500`}
            aria-label={item.label}
            aria-current={item.active ? 'page' : undefined}
          >
            <div className="mb-1">{item.icon}</div>
            <span className="text-xs">{item.label}</span>
          </button>
        ))}
      </div>
    </nav>
  );
}