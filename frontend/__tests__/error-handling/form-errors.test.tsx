/**
 * Comprehensive Form Error Handling Tests
 * Tests validation errors, submission errors, and error recovery mechanisms
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Form, useForm, FormActions } from '@/components/ui/Form';
import { useFormValidation } from '@/hooks/useEnhancements';

describe('Form Error Handling', () => {
  describe('Validation Error Handling', () => {
    it('should display validation errors for required fields', async () => {
      const validation = (values: any) => {
        const errors: any = {};
        if (!values.username) errors.username = 'Username is required';
        if (!values.email) errors.email = 'Email is required';
        if (!values.password) errors.password = 'Password is required';
        return errors;
      };

      const TestForm = () => {
        const { errors, setFieldValue, handleSubmit } = useForm();

        return (
          <form onSubmit={handleSubmit}>
            <input
              data-testid="username-input"
              value=""
              onChange={(e) => setFieldValue('username', e.target.value)}
            />
            {errors.username && <span data-testid="username-error">{errors.username}</span>}

            <input
              data-testid="email-input"
              value=""
              onChange={(e) => setFieldValue('email', e.target.value)}
            />
            {errors.email && <span data-testid="email-error">{errors.email}</span>}

            <input
              data-testid="password-input"
              value=""
              onChange={(e) => setFieldValue('password', e.target.value)}
            />
            {errors.password && <span data-testid="password-error">{errors.password}</span>}

            <button type="submit">Submit</button>
          </form>
        );
      };

      render(
        <Form initialValues={{ username: '', email: '', password: '' }} onSubmit={jest.fn()} validation={validation}>
          <TestForm />
        </Form>
      );

      const submitButton = screen.getByText('Submit');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByTestId('username-error')).toHaveTextContent('Username is required');
        expect(screen.getByTestId('email-error')).toHaveTextContent('Email is required');
        expect(screen.getByTestId('password-error')).toHaveTextContent('Password is required');
      });
    });

    it('should display validation errors for email format', async () => {
      const validation = (values: any) => {
        const errors: any = {};
        if (values.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.email)) {
          errors.email = 'Invalid email format';
        }
        return errors;
      };

      const TestForm = () => {
        const { errors, setFieldValue, handleSubmit } = useForm();

        return (
          <form onSubmit={handleSubmit}>
            <input
              data-testid="email-input"
              value="invalid-email"
              onChange={(e) => setFieldValue('email', e.target.value)}
            />
            {errors.email && <span data-testid="email-error">{errors.email}</span>}
            <button type="submit">Submit</button>
          </form>
        );
      };

      render(
        <Form initialValues={{ email: 'invalid-email' }} onSubmit={jest.fn()} validation={validation}>
          <TestForm />
        </Form>
      );

      const submitButton = screen.getByText('Submit');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByTestId('email-error')).toHaveTextContent('Invalid email format');
      });
    });

    it('should display validation errors for minimum length', async () => {
      const validation = (values: any) => {
        const errors: any = {};
        if (values.password && values.password.length < 8) {
          errors.password = 'Password must be at least 8 characters';
        }
        return errors;
      };

      const TestForm = () => {
        const { errors, setFieldValue, handleSubmit } = useForm();

        return (
          <form onSubmit={handleSubmit}>
            <input
              data-testid="password-input"
              value="short"
              onChange={(e) => setFieldValue('password', e.target.value)}
            />
            {errors.password && <span data-testid="password-error">{errors.password}</span>}
            <button type="submit">Submit</button>
          </form>
        );
      };

      render(
        <Form initialValues={{ password: 'short' }} onSubmit={jest.fn()} validation={validation}>
          <TestForm />
        </Form>
      );

      const submitButton = screen.getByText('Submit');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByTestId('password-error')).toHaveTextContent('Password must be at least 8 characters');
      });
    });

    it('should display validation errors for maximum length', async () => {
      const validation = (values: any) => {
        const errors: any = {};
        if (values.username && values.username.length > 20) {
          errors.username = 'Username must be less than 20 characters';
        }
        return errors;
      };

      const TestForm = () => {
        const { errors, setFieldValue, handleSubmit } = useForm();

        return (
          <form onSubmit={handleSubmit}>
            <input
              data-testid="username-input"
              value="very-long-username-that-exceeds-limit"
              onChange={(e) => setFieldValue('username', e.target.value)}
            />
            {errors.username && <span data-testid="username-error">{errors.username}</span>}
            <button type="submit">Submit</button>
          </form>
        );
      };

      render(
        <Form initialValues={{ username: 'very-long-username-that-exceeds-limit' }} onSubmit={jest.fn()} validation={validation}>
          <TestForm />
        </Form>
      );

      const submitButton = screen.getByText('Submit');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByTestId('username-error')).toHaveTextContent('Username must be less than 20 characters');
      });
    });

    it('should display validation errors for pattern matching', async () => {
      const validation = (values: any) => {
        const errors: any = {};
        if (values.phone && !/^\d{10}$/.test(values.phone)) {
          errors.phone = 'Phone must be 10 digits';
        }
        return errors;
      };

      const TestForm = () => {
        const { errors, setFieldValue, handleSubmit } = useForm();

        return (
          <form onSubmit={handleSubmit}>
            <input
              data-testid="phone-input"
              value="123"
              onChange={(e) => setFieldValue('phone', e.target.value)}
            />
            {errors.phone && <span data-testid="phone-error">{errors.phone}</span>}
            <button type="submit">Submit</button>
          </form>
        );
      };

      render(
        <Form initialValues={{ phone: '123' }} onSubmit={jest.fn()} validation={validation}>
          <TestForm />
        </Form>
      );

      const submitButton = screen.getByText('Submit');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByTestId('phone-error')).toHaveTextContent('Phone must be 10 digits');
      });
    });

    it('should clear validation errors when user fixes input', async () => {
      const validation = (values: any) => {
        const errors: any = {};
        if (!values.email) errors.email = 'Email is required';
        return errors;
      };

      const TestForm = () => {
        const { errors, setFieldValue, handleSubmit } = useForm();

        return (
          <form onSubmit={handleSubmit}>
            <input
              data-testid="email-input"
              value=""
              onChange={(e) => setFieldValue('email', e.target.value)}
            />
            {errors.email && <span data-testid="email-error">{errors.email}</span>}
            <button type="submit">Submit</button>
          </form>
        );
      };

      render(
        <Form initialValues={{ email: '' }} onSubmit={jest.fn()} validation={validation}>
          <TestForm />
        </Form>
      );

      const submitButton = screen.getByText('Submit');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByTestId('email-error')).toBeInTheDocument();
      });

      const emailInput = screen.getByTestId('email-input');
      fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.queryByTestId('email-error')).not.toBeInTheDocument();
      });
    });
  });

  describe('Submission Error Handling', () => {
    it('should handle submission errors gracefully', async () => {
      const handleSubmit = jest.fn().mockRejectedValue(new Error('Submission failed'));
      const validation = (values: any) => {
        if (!values.email) return { email: 'Email is required' };
        return {};
      };

      const TestForm = () => {
        const { errors, setFieldValue, handleSubmit, isSubmitting } = useForm();

        return (
          <form onSubmit={handleSubmit}>
            <input
              data-testid="email-input"
              value="test@example.com"
              onChange={(e) => setFieldValue('email', e.target.value)}
            />
            {errors.email && <span data-testid="email-error">{errors.email}</span>}
            {errors.submit && <span data-testid="submit-error">{errors.submit}</span>}
            <button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Submitting...' : 'Submit'}
            </button>
          </form>
        );
      };

      render(
        <Form initialValues={{ email: 'test@example.com' }} onSubmit={handleSubmit} validation={validation}>
          <TestForm />
        </Form>
      );

      const submitButton = screen.getByText('Submit');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(handleSubmit).toHaveBeenCalled();
      });
    });

    it('should set isSubmitting to true during submission', async () => {
      const handleSubmit = jest.fn().mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 100))
      );

      const TestForm = () => {
        const { handleSubmit, isSubmitting } = useForm();

        return (
          <form onSubmit={handleSubmit}>
            <button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Submitting...' : 'Submit'}
            </button>
          </form>
        );
      };

      render(
        <Form initialValues={{}} onSubmit={handleSubmit}>
          <TestForm />
        </Form>
      );

      const submitButton = screen.getByText('Submit');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Submitting...')).toBeInTheDocument();
      });

      await waitFor(() => {
        expect(screen.getByText('Submit')).toBeInTheDocument();
      }, { timeout: 200 });
    });

    it('should reset isSubmitting after successful submission', async () => {
      const handleSubmit = jest.fn().mockResolvedValue(undefined);

      const TestForm = () => {
        const { handleSubmit, isSubmitting } = useForm();

        return (
          <form onSubmit={handleSubmit}>
            <button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Submitting...' : 'Submit'}
            </button>
          </form>
        );
      };

      render(
        <Form initialValues={{}} onSubmit={handleSubmit}>
          <TestForm />
        </Form>
      );

      const submitButton = screen.getByText('Submit');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Submit')).toBeInTheDocument();
        expect(handleSubmit).toHaveBeenCalled();
      });
    });

    it('should reset isSubmitting after failed submission', async () => {
      const handleSubmit = jest.fn().mockRejectedValue(new Error('Error'));

      const TestForm = () => {
        const { handleSubmit, isSubmitting } = useForm();

        return (
          <form onSubmit={handleSubmit}>
            <button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Submitting...' : 'Submit'}
            </button>
          </form>
        );
      };

      render(
        <Form initialValues={{}} onSubmit={handleSubmit}>
          <TestForm />
        </Form>
      );

      const submitButton = screen.getByText('Submit');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Submit')).toBeInTheDocument();
        expect(handleSubmit).toHaveBeenCalled();
      });
    });

    it('should prevent double submission', async () => {
      const handleSubmit = jest.fn().mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 200))
      );

      const TestForm = () => {
        const { handleSubmit, isSubmitting } = useForm();

        return (
          <form onSubmit={handleSubmit}>
            <button type="submit" disabled={isSubmitting} data-testid="submit-button">
              Submit
            </button>
          </form>
        );
      };

      render(
        <Form initialValues={{}} onSubmit={handleSubmit}>
          <TestForm />
        </Form>
      );

      const submitButton = screen.getByTestId('submit-button');
      fireEvent.click(submitButton);
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(handleSubmit).toHaveBeenCalledTimes(1);
      });
    });
  });

  describe('Form Reset Error Handling', () => {
    it('should reset form values on reset', () => {
      const TestForm = () => {
        const { values, setFieldValue, reset } = useForm();

        return (
          <form>
            <input
              data-testid="name-input"
              value={values.name || ''}
              onChange={(e) => setFieldValue('name', e.target.value)}
            />
            <button type="button" onClick={reset} data-testid="reset-button">
              Reset
            </button>
          </form>
        );
      };

      render(
        <Form initialValues={{ name: 'initial' }} onSubmit={jest.fn()}>
          <TestForm />
        </Form>
      );

      const nameInput = screen.getByTestId('name-input');
      fireEvent.change(nameInput, { target: { value: 'changed' } });

      expect(nameInput).toHaveValue('changed');

      const resetButton = screen.getByTestId('reset-button');
      fireEvent.click(resetButton);

      expect(nameInput).toHaveValue('initial');
    });

    it('should reset errors on reset', async () => {
      const validation = (values: any) => {
        if (!values.name) return { name: 'Name is required' };
        return {};
      };

      const TestForm = () => {
        const { errors, setFieldValue, handleSubmit, reset } = useForm();

        return (
          <form onSubmit={handleSubmit}>
            <input
              data-testid="name-input"
              value=""
              onChange={(e) => setFieldValue('name', e.target.value)}
            />
            {errors.name && <span data-testid="name-error">{errors.name}</span>}
            <button type="submit">Submit</button>
            <button type="button" onClick={reset} data-testid="reset-button">
              Reset
            </button>
          </form>
        );
      };

      render(
        <Form initialValues={{ name: '' }} onSubmit={jest.fn()} validation={validation}>
          <TestForm />
        </Form>
      );

      const submitButton = screen.getByText('Submit');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByTestId('name-error')).toBeInTheDocument();
      });

      const resetButton = screen.getByTestId('reset-button');
      fireEvent.click(resetButton);

      await waitFor(() => {
        expect(screen.queryByTestId('name-error')).not.toBeInTheDocument();
      });
    });

    it('should reset touched state on reset', () => {
      const TestForm = () => {
        const { touched, setFieldValue, reset } = useForm();

        return (
          <form>
            <input
              data-testid="name-input"
              value=""
              onChange={(e) => setFieldValue('name', e.target.value)}
            />
            <span data-testid="touched-state">{touched.name ? 'touched' : 'untouched'}</span>
            <button type="button" onClick={reset} data-testid="reset-button">
              Reset
            </button>
          </form>
        );
      };

      render(
        <Form initialValues={{ name: '' }} onSubmit={jest.fn()}>
          <TestForm />
        </Form>
      );

      const nameInput = screen.getByTestId('name-input');
      fireEvent.change(nameInput, { target: { value: 'test' } });

      expect(screen.getByTestId('touched-state')).toHaveTextContent('touched');

      const resetButton = screen.getByTestId('reset-button');
      fireEvent.click(resetButton);

      expect(screen.getByTestId('touched-state')).toHaveTextContent('untouched');
    });
  });

  describe('FormActions Error Handling', () => {
    it('should handle cancel action', () => {
      const handleCancel = jest.fn();

      render(
        <Form initialValues={{}} onSubmit={jest.fn()}>
          <FormActions onCancel={handleCancel} />
        </Form>
      );

      const cancelButton = screen.getByText('取消');
      fireEvent.click(cancelButton);

      expect(handleCancel).toHaveBeenCalled();
    });

    it('should disable submit button during submission', async () => {
      const handleSubmit = jest.fn().mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 100))
      );

      render(
        <Form initialValues={{}} onSubmit={handleSubmit}>
          <FormActions />
        </Form>
      );

      const submitButton = screen.getByText('提交');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(submitButton).toBeDisabled();
      });
    });

    it('should show loading state when isLoading is true', () => {
      render(
        <Form initialValues={{}} onSubmit={jest.fn()}>
          <FormActions isLoading={true} />
        </Form>
      );

      const submitButton = screen.getByText('提交');
      expect(submitButton).toBeDisabled();
    });

    it('should use custom submit text', () => {
      render(
        <Form initialValues={{}} onSubmit={jest.fn()}>
          <FormActions submitText="Save" />
        </Form>
      );

      expect(screen.getByText('Save')).toBeInTheDocument();
      expect(screen.queryByText('提交')).not.toBeInTheDocument();
    });

    it('should use custom cancel text', () => {
      render(
        <Form initialValues={{}} onSubmit={jest.fn()}>
          <FormActions cancelText="Close" onCancel={jest.fn()} />
        </Form>
      );

      expect(screen.getByText('Close')).toBeInTheDocument();
      expect(screen.queryByText('取消')).not.toBeInTheDocument();
    });
  });

  describe('useFormValidation Hook Error Handling', () => {
    it('should handle missing validation rules', () => {
      const { result } = require('@testing-library/react').renderHook(() =>
        useFormValidation({ name: '' }, {})
      );

      expect(result.current.errors).toEqual({});
    });

    it('should handle empty values', () => {
      const validationRules = {
        name: { required: true },
      };

      const { result } = require('@testing-library/react').renderHook(() =>
        useFormValidation({ name: '' }, validationRules)
      );

      const isValid = result.current.validate();
      expect(isValid).toBe(false);
      expect(result.current.errors.name).toBe('This field is required');
    });

    it('should handle null values', () => {
      const validationRules = {
        name: { required: true },
      };

      const { result } = require('@testing-library/react').renderHook(() =>
        useFormValidation({ name: null }, validationRules)
      );

      const isValid = result.current.validate();
      expect(isValid).toBe(false);
      expect(result.current.errors.name).toBe('This field is required');
    });

    it('should handle undefined values', () => {
      const validationRules = {
        name: { required: true },
      };

      const { result } = require('@testing-library/react').renderHook(() =>
        useFormValidation({ name: undefined }, validationRules)
      );

      const isValid = result.current.validate();
      expect(isValid).toBe(false);
      expect(result.current.errors.name).toBe('This field is required');
    });

    it('should handle multiple validation errors', () => {
      const validationRules = {
        email: { required: true, pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/ },
        password: { required: true, minLength: 8 },
      };

      const { result } = require('@testing-library/react').renderHook(() =>
        useFormValidation({ email: 'invalid', password: 'short' }, validationRules)
      );

      const isValid = result.current.validate();
      expect(isValid).toBe(false);
      expect(result.current.errors.email).toBeDefined();
      expect(result.current.errors.password).toBeDefined();
    });

    it('should handle custom validation function', () => {
      const validationRules = {
        age: {
          custom: (value: string) => {
            const num = parseInt(value);
            if (isNaN(num) || num < 18) return 'Must be at least 18';
            return true;
          },
        },
      };

      const { result } = require('@testing-library/react').renderHook(() =>
        useFormValidation({ age: '15' }, validationRules)
      );

      const isValid = result.current.validate();
      expect(isValid).toBe(false);
      expect(result.current.errors.age).toBe('Must be at least 18');
    });

    it('should handle successful validation', () => {
      const validationRules = {
        name: { required: true },
        email: { required: true, pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/ },
      };

      const { result } = require('@testing-library/react').renderHook(() =>
        useFormValidation({ name: 'John', email: 'john@example.com' }, validationRules)
      );

      const isValid = result.current.validate();
      expect(isValid).toBe(true);
      expect(Object.keys(result.current.errors)).toHaveLength(0);
    });
  });

  describe('Edge Cases and Error Scenarios', () => {
    it('should handle useForm outside Form context', () => {
      const TestComponent = () => {
        try {
          useForm();
          return <div>No error</div>;
        } catch (error) {
          return <div>Error: {(error as Error).message}</div>;
        }
      };

      render(<TestComponent />);
      expect(screen.getByText('Error: useForm must be used within a Form component')).toBeInTheDocument();
    });

    it('should handle undefined validation function', () => {
      const handleSubmit = jest.fn();

      const TestForm = () => {
        const { handleSubmit } = useForm();

        return (
          <form onSubmit={handleSubmit}>
            <button type="submit">Submit</button>
          </form>
        );
      };

      render(
        <Form initialValues={{}} onSubmit={handleSubmit}>
          <TestForm />
        </Form>
      );

      const submitButton = screen.getByText('Submit');
      fireEvent.click(submitButton);

      expect(handleSubmit).toHaveBeenCalled();
    });

    it('should handle validation function returning null', () => {
      const validation = jest.fn().mockReturnValue(null);
      const handleSubmit = jest.fn();

      const TestForm = () => {
        const { handleSubmit } = useForm();

        return (
          <form onSubmit={handleSubmit}>
            <button type="submit">Submit</button>
          </form>
        );
      };

      render(
        <Form initialValues={{}} onSubmit={handleSubmit} validation={validation}>
          <TestForm />
        </Form>
      );

      const submitButton = screen.getByText('Submit');
      fireEvent.click(submitButton);

      expect(handleSubmit).toHaveBeenCalled();
    });

    it('should handle validation function throwing error', () => {
      const validation = jest.fn().mockImplementation(() => {
        throw new Error('Validation error');
      });
      const handleSubmit = jest.fn();

      const TestForm = () => {
        const { handleSubmit } = useForm();

        return (
          <form onSubmit={handleSubmit}>
            <button type="submit">Submit</button>
          </form>
        );
      };

      render(
        <Form initialValues={{}} onSubmit={handleSubmit} validation={validation}>
          <TestForm />
        </Form>
      );

      const submitButton = screen.getByText('Submit');
      
      expect(() => fireEvent.click(submitButton)).toThrow('Validation error');
    });

    it('should handle rapid value changes', () => {
      const TestForm = () => {
        const { values, setFieldValue } = useForm();

        return (
          <form>
            <input
              data-testid="input"
              value={values.name || ''}
              onChange={(e) => setFieldValue('name', e.target.value)}
            />
          </form>
        );
      };

      render(
        <Form initialValues={{ name: '' }} onSubmit={jest.fn()}>
          <TestForm />
        </Form>
      );

      const input = screen.getByTestId('input');
      
      // Simulate rapid changes
      fireEvent.change(input, { target: { value: 'a' } });
      fireEvent.change(input, { target: { value: 'ab' } });
      fireEvent.change(input, { target: { value: 'abc' } });
      fireEvent.change(input, { target: { value: 'abcd' } });

      expect(input).toHaveValue('abcd');
    });

    it('should handle form with no initial values', () => {
      const TestForm = () => {
        const { values } = useForm();

        return (
          <form>
            <span data-testid="values">{JSON.stringify(values)}</span>
          </form>
        );
      };

      render(
        <Form initialValues={{}} onSubmit={jest.fn()}>
          <TestForm />
        </Form>
      );

      expect(screen.getByTestId('values')).toHaveTextContent('{}');
    });
  });
});
