/**
 * Mobile Responsive Layout Components
 * 
 * Provides mobile-first responsive layout components
 * to improve mobile user experience.
 */

import { useState } from 'react';
import { Menu, X } from 'lucide-react';

interface MobileNavProps {
  children: React.ReactNode;
}

export function MobileNav({ children }: MobileNavProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="md:hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="p-2 rounded-md hover:bg-gray-100"
        aria-label="Toggle menu"
      >
        {isOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
      </button>
      {isOpen && (
        <div className="absolute top-16 left-0 right-0 bg-white border-b shadow-lg z-50">
          <div className="p-4 space-y-2">
            {children}
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
}

export function TouchButton({ children, onClick, className, disabled }: TouchButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`
        px-4 py-3 rounded-lg
        active:scale-95 transition-transform
        touch-manipulation
        ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
        ${className}
      `}
    >
      {children}
    </button>
  );
}