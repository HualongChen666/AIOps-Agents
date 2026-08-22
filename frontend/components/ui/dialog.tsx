'use client'

import React, { useEffect, useState } from 'react';

interface DialogProps {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  children: React.ReactNode;
}

interface DialogContentProps {
  className?: string;
  children: React.ReactNode;
  onClose?: () => void;
}

export const Dialog = ({ open = false, onOpenChange, children }: DialogProps) => {
  const [isOpen, setIsOpen] = useState(open);

  useEffect(() => {
    setIsOpen(open);
  }, [open]);

  const handleOpenChange = (newOpen: boolean) => {
    setIsOpen(newOpen);
    onOpenChange?.(newOpen);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" role="dialog" aria-modal="true">
      <div className="fixed inset-0 bg-black/50" onClick={() => handleOpenChange(false)} />
      {React.Children.map(children, (child) => {
        if (React.isValidElement(child)) {
          return React.cloneElement(child as React.ReactElement<DialogContentProps>, {
            onClose: () => handleOpenChange(false),
          });
        }
        return child;
      })}
    </div>
  );
};

export const DialogContent = ({ className = '', children, onClose }: DialogContentProps) => {
  return (
    <div className={`relative z-50 w-full max-w-lg rounded-lg border border-gray-200 bg-white p-6 shadow-lg ${className}`}>
      <button
        onClick={onClose}
        aria-label="关闭对话框"
        className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-white transition-opacity hover:opacity-100"
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
      {children}
    </div>
  );
};

export const DialogHeader = ({ className = '', children }: { className?: string; children: React.ReactNode }) => (
  <div className={`mb-4 ${className}`}>{children}</div>
);

export const DialogTitle = ({ className = '', children }: { className?: string; children: React.ReactNode }) => (
  <h2 className={`text-lg font-semibold text-gray-900 ${className}`}>{children}</h2>
);

export const DialogFooter = ({ className = '', children }: { className?: string; children: React.ReactNode }) => (
  <div className={`mt-6 flex justify-end space-x-2 ${className}`}>{children}</div>
);
