import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Input } from '@/components/ui/input';

describe('Input Component', () => {
  describe('Rendering', () => {
    it('should render input with default props', () => {
      render(<Input />);
      const input = screen.getByRole('textbox');
      expect(input).toBeInTheDocument();
      expect(input).toHaveClass('flex', 'h-10', 'w-full');
    });

    it('should render input with custom className', () => {
      render(<Input className="custom-class" />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveClass('custom-class');
    });

    it('should render disabled input', () => {
      render(<Input disabled />);
      const input = screen.getByRole('textbox');
      expect(input).toBeDisabled();
      expect(input).toHaveClass('disabled:cursor-not-allowed', 'disabled:opacity-50');
    });

    it('should render input with placeholder', () => {
      render(<Input placeholder="Enter text" />);
      const input = screen.getByPlaceholderText('Enter text');
      expect(input).toBeInTheDocument();
    });

    it('should render input with default value', () => {
      render(<Input defaultValue="Default value" />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveValue('Default value');
    });
  });

  describe('Input Types', () => {
    it('should render text input by default', () => {
      render(<Input />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('type', 'text');
    });

    it('should render password input', () => {
      render(<Input type="password" />);
      const input = screen.getByDisplayValue('');
      expect(input).toHaveAttribute('type', 'password');
    });

    it('should render email input', () => {
      render(<Input type="email" />);
      const input = screen.getByDisplayValue('');
      expect(input).toHaveAttribute('type', 'email');
    });

    it('should render number input', () => {
      render(<Input type="number" />);
      const input = screen.getByDisplayValue('');
      expect(input).toHaveAttribute('type', 'number');
    });

    it('should render date input', () => {
      render(<Input type="date" />);
      const input = screen.getByDisplayValue('');
      expect(input).toHaveAttribute('type', 'date');
    });

    it('should render checkbox input', () => {
      render(<Input type="checkbox" />);
      const input = screen.getByRole('checkbox');
      expect(input).toHaveAttribute('type', 'checkbox');
    });

    it('should render file input', () => {
      render(<Input type="file" />);
      // File inputs don't have a role, just verify the input exists
      const input = document.querySelector('input[type="file"]');
      expect(input).toBeInTheDocument();
    });
  });

  describe('Event Handling', () => {
    it('should call onChange handler when value changes', async () => {
      const handleChange = jest.fn();
      const user = userEvent.setup();
      render(<Input onChange={handleChange} />);

      const input = screen.getByRole('textbox');
      await user.type(input, 'test');

      expect(handleChange).toHaveBeenCalled();
    });

    it('should call onFocus handler when focused', async () => {
      const handleFocus = jest.fn();
      const user = userEvent.setup();
      render(<Input onFocus={handleFocus} />);

      const input = screen.getByRole('textbox');
      await user.click(input);

      expect(handleFocus).toHaveBeenCalled();
    });

    it('should call onBlur handler when blurred', async () => {
      const handleBlur = jest.fn();
      const user = userEvent.setup();
      render(<Input onBlur={handleBlur} />);

      const input = screen.getByRole('textbox');
      await user.click(input);
      await user.tab();

      expect(handleBlur).toHaveBeenCalled();
    });

    it('should not call onChange when disabled', async () => {
      const handleChange = jest.fn();
      const user = userEvent.setup();
      render(<Input onChange={handleChange} disabled />);

      const input = screen.getByRole('textbox');
      await user.type(input, 'test');

      expect(handleChange).not.toHaveBeenCalled();
    });

    it('should call onKeyDown handler', async () => {
      const handleKeyDown = jest.fn();
      const user = userEvent.setup();
      render(<Input onKeyDown={handleKeyDown} />);

      const input = screen.getByRole('textbox');
      await user.type(input, 'a');

      expect(handleKeyDown).toHaveBeenCalled();
    });
  });

  describe('Props forwarding', () => {
    it('should forward ref to input element', () => {
      const ref = React.createRef<HTMLInputElement>();
      render(<Input ref={ref} />);

      expect(ref.current).toBeInstanceOf(HTMLInputElement);
    });

    it('should pass additional HTML attributes', () => {
      render(<Input data-testid="test-input" aria-label="Test" />);
      const input = screen.getByTestId('test-input');
      expect(input).toHaveAttribute('aria-label', 'Test');
    });

    it('should handle name attribute', () => {
      render(<Input name="username" />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('name', 'username');
    });

    it('should handle id attribute', () => {
      render(<Input id="test-id" />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('id', 'test-id');
    });

    it('should handle required attribute', () => {
      render(<Input required />);
      const input = screen.getByRole('textbox');
      expect(input).toBeRequired();
    });

    it('should handle readOnly attribute', () => {
      render(<Input readOnly />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('readonly');
    });

    it('should handle maxLength attribute', () => {
      render(<Input maxLength={10} />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('maxlength', '10');
    });

    it('should handle minLength attribute', () => {
      render(<Input minLength={5} />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('minlength', '5');
    });
  });

  describe('Controlled Input', () => {
    it('should work as controlled component', () => {
      const TestComponent = () => {
        const [value, setValue] = React.useState('');
        return <Input value={value} onChange={(e) => setValue(e.target.value)} />;
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
            <Input value={value} onChange={(e) => setValue(e.target.value)} />
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
      render(<Input value="" />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveValue('');
    });

    it('should render with long value', () => {
      const longValue = 'a'.repeat(1000);
      render(<Input defaultValue={longValue} />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveValue(longValue);
    });

    it('should render with special characters', () => {
      const specialChars = '!@#$%^&*()_+-=[]{}|;:,.<>?';
      render(<Input defaultValue={specialChars} />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveValue(specialChars);
    });

    it('should render with unicode characters', () => {
      const unicode = '你好世界🌍';
      render(<Input defaultValue={unicode} />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveValue(unicode);
    });
  });

  describe('Accessibility', () => {
    it('should have proper focus styles', () => {
      render(<Input />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveClass('focus-visible:outline-none', 'focus-visible:ring-2');
    });

    it('should support aria-label', () => {
      render(<Input aria-label="Search input" />);
      const input = screen.getByLabelText('Search input');
      expect(input).toBeInTheDocument();
    });

    it('should support aria-describedby', () => {
      render(
        <>
          <Input aria-describedby="help-text" />
          <span id="help-text">Help text</span>
        </>
      );
      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('aria-describedby', 'help-text');
    });

    it('should support aria-invalid', () => {
      render(<Input aria-invalid="true" />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('aria-invalid', 'true');
    });
  });
});
