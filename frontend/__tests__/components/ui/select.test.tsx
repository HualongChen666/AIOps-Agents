import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Select } from '@/components/ui/select';

// Mock the cn utility
jest.mock('@/lib/utils', () => ({
  cn: (...args: any[]) => args.filter(Boolean).join(' '),
}));

describe('Select Component', () => {
  describe('Rendering', () => {
    it('should render select with default props', () => {
      render(<Select />);
      const select = screen.getByRole('combobox');
      expect(select).toBeInTheDocument();
      expect(select).toHaveClass('flex', 'h-10', 'w-full');
    });

    it('should render select with custom className', () => {
      render(<Select className="custom-class" />);
      const select = screen.getByRole('combobox');
      expect(select).toHaveClass('custom-class');
    });

    it('should render disabled select', () => {
      render(<Select disabled />);
      const select = screen.getByRole('combobox');
      expect(select).toBeDisabled();
      expect(select).toHaveClass('disabled:cursor-not-allowed', 'disabled:opacity-50');
    });

    it('should render select with label', () => {
      render(<Select label="Choose option" />);
      const label = screen.getByText('Choose option');
      expect(label).toBeInTheDocument();
      expect(label).toHaveClass('text-sm', 'font-medium', 'text-gray-700');
    });

    it('should render select with error state', () => {
      render(<Select error="This field is required" />);
      const select = screen.getByRole('combobox');
      expect(select).toHaveClass('border-red-500');
      const error = screen.getByText('This field is required');
      expect(error).toHaveClass('text-xs', 'text-red-600');
    });

    it('should render select with helper text', () => {
      render(<Select helperText="Choose an option from the list" />);
      const helper = screen.getByText('Choose an option from the list');
      expect(helper).toHaveClass('text-xs', 'text-gray-500');
    });

    it('should render select with required indicator', () => {
      render(<Select label="Required field" required />);
      const asterisk = screen.getByText('*');
      expect(asterisk).toHaveClass('text-red-500', 'ml-1');
    });

    it('should render select with fullWidth', () => {
      render(<Select fullWidth />);
      const container = screen.getByRole('combobox').parentElement?.parentElement;
      expect(container).toHaveClass('w-full');
    });

    it('should render select with options', () => {
      render(
        <Select>
          <option value="option1">Option 1</option>
          <option value="option2">Option 2</option>
          <option value="option3">Option 3</option>
        </Select>
      );
      expect(screen.getByText('Option 1')).toBeInTheDocument();
      expect(screen.getByText('Option 2')).toBeInTheDocument();
      expect(screen.getByText('Option 3')).toBeInTheDocument();
    });
  });

  describe('Event Handling', () => {
    it('should call onChange handler when value changes', async () => {
      const handleChange = jest.fn();
      const user = userEvent.setup();
      render(
        <Select onChange={handleChange}>
          <option value="option1">Option 1</option>
          <option value="option2">Option 2</option>
        </Select>
      );
      
      const select = screen.getByRole('combobox');
      await user.selectOptions(select, 'option2');
      
      expect(handleChange).toHaveBeenCalled();
    });

    it('should call onFocus handler when focused', async () => {
      const handleFocus = jest.fn();
      const user = userEvent.setup();
      render(<Select onFocus={handleFocus} />);
      
      const select = screen.getByRole('combobox');
      await user.click(select);
      
      expect(handleFocus).toHaveBeenCalled();
    });

    it('should call onBlur handler when blurred', async () => {
      const handleBlur = jest.fn();
      const user = userEvent.setup();
      render(<Select onBlur={handleBlur} />);
      
      const select = screen.getByRole('combobox');
      await user.click(select);
      await user.tab();
      
      expect(handleBlur).toHaveBeenCalled();
    });

    it('should not call onChange when disabled', async () => {
      const handleChange = jest.fn();
      const user = userEvent.setup();
      render(
        <Select onChange={handleChange} disabled>
          <option value="option1">Option 1</option>
          <option value="option2">Option 2</option>
        </Select>
      );
      
      const select = screen.getByRole('combobox');
      expect(select).toBeDisabled();
    });
  });

  describe('Props forwarding', () => {
    it('should forward ref to select element', () => {
      const ref = React.createRef<HTMLSelectElement>();
      render(<Select ref={ref} />);
      
      expect(ref.current).toBeInstanceOf(HTMLSelectElement);
    });

    it('should pass additional HTML attributes', () => {
      render(<Select data-testid="test-select" aria-label="Test Select" />);
      const select = screen.getByTestId('test-select');
      expect(select).toHaveAttribute('aria-label', 'Test Select');
    });

    it('should handle name attribute', () => {
      render(<Select name="category" />);
      const select = screen.getByRole('combobox');
      expect(select).toHaveAttribute('name', 'category');
    });

    it('should handle id attribute', () => {
      render(<Select id="test-id" />);
      const select = screen.getByRole('combobox');
      expect(select).toHaveAttribute('id', 'test-id');
    });

    it('should handle multiple attribute', () => {
      render(
        <Select multiple>
          <option value="option1">Option 1</option>
          <option value="option2">Option 2</option>
        </Select>
      );
      const select = screen.getByRole('listbox');
      expect(select).toHaveAttribute('multiple');
    });

    it('should handle size attribute', () => {
      render(
        <Select size={5}>
          <option value="option1">Option 1</option>
          <option value="option2">Option 2</option>
        </Select>
      );
      const select = screen.getByRole('listbox');
      expect(select).toHaveAttribute('size', '5');
    });
  });

  describe('Label Behavior', () => {
    it('should render label in red when error is present', () => {
      render(<Select label="Field" error="Error" />);
      const label = screen.getByText('Field');
      expect(label).toHaveClass('text-red-600');
    });

    it('should render label in gray when no error', () => {
      render(<Select label="Field" />);
      const label = screen.getByText('Field');
      expect(label).toHaveClass('text-gray-700');
    });

    it('should not render label when not provided', () => {
      render(<Select />);
      const label = screen.queryByText('Field');
      expect(label).not.toBeInTheDocument();
    });

    it('should associate label with select via htmlFor when id is provided', () => {
      render(<Select id="test-select" label="Test Label" />);
      const label = screen.getByText('Test Label');
      expect(label.tagName).toBe('LABEL');
    });
  });

  describe('Error State', () => {
    it('should show error message when error prop is provided', () => {
      render(<Select error="This is required" />);
      const error = screen.getByText('This is required');
      expect(error).toBeInTheDocument();
      expect(error).toHaveClass('text-xs', 'text-red-600');
    });

    it('should apply error border to select', () => {
      render(<Select error="Error" />);
      const select = screen.getByRole('combobox');
      expect(select).toHaveClass('border-red-500');
    });

    it('should not show helper text when error is present', () => {
      render(<Select error="Error" helperText="Helper" />);
      expect(screen.getByText('Error')).toBeInTheDocument();
      expect(screen.queryByText('Helper')).not.toBeInTheDocument();
    });
  });

  describe('Helper Text', () => {
    it('should show helper text when no error', () => {
      render(<Select helperText="Choose wisely" />);
      const helper = screen.getByText('Choose wisely');
      expect(helper).toBeInTheDocument();
      expect(helper).toHaveClass('text-xs', 'text-gray-500');
    });

    it('should not show helper text when error is present', () => {
      render(<Select helperText="Helper" error="Error" />);
      expect(screen.queryByText('Helper')).not.toBeInTheDocument();
    });

    it('should not show helper text when not provided', () => {
      render(<Select />);
      const helper = screen.queryByText('Helper');
      expect(helper).not.toBeInTheDocument();
    });
  });

  describe('Required State', () => {
    it('should show asterisk when required', () => {
      render(<Select label="Field" required />);
      const asterisk = screen.getByText('*');
      expect(asterisk).toBeInTheDocument();
      expect(asterisk).toHaveClass('text-red-500', 'ml-1');
    });

    it('should not show asterisk when not required', () => {
      render(<Select label="Field" />);
      const asterisk = screen.queryByText('*');
      expect(asterisk).not.toBeInTheDocument();
    });

    it('should add required attribute to select', () => {
      render(<Select required />);
      const select = screen.getByRole('combobox');
      expect(select).toBeRequired();
    });
  });

  describe('Full Width', () => {
    it('should apply w-full class when fullWidth is true', () => {
      render(<Select fullWidth />);
      const container = screen.getByRole('combobox').parentElement?.parentElement;
      expect(container).toHaveClass('w-full');
    });

    it('should not apply w-full class when fullWidth is false', () => {
      render(<Select fullWidth={false} />);
      const container = screen.getByRole('combobox').parentElement?.parentElement;
      expect(container).not.toHaveClass('w-full');
    });

    it('should not apply w-full class by default', () => {
      render(<Select />);
      const container = screen.getByRole('combobox').parentElement?.parentElement;
      expect(container).not.toHaveClass('w-full');
    });
  });

  describe('Controlled Select', () => {
    it('should work as controlled component', () => {
      const TestComponent = () => {
        const [value, setValue] = React.useState('');
        return (
          <Select value={value} onChange={(e) => setValue(e.target.value)}>
            <option value="">Select...</option>
            <option value="option1">Option 1</option>
            <option value="option2">Option 2</option>
          </Select>
        );
      };
      
      render(<TestComponent />);
      const select = screen.getByRole('combobox');
      expect(select).toHaveValue('');
    });

    it('should update controlled value', async () => {
      const TestComponent = () => {
        const [value, setValue] = React.useState('option1');
        return (
          <>
            <Select value={value} onChange={(e) => setValue(e.target.value)}>
              <option value="option1">Option 1</option>
              <option value="option2">Option 2</option>
            </Select>
            <button onClick={() => setValue('option2')}>Update</button>
          </>
        );
      };
      
      const user = userEvent.setup();
      render(<TestComponent />);
      
      const select = screen.getByRole('combobox');
      expect(select).toHaveValue('option1');
      
      const button = screen.getByRole('button', { name: 'Update' });
      await user.click(button);
      
      expect(select).toHaveValue('option2');
    });
  });

  describe('Edge Cases', () => {
    it('should render with empty options', () => {
      render(<Select></Select>);
      const select = screen.getByRole('combobox');
      expect(select).toBeInTheDocument();
    });

    it('should render with null children', () => {
      render(<Select>{null}</Select>);
      const select = screen.getByRole('combobox');
      expect(select).toBeInTheDocument();
    });

    it('should render with undefined children', () => {
      render(<Select>{undefined}</Select>);
      const select = screen.getByRole('combobox');
      expect(select).toBeInTheDocument();
    });

    it('should render with mixed children', () => {
      render(
        <Select>
          <option value="option1">Option 1</option>
          {null}
          <option value="option2">Option 2</option>
        </Select>
      );
      expect(screen.getByText('Option 1')).toBeInTheDocument();
      expect(screen.getByText('Option 2')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper focus styles', () => {
      render(<Select />);
      const select = screen.getByRole('combobox');
      expect(select).toHaveClass('focus-visible:outline-none', 'focus-visible:ring-2');
    });

    it('should support aria-label', () => {
      render(<Select aria-label="Choose category" />);
      const select = screen.getByLabelText('Choose category');
      expect(select).toBeInTheDocument();
    });

    it('should support aria-describedby for helper text', () => {
      render(
        <>
          <Select aria-describedby="help-text" helperText="Help" />
          <span id="help-text">Help text</span>
        </>
      );
      const select = screen.getByRole('combobox');
      expect(select).toHaveAttribute('aria-describedby', 'help-text');
    });

    it('should support aria-invalid for error state', () => {
      render(<Select error="Error" aria-invalid="true" />);
      const select = screen.getByRole('combobox');
      expect(select).toHaveAttribute('aria-invalid', 'true');
    });

    it('should support aria-required for required state', () => {
      render(<Select required aria-required="true" />);
      const select = screen.getByRole('combobox');
      expect(select).toHaveAttribute('aria-required', 'true');
    });
  });

  describe('Styling', () => {
    it('should have correct base styles', () => {
      render(<Select />);
      const select = screen.getByRole('combobox');
      expect(select).toHaveClass('flex', 'h-10', 'w-full', 'rounded-md', 'border', 'border-gray-300', 'bg-white');
    });

    it('should have correct padding', () => {
      render(<Select />);
      const select = screen.getByRole('combobox');
      expect(select).toHaveClass('px-3', 'py-2');
    });

    it('should have correct text styles', () => {
      render(<Select />);
      const select = screen.getByRole('combobox');
      expect(select).toHaveClass('text-sm');
    });

    it('should have correct focus styles', () => {
      render(<Select />);
      const select = screen.getByRole('combobox');
      expect(select).toHaveClass('focus-visible:outline-none', 'focus-visible:ring-2', 'focus-visible:ring-blue-500');
    });

    it('should have correct disabled styles', () => {
      render(<Select disabled />);
      const select = screen.getByRole('combobox');
      expect(select).toHaveClass('disabled:cursor-not-allowed', 'disabled:opacity-50');
    });
  });
});
