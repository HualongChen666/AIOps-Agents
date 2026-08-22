import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Textarea } from '@/components/ui/textarea';

describe('Textarea Component', () => {
  describe('Rendering', () => {
    it('should render textarea with default props', () => {
      render(<Textarea />);
      const textarea = screen.getByRole('textbox');
      expect(textarea).toBeInTheDocument();
      expect(textarea).toHaveClass('flex', 'min-h-[80px]', 'w-full');
    });

    it('should render textarea with custom className', () => {
      render(<Textarea className="custom-class" />);
      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveClass('custom-class');
    });

    it('should render disabled textarea', () => {
      render(<Textarea disabled />);
      const textarea = screen.getByRole('textbox');
      expect(textarea).toBeDisabled();
      expect(textarea).toHaveClass('disabled:cursor-not-allowed', 'disabled:opacity-50');
    });

    it('should render textarea with placeholder', () => {
      render(<Textarea placeholder="Enter text" />);
      const textarea = screen.getByPlaceholderText('Enter text');
      expect(textarea).toBeInTheDocument();
    });

    it('should render textarea with default value', () => {
      render(<Textarea defaultValue="Default value" />);
      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveValue('Default value');
    });
  });

  describe('Event Handling', () => {
    it('should call onChange handler when value changes', async () => {
      const handleChange = jest.fn();
      const user = userEvent.setup();
      render(<Textarea onChange={handleChange} />);
      
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'test');
      
      expect(handleChange).toHaveBeenCalled();
    });

    it('should call onFocus handler when focused', async () => {
      const handleFocus = jest.fn();
      const user = userEvent.setup();
      render(<Textarea onFocus={handleFocus} />);
      
      const textarea = screen.getByRole('textbox');
      await user.click(textarea);
      
      expect(handleFocus).toHaveBeenCalled();
    });

    it('should call onBlur handler when blurred', async () => {
      const handleBlur = jest.fn();
      const user = userEvent.setup();
      render(<Textarea onBlur={handleBlur} />);
      
      const textarea = screen.getByRole('textbox');
      await user.click(textarea);
      await user.tab();
      
      expect(handleBlur).toHaveBeenCalled();
    });

    it('should not call onChange when disabled', async () => {
      const handleChange = jest.fn();
      const user = userEvent.setup();
      render(<Textarea onChange={handleChange} disabled />);
      
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'test');
      
      expect(handleChange).not.toHaveBeenCalled();
    });

    it('should call onKeyDown handler', async () => {
      const handleKeyDown = jest.fn();
      const user = userEvent.setup();
      render(<Textarea onKeyDown={handleKeyDown} />);
      
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'a');
      
      expect(handleKeyDown).toHaveBeenCalled();
    });

    it('should call onInput handler', async () => {
      const handleInput = jest.fn();
      const user = userEvent.setup();
      render(<Textarea onInput={handleInput} />);
      
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'test');
      
      expect(handleInput).toHaveBeenCalled();
    });
  });

  describe('Props forwarding', () => {
    it('should forward ref to textarea element', () => {
      const ref = React.createRef<HTMLTextAreaElement>();
      render(<Textarea ref={ref} />);
      
      expect(ref.current).toBeInstanceOf(HTMLTextAreaElement);
    });

    it('should pass additional HTML attributes', () => {
      render(<Textarea data-testid="test-textarea" aria-label="Test" />);
      const textarea = screen.getByTestId('test-textarea');
      expect(textarea).toHaveAttribute('aria-label', 'Test');
    });

    it('should handle name attribute', () => {
      render(<Textarea name="description" />);
      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveAttribute('name', 'description');
    });

    it('should handle id attribute', () => {
      render(<Textarea id="test-id" />);
      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveAttribute('id', 'test-id');
    });

    it('should handle required attribute', () => {
      render(<Textarea required />);
      const textarea = screen.getByRole('textbox');
      expect(textarea).toBeRequired();
    });

    it('should handle readOnly attribute', () => {
      render(<Textarea readOnly />);
      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveAttribute('readonly');
    });

    it('should handle maxLength attribute', () => {
      render(<Textarea maxLength={500} />);
      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveAttribute('maxlength', '500');
    });

    it('should handle minLength attribute', () => {
      render(<Textarea minLength={10} />);
      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveAttribute('minlength', '10');
    });

    it('should handle rows attribute', () => {
      render(<Textarea rows={5} />);
      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveAttribute('rows', '5');
    });

    it('should handle cols attribute', () => {
      render(<Textarea cols={40} />);
      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveAttribute('cols', '40');
    });

    it('should handle wrap attribute', () => {
      render(<Textarea wrap="hard" />);
      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveAttribute('wrap', 'hard');
    });
  });

  describe('Controlled Textarea', () => {
    it('should work as controlled component', () => {
      const TestComponent = () => {
        const [value, setValue] = React.useState('');
        return <Textarea value={value} onChange={(e) => setValue(e.target.value)} />;
      };
      
      render(<TestComponent />);
      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveValue('');
    });

    it('should update controlled value', async () => {
      const TestComponent = () => {
        const [value, setValue] = React.useState('initial');
        return (
          <>
            <Textarea value={value} onChange={(e) => setValue(e.target.value)} />
            <button onClick={() => setValue('updated')}>Update</button>
          </>
        );
      };
      
      const user = userEvent.setup();
      render(<TestComponent />);
      
      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveValue('initial');
      
      const button = screen.getByRole('button', { name: 'Update' });
      await user.click(button);
      
      expect(textarea).toHaveValue('updated');
    });
  });

  describe('Edge Cases', () => {
    it('should render with empty value', () => {
      render(<Textarea value="" />);
      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveValue('');
    });

    it('should render with long value', () => {
      const longValue = 'a'.repeat(10000);
      render(<Textarea defaultValue={longValue} />);
      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveValue(longValue);
    });

    it('should render with multiline text', () => {
      const multiline = 'Line 1\nLine 2\nLine 3';
      render(<Textarea defaultValue={multiline} />);
      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveValue(multiline);
    });

    it('should render with special characters', () => {
      const specialChars = '!@#$%^&*()_+-=[]{}|;:,.<>?';
      render(<Textarea defaultValue={specialChars} />);
      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveValue(specialChars);
    });

    it('should render with unicode characters', () => {
      const unicode = '你好世界🌍\nこんにちは\n안녕하세요';
      render(<Textarea defaultValue={unicode} />);
      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveValue(unicode);
    });

    it('should render with HTML entities', () => {
      const htmlEntities = '&lt;div&gt;Hello&lt;/div&gt;';
      render(<Textarea defaultValue={htmlEntities} />);
      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveValue(htmlEntities);
    });
  });

  describe('Styling', () => {
    it('should have correct base styles', () => {
      render(<Textarea />);
      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveClass('flex', 'min-h-[80px]', 'w-full', 'rounded-md', 'border', 'border-gray-300', 'bg-white');
    });

    it('should have correct padding', () => {
      render(<Textarea />);
      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveClass('px-3', 'py-2');
    });

    it('should have correct text styles', () => {
      render(<Textarea />);
      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveClass('text-sm');
    });

    it('should have correct focus styles', () => {
      render(<Textarea />);
      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveClass('focus-visible:outline-none', 'focus-visible:ring-2', 'focus-visible:ring-blue-500');
    });

    it('should have correct disabled styles', () => {
      render(<Textarea disabled />);
      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveClass('disabled:cursor-not-allowed', 'disabled:opacity-50');
    });
  });

  describe('Accessibility', () => {
    it('should support aria-label', () => {
      render(<Textarea aria-label="Description input" />);
      const textarea = screen.getByLabelText('Description input');
      expect(textarea).toBeInTheDocument();
    });

    it('should support aria-describedby', () => {
      render(
        <>
          <Textarea aria-describedby="help-text" />
          <span id="help-text">Help text</span>
        </>
      );
      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveAttribute('aria-describedby', 'help-text');
    });

    it('should support aria-invalid', () => {
      render(<Textarea aria-invalid="true" />);
      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveAttribute('aria-invalid', 'true');
    });

    it('should support aria-required', () => {
      render(<Textarea aria-required="true" />);
      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveAttribute('aria-required', 'true');
    });

    it('should support placeholder for accessibility', () => {
      render(<Textarea placeholder="Enter your message" />);
      const textarea = screen.getByPlaceholderText('Enter your message');
      expect(textarea).toBeInTheDocument();
    });
  });

  describe('User Interaction', () => {
    it('should allow typing text', async () => {
      const user = userEvent.setup();
      render(<Textarea />);
      
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Hello World');
      
      expect(textarea).toHaveValue('Hello World');
    });

    it('should allow deleting text', async () => {
      const user = userEvent.setup();
      render(<Textarea defaultValue="Hello World" />);
      
      const textarea = screen.getByRole('textbox');
      await user.click(textarea);
      await user.keyboard('{Control>}{End}{/Control}');
      await user.type(textarea, '{backspace}'.repeat(5));
      
      expect(textarea).toHaveValue('Hello ');
    });

    it('should allow selecting text', async () => {
      const user = userEvent.setup();
      render(<Textarea defaultValue="Hello World" />);
      
      const textarea = screen.getByRole('textbox');
      await user.click(textarea);
      await user.keyboard('{Control>}{a}{/Control}');
      
      expect(textarea).toHaveFocus();
    });

    it('should handle paste operation', async () => {
      const user = userEvent.setup();
      render(<Textarea />);
      
      const textarea = screen.getByRole('textbox');
      await user.click(textarea);
      
      const clipboardData = {
        getData: jest.fn(() => 'Pasted text'),
      };
      
      await user.paste('Pasted text');
      
      expect(textarea).toHaveValue('Pasted text');
    });
  });
});
