# 表单验证优化文档

## 概述

本文档描述了AIOps SRE Agent前端应用的表单验证优化方案，旨在提升用户体验和数据质量。

---

## 优化目标

1. **实时验证**: 在用户输入时进行实时验证
2. **清晰的错误提示**: 提供明确的错误信息和解决建议
3. **智能验证**: 根据上下文提供智能验证规则
4. **友好的用户体验**: 减少用户输入错误，提升表单填写效率
5. **一致性**: 统一全应用的表单验证样式和行为

---

## 验证规则类型

### 1. 基础验证

#### 必填验证
```typescript
interface RequiredRule {
  required: true;
  message?: string;
}

const requiredRule: RequiredRule = {
  required: true,
  message: '此字段为必填项'
};
```

#### 长度验证
```typescript
interface LengthRule {
  minLength?: number;
  maxLength?: number;
  message?: string;
}

const lengthRule: LengthRule = {
  minLength: 8,
  maxLength: 32,
  message: '长度必须在8-32个字符之间'
};
```

#### 格式验证
```typescript
interface PatternRule {
  pattern: RegExp;
  message?: string;
}

const emailRule: PatternRule = {
  pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
  message: '请输入有效的邮箱地址'
};

const phoneRule: PatternRule = {
  pattern: /^1[3-9]\d{9}$/,
  message: '请输入有效的手机号码'
};
```

### 2. 业务验证

#### 用户名验证
```typescript
const usernameRule: ValidationRule = {
  required: true,
  minLength: 3,
  maxLength: 20,
  pattern: /^[a-zA-Z0-9_]+$/,
  message: '用户名只能包含字母、数字和下划线，长度3-20个字符'
};
```

#### 密码验证
```typescript
const passwordRule: ValidationRule = {
  required: true,
  minLength: 8,
  pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/,
  message: '密码必须包含大小写字母、数字和特殊字符，至少8个字符'
};
```

#### URL验证
```typescript
const urlRule: ValidationRule = {
  required: true,
  pattern: /^https?:\/\/.+/,
  message: '请输入有效的URL地址，必须以http://或https://开头'
};
```

### 3. 自定义验证

#### 异步验证
```typescript
interface AsyncValidationRule {
  validate: (value: any) => Promise<boolean | string>;
  message?: string;
}

const uniqueUsernameRule: AsyncValidationRule = {
  validate: async (username: string) => {
    const exists = await checkUsernameExists(username);
    return exists ? '用户名已存在' : true;
  }
};
```

#### 条件验证
```typescript
interface ConditionalRule {
  condition: (values: Record<string, any>) => boolean;
  rule: ValidationRule;
}

const confirmPasswordRule: ConditionalRule = {
  condition: (values) => values.password === values.confirmPassword,
  rule: {
    message: '两次输入的密码不一致'
  }
};
```

---

## 表单验证组件

### 基础组件

#### FormField
```typescript
interface FormFieldProps {
  name: string;
  label: string;
  type?: 'text' | 'email' | 'password' | 'number' | 'tel' | 'url';
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
  rules?: ValidationRule[];
  error?: string;
  value: any;
  onChange: (value: any) => void;
  onBlur?: () => void;
}

export const FormField: React.FC<FormFieldProps> = ({
  name,
  label,
  type = 'text',
  placeholder,
  required = false,
  disabled = false,
  rules = [],
  error,
  value,
  onChange,
  onBlur
}) => {
  const [localError, setLocalError] = useState('');
  const [touched, setTouched] = useState(false);
  
  const validate = (val: any): string => {
    for (const rule of rules) {
      if (rule.required && !val) {
        return rule.message || '此字段为必填项';
      }
      if (rule.minLength && val.length < rule.minLength) {
        return rule.message || `长度不能少于${rule.minLength}个字符`;
      }
      if (rule.maxLength && val.length > rule.maxLength) {
        return rule.message || `长度不能超过${rule.maxLength}个字符`;
      }
      if (rule.pattern && !rule.pattern.test(val)) {
        return rule.message || '格式不正确';
      }
    }
    return '';
  };
  
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    onChange(newValue);
    
    if (touched) {
      setLocalError(validate(newValue));
    }
  };
  
  const handleBlur = () => {
    setTouched(true);
    setLocalError(validate(value));
    onBlur?.();
  };
  
  const displayError = error || localError;
  
  return (
    <div className="mb-4">
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      <input
        type={type}
        name={name}
        value={value}
        onChange={handleChange}
        onBlur={handleBlur}
        placeholder={placeholder}
        disabled={disabled}
        className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
          displayError ? 'border-red-500' : 'border-gray-300'
        } ${disabled ? 'bg-gray-100 cursor-not-allowed' : ''}`}
      />
      {displayError && (
        <p className="mt-1 text-sm text-red-600">{displayError}</p>
      )}
    </div>
  );
};
```

#### FormSelect
```typescript
interface FormSelectProps {
  name: string;
  label: string;
  options: Array<{ value: string; label: string }>;
  required?: boolean;
  disabled?: boolean;
  error?: string;
  value: string;
  onChange: (value: string) => void;
}

