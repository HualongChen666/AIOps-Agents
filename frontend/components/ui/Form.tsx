'use client';

import { createContext, useContext, useState, useCallback } from 'react';
import { Button } from '@/components/ui/button';

interface FormContextValue {
  values: Record<string, any>;
  errors: Record<string, string>;
  touched: Record<string, boolean>;
  isSubmitting: boolean;
  setFieldValue: (field: string, value: any) => void;
  setFieldTouched: (field: string, touched: boolean) => void;
  handleSubmit: (e: React.FormEvent) => void;
  reset: () => void;
}

const FormContext = createContext<FormContextValue | undefined>(undefined);

interface FormProps {
  initialValues: Record<string, any>;
  onSubmit: (values: Record<string, any>) => void | Promise<void>;
  validation?: (values: Record<string, any>) => Record<string, string>;
  children: React.ReactNode;
}

export function Form({ initialValues, onSubmit, validation, children }: FormProps) {
  const [values, setValues] = useState(initialValues);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const setFieldValue = useCallback((field: string, value: any) => {
    setValues((prev) => ({ ...prev, [field]: value }));
    setTouched((prev) => ({ ...prev, [field]: true }));
  }, []);

  const setFieldTouched = useCallback((field: string, fieldTouched: boolean) => {
    setTouched((prev) => ({ ...prev, [field]: fieldTouched }));
  }, []);

  const validate = useCallback(() => {
    if (!validation) return {};
    const validationErrors = validation(values);
    setErrors(validationErrors);
    return validationErrors;
  }, [validation, values]);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      const validationErrors = validate();
      if (Object.keys(validationErrors).length > 0) return;

      setIsSubmitting(true);
      try {
        await onSubmit(values);
      } finally {
        setIsSubmitting(false);
      }
    },
    [onSubmit, values, validate]
  );

  const reset = useCallback(() => {
    setValues(initialValues);
    setErrors({});
    setTouched({});
  }, [initialValues]);

  return (
    <FormContext.Provider
      value={{
        values,
        errors,
        touched,
        isSubmitting,
        setFieldValue,
        setFieldTouched,
        handleSubmit,
        reset,
      }}
    >
      <form onSubmit={handleSubmit} role="form">{children}</form>
    </FormContext.Provider>
  );
}

export function useForm() {
  const context = useContext(FormContext);
  if (!context) {
    throw new Error('useForm must be used within a Form component');
  }
  return context;
}

export function FormActions({
  onCancel,
  submitText = '提交',
  cancelText = '取消',
  isLoading = false,
}: {
  onCancel?: () => void;
  submitText?: string;
  cancelText?: string;
  isLoading?: boolean;
}) {
  const { isSubmitting, reset } = useForm();

  const handleCancel = () => {
    reset();
    onCancel?.();
  };

  return (
    <div className="flex justify-end gap-2 mt-6">
      {onCancel && (
        <Button type="button" variant="outline" onClick={handleCancel} disabled={isSubmitting || isLoading}>
          {cancelText}
        </Button>
      )}
      <Button type="submit" disabled={isSubmitting || isLoading}>
        {isSubmitting || isLoading ? '提交中...' : submitText}
      </Button>
    </div>
  );
}
