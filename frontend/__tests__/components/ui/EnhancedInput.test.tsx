import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { EnhancedInput } from '@/components/ui/EnhancedInput';
import { Search } from 'lucide-react';

// Mock the lucide-react icon
jest.mock('lucide-react', () => ({
  Search: () => <span data-testid="search-icon">🔍</span>,
}));

// Mock the Label component
jest.mock('@/components/ui/label', () => ({
  Label: ({ children, className, htmlFor }: any) => (
    <label htmlFor={htmlFor} className={className}>
      {children}
    </label>
  ),
}));

describe('EnhancedInput Component', () => {
  describe('Rendering', () => {
    it('should render input with default props', () => {
      render(<EnhancedInput />);
      const input = screen.getByRole('textbox');
      expect(input).toBeInTheDocument();
    });

    it('should render input with label', () => {
      render(<EnhancedInput label="Username" />);
      expect(screen.getByText('Username')).toBeInTheDocument();
    });

    it('should render input with error state', () => {
      render(<EnhancedInput error="This field is required" />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveClass('border-red-500');
      expect(screen.getByText('This field is required')).toBeInTheDocument();
    });

    it('should render input with helper text', () => {
      render(<EnhancedInput helperText="Enter your username" />);
      expect(screen.getByText('Enter your username')).toBeInTheDocument();
    });

    it('should render input with icon on left', () => {
      render(<EnhancedInput icon={Search} iconPosition="left" />);
      const icon = screen.getByTestId('search-icon');
      expect(icon).toBeInTheDocument();
    });

    it('should render input with icon on right', () => {
      render(<EnhancedInput icon={Search} iconPosition="right" />);
      const icon = screen.getByTestId('search-icon');
      expect(icon).toBeInTheDocument();
    });

    it('should render input with fullWidth', () => {
      render(<EnhancedInput fullWidth />);
      const container = screen.getByRole('textbox').parentElement?.parentElement;
      expect(container).toHaveClass('w-full');
    });

    it('should render input with custom className', () => {
      render(<EnhancedInput className="custom-class" />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveClass('custom-class');
    });
  });

  describe('Label Behavior', () => {
    it('should render label in red when error is present', () => {
      render(<EnhancedInput label="Field" error="Error" />);
      const label = screen.getByText('Field');
      expect(label).toHaveClass('text-red-600');
    });

    it('should render label in gray when no error', () => {
      render(<EnhancedInput label="Field" />);
      const label = screen.getByText('Field');
      expect(label).toHaveClass('text-gray-700');
    });

    it('should not render label when not provided', () => {
      render(<EnhancedInput />);
      const label = screen.queryByText('Field');
      expect(label).not.toBeInTheDocument();
    });
  });

  describe('Error State', () => {
    it('should show error message when error prop is provided', () => {
      render(<EnhancedInput error="This is required" />);
      const error = screen.getByText('This is required');
      expect(error).toHaveClass('text-xs', 'text-red-600');
    });

    it('should apply error border to input', () => {
      render(<EnhancedInput error="Error" />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveClass('border-red-500', 'focus:border-red-500');
    });

    it('should not show helper text when error is present', () => {
      render(<EnhancedInput error="Error" helperText="Helper" />);
      expect(screen.getByText('Error')).toBeInTheDocument();
      expect(screen.queryByText('Helper')).not.toBeInTheDocument();
    });
  });

  describe('Helper Text', () => {
    it('should show helper text when no error', () => {
      render(<EnhancedInput helperText="Choose wisely" />);
      const helper = screen.getByText('Choose wisely');
      expect(helper).toHaveClass('text-xs', 'text-gray-500');
    });

    it('should not show helper text when error is present', () => {
      render(<EnhancedInput helperText="Helper" error="Error" />);
      expect(screen.queryByText('Helper')).not.toBeInTheDocument();
    });

    it('should not show helper text when not provided', () => {
      render(<EnhancedInput />);
      const helper = screen.queryByText('Helper');
      expect(helper).not.toBeInTheDocument();
    });
  });

  describe('Icon Position', () => {
    it('should place icon on left when iconPosition is left', () => {
      render(<EnhancedInput icon={Search} iconPosition="left" />);
      const icon = screen.getByTestId('search-icon');
      expect(icon).toBeInTheDocument();
    });

    it('should place icon on right when iconPosition is right', () => {
      render(<EnhancedInput icon={Search} iconPosition="right" />);
      const icon = screen.getByTestId('search-icon');
      expect(icon).toBeInTheDocument();
    });

    it('should default to left icon position', () => {
      render(<EnhancedInput icon={Search} />);
      const icon = screen.getByTestId('search-icon');
      expect(icon).toBeInTheDocument();
    });

    it('should not render icon when not provided', () => {
      render(<EnhancedInput />);
      expect(screen.queryByTestId('search-icon')).not.toBeInTheDocument();
    });

    it('should add left padding when icon is on left', () => {
      render(<EnhancedInput icon={Search} iconPosition="left" />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveClass('pl-10');
    });

    it('should add right padding when icon is on right', () => {
      render(<EnhancedInput icon={Search} iconPosition="right" />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveClass('pr-10');
    });
  });

  describe('Full Width', () => {
    it('should apply w-full class when fullWidth is true', () => {
      render(<EnhancedInput fullWidth />);
      const container = screen.getByRole('textbox').parentElement?.parentElement;
      expect(container).toHaveClass('w-full');
    });

    it('should not apply w-full class when fullWidth is false', () => {
      render(<EnhancedInput fullWidth={false} />);
      const container = screen.getByRole('textbox').parentElement?.parentElement;
      expect(container).not.toHaveClass('w-full');
    });

    it('should not apply w-full class by default', () => {
      render(<EnhancedInput />);
      const container = screen.getByRole('textbox').parentElement?.parentElement;
      expect(container).not.toHaveClass('w-full');
    });
  });

  describe('Focus State', () => {
    it('should add ring class when focused', async () => {
      const user = userEvent.setup();
      render(<EnhancedInput />);
      
      const input = screen.getByRole('textbox');
      await user.click(input);
      
      expect(input).toHaveClass('ring-2', 'ring-blue-500');
    });

    it('should remove ring class when blurred', async () => {
      const user = userEvent.setup();
      render(<EnhancedInput />);
      
      const input = screen.getByRole('textbox');
      await user.click(input);
      await user.tab();
      
      expect(input).not.toHaveClass('ring-2', 'ring-blue-500');
    });

    it('should call onFocus handler when focused', async () => {
      const handleFocus = jest.fn();
      const user = userEvent.setup();
      render(<EnhancedInput onFocus={handleFocus} />);
      
      const input = screen.getByRole('textbox');
      await user.click(input);
      
      expect(handleFocus).toHaveBeenCalled();
    });

    it('should call onBlur handler when blurred', async () => {
      const handleBlur = jest.fn();
      const user = userEvent.setup();
      render(<EnhancedInput onBlur={handleBlur} />);
      
      const input = screen.getByRole('textbox');
      await user.click(input);
      await user.tab();
      
      expect(handleBlur).toHaveBeenCalled();
    });
  });

  describe('Event Handling', () => {
    it('should call onChange handler when value changes', async () => {
      const handleChange = jest.fn();
      const user = userEvent.setup();
      render(<EnhancedInput onChange={handleChange} />);
      
      const input = screen.getByRole('textbox');
      await user.type(input, 'test');
      
      expect(handleChange).toHaveBeenCalled();
    });

    it('should not call onChange when disabled', async () => {
      const handleChange = jest.fn();
      const user = userEvent.setup();
      render(<EnhancedInput onChange={handleChange} disabled />);
      
      const input = screen.getByRole('textbox');
      await user.type(input, 'test');
      
      expect(handleChange).not.toHaveBeenCalled();
    });

    it('should call onKeyDown handler', async () => {
      const handleKeyDown = jest.fn();
      const user = userEvent.setup();
      render(<EnhancedInput onKeyDown={handleKeyDown} />);
      
      const input = screen.getByRole('textbox');
      await user.type(input, 'a');
      
      expect(handleKeyDown).toHaveBeenCalled();
    });
  });

  describe('Props forwarding', () => {
    it('should pass additional HTML attributes', () => {
      render(<EnhancedInput data-testid="test-input" aria-label="Test" />);
      const input = screen.getByTestId('test-input');
      expect(input).toHaveAttribute('aria-label', 'Test');
    });

    it('should handle name attribute', () => {
      render(<EnhancedInput name="username" />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('name', 'username');
    });

    it('should handle id attribute', () => {
      render(<EnhancedInput id="test-id" />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('id', 'test-id');
    });

    it('should handle placeholder attribute', () => {
      render(<EnhancedInput placeholder="Enter text" />);
      const input = screen.getByPlaceholderText('Enter text');
      expect(input).toBeInTheDocument();
    });

    it('should handle type attribute', () => {
      render(<EnhancedInput type="password" />);
      const input = screen.getByDisplayValue('');
      expect(input).toHaveAttribute('type', 'password');
    });

    it('should handle required attribute', () => {
      render(<EnhancedInput required />);
      const input = screen.getByRole('textbox');
      expect(input).toBeRequired();
    });

    it('should handle disabled attribute', () => {
      render(<EnhancedInput disabled />);
      const input = screen.getByRole('textbox');
      expect(input).toBeDisabled();
    });

    it('should handle readOnly attribute', () => {
      render(<EnhancedInput readOnly />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('readonly');
    });

    it('should handle maxLength attribute', () => {
      render(<EnhancedInput maxLength={10} />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('maxlength', '10');
    });
  });

  describe('Controlled Input', () => {
    it('should work as controlled component', () => {
      const TestComponent = () => {
        const [value, setValue] = React.useState('');
        return <EnhancedInput value={value} onChange={(e) => setValue(e.target.value)} />;
      };
      
      render(<TestComponent />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveValue('');
    });

    it('should update controlled value', async () => {
      const TestComponent = () => {
        const [value, setValue] = React.useState('initial');
        return (
          <>
            <EnhancedInput value={value} onChange={(e) => setValue(e.target.value)} />
            <button onClick={() => setValue('updated')}>Update</button>
          </>
        );
      };
      
      const user = userEvent.setup();
      render(<TestComponent />);
      
      const input = screen.getByRole('textbox');
      expect(input).toHaveValue('initial');
      
      const button = screen.getByRole('button', { name: 'Update' });
      await user.click(button);
      
      expect(input).toHaveValue('updated');
    });
  });

  describe('Edge Cases', () => {
    it('should render with empty value', () => {
      render(<EnhancedInput value="" />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveValue('');
    });

    it('should render with long value', () => {
      const longValue = 'a'.repeat(1000);
      render(<EnhancedInput defaultValue={longValue} />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveValue(longValue);
    });

    it('should render with special characters', () => {
      const specialChars = '!@#$%^&*()_+-=[]{}|;:,.<>?';
      render(<EnhancedInput defaultValue={specialChars} />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveValue(specialChars);
    });

    it('should render with unicode characters', () => {
      const unicode = '你好世界🌍';
      render(<EnhancedInput defaultValue={unicode} />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveValue(unicode);
    });

    it('should handle label with icon', () => {
      render(<EnhancedInput label="Search" icon={Search} />);
      expect(screen.getByText('Search')).toBeInTheDocument();
      expect(screen.getByTestId('search-icon')).toBeInTheDocument();
    });

    it('should handle error with icon', () => {
      render(<EnhancedInput error="Error" icon={Search} />);
      expect(screen.getByText('Error')).toBeInTheDocument();
      expect(screen.getByTestId('search-icon')).toBeInTheDocument();
    });

    it('should handle helper text with icon', () => {
      render(<EnhancedInput helperText="Helper" icon={Search} />);
      expect(screen.getByText('Helper')).toBeInTheDocument();
      expect(screen.getByTestId('search-icon')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should support aria-label', () => {
      render(<EnhancedInput aria-label="Search input" />);
      const input = screen.getByLabelText('Search input');
      expect(input).toBeInTheDocument();
    });

    it('should support aria-describedby for helper text', () => {
      render(
        <>
          <EnhancedInput aria-describedby="help-text" helperText="Help" />
          <span id="help-text">Help text</span>
        </>
      );
      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('aria-describedby', 'help-text');
    });

    it('should support aria-invalid for error state', () => {
      render(<EnhancedInput error="Error" aria-invalid="true" />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('aria-invalid', 'true');
    });

    it('should support aria-required for required state', () => {
      render(<EnhancedInput required aria-required="true" />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('aria-required', 'true');
    });
  });

  describe('Integration Tests', () => {
    it('should handle all props together', () => {
      render(
        <EnhancedInput
          label="Search"
          error="Error"
          helperText="Helper"
          icon={Search}
          iconPosition="left"
          fullWidth
          className="custom"
          placeholder="Search..."
        />
      );
      
      expect(screen.getByText('Search')).toBeInTheDocument();
      expect(screen.getByTestId('search-icon')).toBeInTheDocument();
      expect(screen.getByRole('textbox')).toHaveClass('custom');
    });

    it('should transition from normal to error state', () => {
      const { rerender } = render(<EnhancedInput label="Field" />);
      expect(screen.getByText('Field')).toHaveClass('text-gray-700');
      
      rerender(<EnhancedInput label="Field" error="Error" />);
      expect(screen.getByText('Field')).toHaveClass('text-red-600');
    });

    it('should transition from error to normal state', () => {
      const { rerender } = render(<EnhancedInput label="Field" error="Error" />);
      expect(screen.getByText('Field')).toHaveClass('text-red-600');
      
      rerender(<EnhancedInput label="Field" />);
      expect(screen.getByText('Field')).toHaveClass('text-gray-700');
    });
  });
});