export const FormSelect: React.FC<FormSelectProps> = ({
  name,
  label,
  options,
  required = false,
  disabled = false,
  error,
  value,
  onChange
}) => {
  return (
    <div className="mb-4">
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      <select
        name={name}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
          error ? 'border-red-500' : 'border-gray-300'
        } ${disabled ? 'bg-gray-100 cursor-not-allowed' : ''}`}
      >
        <option value="">请选择</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {error && <p className="mt-1 text-sm text-red-600">{error}</p>}
    </div>
  );
};
```

#### FormCheckbox
```typescript
interface FormCheckboxProps {
  name: string;
  label: string;
  required?: boolean;
  disabled?: boolean;
  error?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}

export const FormCheckbox: React.FC<FormCheckboxProps> = ({
  name,
  label,
  required = false,
  disabled = false,
  error,
  checked,
  onChange
}) => {
  return (
    <div className="mb-4">
      <label className="flex items-center">
        <input
          type="checkbox"
          name={name}
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          disabled={disabled}
          className={`w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 ${
            error ? 'border-red-500' : ''
          } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
        />
        <span className="ml-2 text-sm text-gray-700">
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </span>
      </label>
      {error && <p className="mt-1 text-sm text-red-600">{error}</p>}
    </div>
  );
};
```

### 高级组件

#### SmartForm
```typescript
interface SmartFormProps {
  initialValues: Record<string, any>;
  validationRules: Record<string, ValidationRule[]>;
  onSubmit: (values: Record<string, any>) => Promise<void>;
  children: React.ReactNode;
}

export const SmartForm: React.FC<SmartFormProps> = ({
  initialValues,
  validationRules,
  onSubmit,
  children
}) => {
  const [values, setValues] = useState(initialValues);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [submitting, setSubmitting] = useState(false);
  
  const validateField = (name: string, value: any): string => {
    const rules = validationRules[name] || [];
    for (const rule of rules) {
      if (rule.required && !value) {
        return rule.message || '此字段为必填项';
      }
      if (rule.minLength && value.length < rule.minLength) {
        return rule.message || `长度不能少于${rule.minLength}个字符`;
      }
      if (rule.maxLength && value.length > rule.maxLength) {
        return rule.message || `长度不能超过${rule.maxLength}个字符`;
      }
      if (rule.pattern && !rule.pattern.test(value)) {
        return rule.message || '格式不正确';
      }
    }
    return '';
  };
  
  const validateAll = (): boolean => {
    const newErrors: Record<string, string> = {};
    let isValid = true;
    
    for (const [name, value] of Object.entries(values)) {
      const error = validateField(name, value);
      if (error) {
        newErrors[name] = error;
        isValid = false;
      }
    }
    
    setErrors(newErrors);
    return isValid;
  };
  
  const handleChange = (name: string, value: any) => {
    setValues({ ...values, [name]: value });
    
    if (touched[name]) {
      const error = validateField(name, value);
      setErrors({ ...errors, [name]: error });
    }
  };
  
  const handleBlur = (name: string) => {
    setTouched({ ...touched, [name]: true });
    const error = validateField(name, values[name]);
    setErrors({ ...errors, [name]: error });
  };
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // 标记所有字段为已触摸
    const allTouched = Object.keys(values).reduce((acc, key) => {
      acc[key] = true;
      return acc;
    }, {} as Record<string, boolean>);
    setTouched(allTouched);
    
    // 验证所有字段
    if (!validateAll()) {
      return;
    }
    
    setSubmitting(true);
    try {
      await onSubmit(values);
    } finally {
      setSubmitting(false);
    }
  };
  
  return (
    <form onSubmit={handleSubmit}>
      <FormContext.Provider
        value={{
          values,
          errors,
          touched,
          handleChange,
          handleBlur,
          submitting
        }}
      >
        {children}
      </FormContext.Provider>
    </form>
  );
};
```

#### FormWizard
```typescript
interface FormWizardProps {
  steps: Array<{
    title: string;
    component: React.ReactNode;
    validate?: () => boolean;
  }>;
  onComplete: () => void;
}

