'use client';

import { useState } from 'react';
import { Label } from '@/components/ui/label';
import { Check, ChevronDown } from 'lucide-react';

interface MultiSelectProps {
  label?: string;
  value: string[];
  onChange: (value: string[]) => void;
  options: { value: string; label: string; disabled?: boolean }[];
  placeholder?: string;
  error?: string;
  helperText?: string;
  disabled?: boolean;
  fullWidth?: boolean;
  required?: boolean;
}

export function MultiSelect({
  label,
  value,
  onChange,
  options,
  placeholder = '请选择',
  error,
  helperText,
  disabled = false,
  fullWidth = false,
  required = false,
}: MultiSelectProps) {
  const [isOpen, setIsOpen] = useState(false);

  const selectedLabels = value
    .map((v) => options.find((opt) => opt.value === v)?.label)
    .filter(Boolean)
    .join(', ');

  const toggleOption = (optionValue: string) => {
    if (value.includes(optionValue)) {
      onChange(value.filter((v) => v !== optionValue));
    } else {
      onChange([...value, optionValue]);
    }
  };

  return (
    <div className={`space-y-1 ${fullWidth ? 'w-full' : ''}`}>
      {label && (
        <Label className={`text-sm font-medium ${error ? 'text-red-600' : 'text-gray-700'}`}>
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </Label>
      )}
      <div className="relative">
        <button
          type="button"
          onClick={() => !disabled && setIsOpen(!isOpen)}
          disabled={disabled}
          className={`w-full flex items-center justify-between px-3 py-2 border rounded-md bg-white text-left ${
            error ? 'border-red-500' : 'border-gray-300'
          } ${disabled ? 'bg-gray-100 cursor-not-allowed' : 'hover:border-gray-400'} transition`}
        >
          <span className={value.length > 0 ? 'text-gray-900' : 'text-gray-500'}>
            {value.length > 0 ? selectedLabels : placeholder}
          </span>
          <ChevronDown className={`h-4 w-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </button>

        {isOpen && !disabled && (
          <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-auto">
            {options.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => toggleOption(option.value)}
                disabled={option.disabled}
                className={`w-full flex items-center justify-between px-3 py-2 hover:bg-gray-100 transition ${
                  option.disabled ? 'text-gray-400 cursor-not-allowed' : 'text-gray-900'
                }`}
              >
                <span>{option.label}</span>
                {value.includes(option.value) && <Check className="h-4 w-4 text-blue-600" />}
              </button>
            ))}
          </div>
        )}
      </div>
      {error && <p className="text-xs text-red-600">{error}</p>}
      {helperText && !error && <p className="text-xs text-gray-500">{helperText}</p>}
    </div>
  );
}
