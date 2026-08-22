import { describe, it, expect } from '@jest/globals';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Form, useForm, FormActions } from '@/components/ui/Form';

describe('Form Component Tests', () => {
  describe('Form Component', () => {
    it('should render form with children', () => {
      render(
        <Form initialValues={{ name: '' }} onSubmit={jest.fn()}>
          <input data-testid="name-input" name="name" />
        </Form>
      );

      expect(screen.getByTestId('name-input')).toBeInTheDocument();
    });

    it('should call onSubmit with form values', async () => {
      const handleSubmit = jest.fn();

      render(
        <Form initialValues={{ name: '' }} onSubmit={handleSubmit}>
          <input
            data-testid="name-input"
            name="name"
            value="Test"
            onChange={(e) => e.target.value}
          />
          <button type="submit">Submit</button>
        </Form>
      );

      const submitButton = screen.getByText('Submit');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(handleSubmit).toHaveBeenCalled();
      });
    });

    it('should validate form before submission', async () => {
      const handleSubmit = jest.fn();
      const validation = (values: any) => {
        const errors: any = {};
        if (!values.name) errors.name = 'Name is required';
        return errors;
      };

      render(
        <Form
          initialValues={{ name: '' }}
          onSubmit={handleSubmit}
          validation={validation}
        >
          <input data-testid="name-input" name="name" value="" />
          <button type="submit">Submit</button>
        </Form>
      );

      const submitButton = screen.getByText('Submit');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(handleSubmit).not.toHaveBeenCalled();
      });
    });

    it('should show validation errors', async () => {
      const validation = (values: any) => {
        const errors: any = {};
        if (!values.name) errors.name = 'Name is required';
        if (!values.email) errors.email = 'Email is required';
        return errors;
      };

      const TestForm = () => {
        const { errors, setFieldValue, handleSubmit } = useForm();

        return (
          <form onSubmit={handleSubmit}>
            <input
              data-testid="name-input"
              value=""
              onChange={(e) => setFieldValue('name', e.target.value)}
            />
            {errors.name && <span data-testid="name-error">{errors.name}</span>}

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
        <Form initialValues={{ name: '', email: '' }} onSubmit={jest.fn()} validation={validation}>
          <TestForm />
        </Form>
      );

      const submitButton = screen.getByText('Submit');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByTestId('name-error')).toHaveTextContent('Name is required');
        expect(screen.getByTestId('email-error')).toHaveTextContent('Email is required');
      });
    });

    it('should reset form to initial values', () => {
      const TestForm = () => {
        const { values, setFieldValue, reset } = useForm();

        return (
          <form>
            <input
              data-testid="name-input"
              value={values.name}
              onChange={(e) => setFieldValue('name', e.target.value)}
            />
            <button type="button" onClick={reset}>Reset</button>
          </form>
        );
      };

      render(
        <Form initialValues={{ name: 'Initial' }} onSubmit={jest.fn()}>
          <TestForm />
        </Form>
      );

      const input = screen.getByTestId('name-input');
      fireEvent.change(input, { target: { value: 'Changed' } });
      expect(input).toHaveValue('Changed');

      const resetButton = screen.getByText('Reset');
      fireEvent.click(resetButton);

      expect(input).toHaveValue('Initial');
    });

    it('should set isSubmitting during submission', async () => {
      const handleSubmit = jest.fn(() => new Promise(resolve => setTimeout(resolve, 100)));

      const TestForm = () => {
        const { isSubmitting, handleSubmit } = useForm();

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

    it('should track touched fields', () => {
      const TestForm = () => {
        const { touched, setFieldTouched, setFieldValue } = useForm();

        return (
          <form>
            <input
              data-testid="name-input"
              onChange={(e) => {
                setFieldValue('name', e.target.value);
                setFieldTouched('name', true);
              }}
            />
            {touched.name && <span data-testid="touched-indicator">Touched</span>}
          </form>
        );
      };

      render(
        <Form initialValues={{ name: '' }} onSubmit={jest.fn()}>
          <TestForm />
        </Form>
      );

      expect(screen.queryByTestId('touched-indicator')).not.toBeInTheDocument();

      const input = screen.getByTestId('name-input');
      fireEvent.change(input, { target: { value: 'Test' } });

      expect(screen.getByTestId('touched-indicator')).toBeInTheDocument();
    });
  });

  describe('useForm Hook', () => {
    it('should provide all context values', () => {
      const TestForm = () => {
        const context = useForm();

        expect(context).toHaveProperty('values');
        expect(context).toHaveProperty('errors');
        expect(context).toHaveProperty('touched');
        expect(context).toHaveProperty('isSubmitting');
        expect(context).toHaveProperty('setFieldValue');
        expect(context).toHaveProperty('setFieldTouched');
        expect(context).toHaveProperty('handleSubmit');
        expect(context).toHaveProperty('reset');

        return null;
      };

      render(
        <Form initialValues={{}} onSubmit={jest.fn()}>
          <TestForm />
        </Form>
      );
    });
  });

  describe('FormActions Component', () => {
    it('should render submit and cancel buttons', () => {
      const handleCancel = jest.fn();

      render(
        <Form initialValues={{}} onSubmit={jest.fn()}>
          <FormActions onCancel={handleCancel} />
        </Form>
      );

      expect(screen.getByText('取消')).toBeInTheDocument();
      expect(screen.getByText('提交')).toBeInTheDocument();
    });

    it('should call onCancel when cancel button clicked', () => {
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

    it('should reset form when cancel button clicked', () => {
      const handleCancel = jest.fn();

      const TestForm = () => {
        const { values, setFieldValue } = useForm();

        return (
          <form>
            <input
              data-testid="name-input"
              value={values.name}
              onChange={(e) => setFieldValue('name', e.target.value)}
            />
            <FormActions onCancel={handleCancel} />
          </form>
        );
      };

      render(
        <Form initialValues={{ name: 'Initial' }} onSubmit={jest.fn()}>
          <TestForm />
        </Form>
      );

      const input = screen.getByTestId('name-input');
      fireEvent.change(input, { target: { value: 'Changed' } });
      expect(input).toHaveValue('Changed');

      const cancelButton = screen.getByText('取消');
      fireEvent.click(cancelButton);

      expect(input).toHaveValue('Initial');
    });

    it('should disable buttons when submitting', async () => {
      const handleSubmit = jest.fn(() => new Promise(resolve => setTimeout(resolve, 100)));

      const TestForm = () => {
        const { handleSubmit } = useForm();

        return (
          <form onSubmit={handleSubmit}>
            <FormActions />
          </form>
        );
      };

      render(
        <Form initialValues={{}} onSubmit={handleSubmit}>
          <TestForm />
        </Form>
      );

      const submitButton = screen.getByText('提交');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(submitButton).toBeDisabled();
      });

      await waitFor(() => {
        expect(submitButton).not.toBeDisabled();
      }, { timeout: 200 });
    });

    it('should show loading text when submitting', async () => {
      const handleSubmit = jest.fn(() => new Promise(resolve => setTimeout(resolve, 100)));

      const TestForm = () => {
        const { handleSubmit } = useForm();

        return (
          <form onSubmit={handleSubmit}>
            <FormActions />
          </form>
        );
      };

      render(
        <Form initialValues={{}} onSubmit={handleSubmit}>
          <TestForm />
        </Form>
      );

      const submitButton = screen.getByText('提交');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('提交中...')).toBeInTheDocument();
      });
    });

    it('should not render cancel button when onCancel not provided', () => {
      render(
        <Form initialValues={{}} onSubmit={jest.fn()}>
          <FormActions />
        </Form>
      );

      expect(screen.queryByText('取消')).not.toBeInTheDocument();
      expect(screen.getByText('提交')).toBeInTheDocument();
    });
  });

  describe('Form Validation Scenarios', () => {
    it('should validate required fields', async () => {
      const validation = (values: any) => {
        const errors: any = {};
        if (!values.name?.trim()) errors.name = 'Name is required';
        if (!values.email?.trim()) errors.email = 'Email is required';
        return errors;
      };

      const handleSubmit = jest.fn();

      const TestForm = () => {
        const { errors, setFieldValue, handleSubmit } = useForm();

        return (
          <form onSubmit={handleSubmit}>
            <input
              data-testid="name-input"
              value=""
              onChange={(e) => setFieldValue('name', e.target.value)}
            />
            {errors.name && <span data-testid="name-error">{errors.name}</span>}

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
        <Form
          initialValues={{ name: '', email: '' }}
          onSubmit={handleSubmit}
          validation={validation}
        >
          <TestForm />
        </Form>
      );

      const submitButton = screen.getByText('Submit');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(handleSubmit).not.toHaveBeenCalled();
        expect(screen.getByTestId('name-error')).toBeInTheDocument();
        expect(screen.getByTestId('email-error')).toBeInTheDocument();
      });
    });
  });

  describe('Form Edge Cases', () => {
    it('should handle empty initial values', () => {
      render(
        <Form initialValues={{}} onSubmit={jest.fn()}>
          <div>Form Content</div>
        </Form>
      );

      expect(screen.getByText('Form Content')).toBeInTheDocument();
    });

    it('should handle null values', () => {
      render(
        <Form initialValues={{ name: null as any }} onSubmit={jest.fn()}>
          <div>Form Content</div>
        </Form>
      );

      expect(screen.getByText('Form Content')).toBeInTheDocument();
    });

    it('should handle undefined values', () => {
      render(
        <Form initialValues={{ name: undefined as any }} onSubmit={jest.fn()}>
          <div>Form Content</div>
        </Form>
      );

      expect(screen.getByText('Form Content')).toBeInTheDocument();
    });

    it('should handle rapid field changes', () => {
      const TestForm = () => {
        const { values, setFieldValue } = useForm();

        return (
          <form>
            <input
              data-testid="name-input"
              value={values.name}
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

      const input = screen.getByTestId('name-input');

      for (let i = 0; i < 10; i++) {
        fireEvent.change(input, { target: { value: `Value ${i}` } });
      }

      expect(input).toHaveValue('Value 9');
    });
  });
});