export const FormWizard: React.FC<FormWizardProps> = ({
  steps,
  onComplete
}) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());
  
  const handleNext = () => {
    const currentStepData = steps[currentStep];
    if (currentStepData.validate) {
      const isValid = currentStepData.validate();
      if (!isValid) return;
    }
    
    setCompletedSteps(new Set([...completedSteps, currentStep]));
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      onComplete();
    }
  };
  
  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };
  
  const handleStepClick = (step: number) => {
    if (completedSteps.has(step) || step < currentStep) {
      setCurrentStep(step);
    }
  };
  
  return (
    <div className="w-full">
      {/* 步骤指示器 */}
      <div className="flex items-center justify-between mb-8">
        {steps.map((step, index) => (
          <div
            key={index}
            className={`flex items-center cursor-pointer ${
              index < steps.length - 1 ? 'flex-1' : ''
            }`}
            onClick={() => handleStepClick(index)}
          >
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                completedSteps.has(index)
                  ? 'bg-green-500 text-white'
                  : index === currentStep
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-200 text-gray-600'
              }`}
            >
              {completedSteps.has(index) ? '✓' : index + 1}
            </div>
            <span className="ml-2 text-sm font-medium">{step.title}</span>
            {index < steps.length - 1 && (
              <div className="flex-1 h-px bg-gray-200 mx-4" />
            )}
          </div>
        ))}
      </div>
      
      {/* 当前步骤内容 */}
      <div className="mb-6">{steps[currentStep].component}</div>
      
      {/* 导航按钮 */}
      <div className="flex justify-between">
        <Button
          variant="outline"
          onClick={handlePrevious}
          disabled={currentStep === 0}
        >
          上一步
        </Button>
        <Button onClick={handleNext}>
          {currentStep === steps.length - 1 ? '完成' : '下一步'}
        </Button>
      </div>
    </div>
  );
};
```

---

## 验证最佳实践

### 1. 实时验证

```typescript
// 实时验证输入
const useRealTimeValidation = (
  value: any,
  rules: ValidationRule[]
): { error: string; isValid: boolean } => {
  const [error, setError] = useState('');
  const [isValid, setIsValid] = useState(true);
  
  useEffect(() => {
    const validationError = validateValue(value, rules);
    setError(validationError);
    setIsValid(!validationError);
  }, [value, rules]);
  
  return { error, isValid };
};
```

### 2. 防抖验证

```typescript
// 防抖验证，避免频繁验证
const useDebouncedValidation = (
  value: any,
  rules: ValidationRule[],
  delay: number = 300
): { error: string; isValid: boolean } => {
  const [error, setError] = useState('');
  const [isValid, setIsValid] = useState(true);
  
  const debouncedValidate = useMemo(
    () => debounce((val: any) => {
      const validationError = validateValue(val, rules);
      setError(validationError);
      setIsValid(!validationError);
    }, delay),
    [rules, delay]
  );
  
  useEffect(() => {
    debouncedValidate(value);
  }, [value, debouncedValidate]);
  
  return { error, isValid };
};
```

### 3. 智能提示

```typescript
// 智能提示用户输入
const useSmartHint = (
  value: any,
  fieldType: string
): string => {
  const hints: Record<string, (val: any) => string> = {
    email: (val) => {
      if (!val) return '请输入邮箱地址';
      if (!val.includes('@')) return '邮箱地址必须包含@符号';
      if (!val.includes('.')) return '邮箱地址必须包含.符号';
      return '';
    },
    password: (val) => {
      if (!val) return '请输入密码';
      if (val.length < 8) return '密码长度至少8个字符';
      if (!/[A-Z]/.test(val)) return '密码必须包含大写字母';
      if (!/[a-z]/.test(val)) return '密码必须包含小写字母';
      if (!/\d/.test(val)) return '密码必须包含数字';
      return '';
    }
  };
  
  return hints[fieldType]?.(value) || '';
};
```

### 4. 条件验证

```typescript
// 条件验证，根据其他字段的值决定验证规则
const useConditionalValidation = (
  values: Record<string, any>,
  fieldName: string
): ValidationRule[] => {
  const getRules = (): ValidationRule[] => {
    const baseRules: ValidationRule[] = [];
    
    // 示例：如果选择了"其他"，则必须填写说明
    if (values.category === 'other' && fieldName === 'otherDescription') {
      baseRules.push({
        required: true,
        message: '选择其他时必须填写说明'
      });
    }
    
    // 示例：如果年龄大于18，则必须填写职业
    if (values.age > 18 && fieldName === 'occupation') {
      baseRules.push({
        required: true,
        message: '成年人必须填写职业'
      });
    }
    
    return baseRules;
  };
  
  return getRules();
};
```

### 5. 异步验证

```typescript
// 异步验证，如检查用户名是否已存在
const useAsyncValidation = (
  value: any,
  validator: (val: any) => Promise<boolean | string>
): { error: string; isValidating: boolean } => {
  const [error, setError] = useState('');
  const [isValidating, setIsValidating] = useState(false);
  
  useEffect(() => {
    if (!value) {
      setError('');
      return;
    }
    
    setIsValidating(true);
    validator(value)
      .then((result) => {
        if (typeof result === 'string') {
          setError(result);
        } else {
          setError('');
        }
      })
      .catch(() => {
        setError('验证失败，请稍后重试');
      })
      .finally(() => {
        setIsValidating(false);
      });
  }, [value, validator]);
  
  return { error, isValidating };
};
```

---

## 表单验证样式

### 错误状态样式

```css
/* 错误状态 */
.form-field-error {
  border-color: var(--error-border);
  background-color: var(--error-bg);
}

.form-field-error:focus {
  border-color: var(--error-icon);
  box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.1);
}

/* 成功状态 */
.form-field-success {
  border-color: var(--success-border);
  background-color: var(--success-bg);
}

.form-field-success:focus {
  border-color: var(--success-icon);
  box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.1);
}

/* 警告状态 */
.form-field-warning {
  border-color: var(--warning-border);
  background-color: var(--warning-bg);
}

.form-field-warning:focus {
  border-color: var(--warning-icon);
  box-shadow: 0 0 0 3px rgba(234, 179, 8, 0.1);
}
```

### 动画效果

```css
/* 错误提示动画 */
@keyframes shake {
  0%, 100% {
    transform: translateX(0);
  }
  10%, 30%, 50%, 70%, 90% {
    transform: translateX(-5px);
  }
  20%, 40%, 60%, 80% {
    transform: translateX(5px);
  }
}

.form-field-shake {
  animation: shake 0.5s ease-in-out;
}

/* 成功标记动画 */
@keyframes checkmark {
  0% {
    stroke-dashoffset: 100;
  }
  100% {
    stroke-dashoffset: 0;
  }
}

.form-success-icon {
  animation: checkmark 0.3s ease-in-out;
}
```

---

## 可访问性

### 1. ARIA属性

```typescript
<input
  aria-invalid={!!error}
  aria-describedby={error ? `${name}-error` : undefined}
  aria-required={required}
/>
{error && (
  <span id={`${name}-error`} role="alert" className="text-red-600">
    {error}
  </span>
)}
```

### 2. 键盘导航

```typescript
// 支持键盘导航和快捷键
const useFormKeyboardNavigation = () => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Enter' && e.ctrlKey) {
        // Ctrl+Enter 提交表单
        e.preventDefault();
        document.querySelector('form')?.requestSubmit();
      }
      if (e.key === 'Escape') {
        // ESC 重置表单
        e.preventDefault();
        document.querySelector('form')?.reset();
      }
    };
    
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);
};
```

### 3. 屏幕阅读器支持

```typescript
// 为屏幕阅读器提供验证状态
<div role="status" aria-live="polite" aria-atomic="true">
  {error && (
    <span className="sr-only">表单验证失败：{error}</span>
  )}
</div>
```

---

## 测试策略

### 1. 单元测试

```typescript
describe('FormField', () => {
  it('should show required error when empty', () => {
    render(<FormField name="test" label="Test" required value="" onChange={() => {}} />);
    fireEvent.blur(screen.getByLabelText('Test'));
    expect(screen.getByText('此字段为必填项')).toBeInTheDocument();
  });
  
  it('should validate email format', () => {
    render(
      <FormField 
        name="email" 
        label="Email" 
        type="email" 
        rules={[emailRule]} 
        value="invalid-email" 
        onChange={() => {}} 
      />
    );
    fireEvent.blur(screen.getByLabelText('Email'));
    expect(screen.getByText('请输入有效的邮箱地址')).toBeInTheDocument();
  });
});
```

### 2. 集成测试

```typescript
describe('SmartForm Integration', () => {
  it('should validate all fields on submit', async () => {
    const mockSubmit = jest.fn();
    render(
      <SmartForm
        initialValues={{ username: '', email: '' }}
        validationRules={{
          username: [requiredRule],
          email: [requiredRule, emailRule]
        }}
        onSubmit={mockSubmit}
      >
        <FormField name="username" label="Username" value="" onChange={() => {}} />
        <FormField name="email" label="Email" value="" onChange={() => {}} />
        <Button type="submit">Submit</Button>
      </SmartForm>
    );
    
    fireEvent.click(screen.getByText('Submit'));
    
    expect(screen.getByText('此字段为必填项')).toBeInTheDocument();
    expect(mockSubmit).not.toHaveBeenCalled();
  });
});
```

### 3. E2E测试

```typescript
test('form validation flow', async ({ page }) => {
  await page.goto('/login');
  
  // 尝试提交空表单
  await page.click('#submit-button');
  
  // 验证错误提示
  await expect(page.locator('.error-message')).toBeVisible();
  
  // 填写有效数据
  await page.fill('#username', 'testuser');
  await page.fill('#password', 'Test@1234');
  
  // 提交表单
  await page.click('#submit-button');
  
  // 验证成功
  await expect(page.locator('.success-message')).toBeVisible();
});
```

---

## 监控和分析

### 1. 验证错误监控

```typescript
const useValidationMonitoring = () => {
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([]);
  
  const logValidationError = (field: string, error: string) => {
    const errorData: ValidationError = {
      field,
      error,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent
    };
    
    setValidationErrors([...validationErrors, errorData]);
    
    // 发送到监控服务
    analytics.track('validation_error', errorData);
  };
  
  return { validationErrors, logValidationError };
};
```

### 2. 表单完成率分析

```typescript
const useFormCompletionRate = () => {
  const [completionRate, setCompletionRate] = useState(0);
  
  const calculateCompletion = (required: string[], filled: string[]) => {
    const rate = (filled.length / required.length) * 100;
    setCompletionRate(rate);
  };
  
  return { completionRate, calculateCompletion };
};
```

---

**文档版本**: 1.0  
**创建日期**: 2026-08-31  
**最后更新**: 2026-08-31  
**维护团队**: AIOps SRE Agent 前端团队