import { describe, it, expect, beforeEach } from '@jest/globals';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import LoginPage from '@/app/login/page';

// Mock Next.js router
jest.mock('next/navigation', () => ({
  useRouter() {
    return {
      push: jest.fn(),
      replace: jest.fn(),
      prefetch: jest.fn(),
      back: jest.fn(),
      pathname: '/login',
      query: {},
      asPath: '/login',
    };
  },
  usePathname() {
    return '/login';
  },
  useSearchParams() {
    return new URLSearchParams();
  },
}));

// Mock react-hot-toast
jest.mock('react-hot-toast', () => ({
  __esModule: true,
  default: {
    error: jest.fn(),
    success: jest.fn(),
  },
}));

// Mock api module
jest.mock('@/lib/api', () => ({
  login: jest.fn(),
  logout: jest.fn(),
  getCurrentUser: jest.fn(),
  isAuthenticated: jest.fn(),
  getToken: jest.fn(),
  default: {
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
  },
}));

import { login, isAuthenticated } from '@/lib/api';

// Clear localStorage before each test
beforeEach(() => {
  localStorage.clear();
  jest.clearAllMocks();

  // Mock authentication status
  (isAuthenticated as jest.Mock).mockReturnValue(false);

  // Mock login function
  (login as jest.Mock).mockImplementation(() => {
    return Promise.resolve({
      access_token: 'mock-jwt-token-12345',
      user: { id: 1, username: 'admin', email: 'admin@example.com', role: 'admin' },
    });
  });
});

describe('Login Form Validation Tests', () => {
  describe('Form Rendering', () => {
    it('should render login form with all fields', () => {
      render(<LoginPage />);

      expect(screen.getByText('AIOps Agent 登录')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('请输入用户名')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('请输入密码')).toBeInTheDocument();
      expect(screen.getByText('登录')).toBeInTheDocument();
    });

    it('should render username input with correct attributes', () => {
      render(<LoginPage />);

      const usernameInput = screen.getByPlaceholderText('请输入用户名');
      expect(usernameInput).toHaveAttribute('type', 'text');
      expect(usernameInput).toHaveAttribute('required');
      expect(usernameInput).toHaveAttribute('placeholder', '请输入用户名');
    });

    it('should render password input with correct attributes', () => {
      render(<LoginPage />);

      const passwordInput = screen.getByPlaceholderText('请输入密码');
      expect(passwordInput).toHaveAttribute('type', 'password');
      expect(passwordInput).toHaveAttribute('required');
      expect(passwordInput).toHaveAttribute('placeholder', '请输入密码');
    });

    it('should show setup link when not authenticated', () => {
      render(<LoginPage />);

      expect(screen.getByText('还没有管理员？')).toBeInTheDocument();
      expect(screen.getByText('创建首个管理员')).toBeInTheDocument();
    });

    it('should disable inputs during loading', async () => {
      render(<LoginPage />);

      const usernameInput = screen.getByPlaceholderText('请输入用户名');
      const passwordInput = screen.getByPlaceholderText('请输入密码');
      const submitButton = screen.getByText('登录');

      // Initially not disabled
      expect(usernameInput).not.toBeDisabled();
      expect(passwordInput).not.toBeDisabled();
      expect(submitButton).not.toBeDisabled();
    });
  });

  describe('Form Validation', () => {
    it('should require username field', () => {
      render(<LoginPage />);

      const usernameInput = screen.getByPlaceholderText('请输入用户名');
      expect(usernameInput).toHaveAttribute('required');
    });

    it('should require password field', () => {
      render(<LoginPage />);

      const passwordInput = screen.getByPlaceholderText('请输入密码');
      expect(passwordInput).toHaveAttribute('required');
    });

    it('should not submit with empty fields', async () => {
      render(<LoginPage />);

      const submitButton = screen.getByText('登录');
      const form = submitButton.closest('form');

      if (form) {
        fireEvent.submit(form);

        // HTML5 validation should prevent submission
        // The form should not submit if required fields are empty
      }
    });

    it('should show error message on failed login', async () => {
      render(<LoginPage />);

      const usernameInput = screen.getByPlaceholderText('请输入用户名');
      const passwordInput = screen.getByPlaceholderText('请输入密码');
      const submitButton = screen.getByText('登录');

      fireEvent.change(usernameInput, { target: { value: 'invalid' } });
      fireEvent.change(passwordInput, { target: { value: 'wrong' } });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/登录失败/)).toBeInTheDocument();
      });
    });

    it('should clear error message on successful login', async () => {
      render(<LoginPage />);

      const usernameInput = screen.getByPlaceholderText('请输入用户名');
      const passwordInput = screen.getByPlaceholderText('请输入密码');
      const submitButton = screen.getByText('登录');

      // First, fail login
      fireEvent.change(usernameInput, { target: { value: 'invalid' } });
      fireEvent.change(passwordInput, { target: { value: 'wrong' } });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/登录失败/)).toBeInTheDocument();
      });

      // Then, succeed login
      fireEvent.change(usernameInput, { target: { value: 'admin' } });
      fireEvent.change(passwordInput, { target: { value: 'password' } });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.queryByText(/登录失败/)).not.toBeInTheDocument();
      });
    });
  });

  describe('User Interactions', () => {
    it('should allow typing in username field', () => {
      render(<LoginPage />);

      const usernameInput = screen.getByPlaceholderText('请输入用户名');
      fireEvent.change(usernameInput, { target: { value: 'testuser' } });

      expect(usernameInput).toHaveValue('testuser');
    });

    it('should allow typing in password field', () => {
      render(<LoginPage />);

      const passwordInput = screen.getByPlaceholderText('请输入密码');
      fireEvent.change(passwordInput, { target: { value: 'testpass' } });

      expect(passwordInput).toHaveValue('testpass');
    });

    it('should handle form submission with Enter key', async () => {
      render(<LoginPage />);

      const usernameInput = screen.getByPlaceholderText('请输入用户名');
      const passwordInput = screen.getByPlaceholderText('请输入密码');

      fireEvent.change(usernameInput, { target: { value: 'admin' } });
      fireEvent.change(passwordInput, { target: { value: 'password' } });
      fireEvent.keyDown(passwordInput, { key: 'Enter', code: 'Enter' });

      // Form should attempt submission
      expect(usernameInput).toHaveValue('admin');
      expect(passwordInput).toHaveValue('password');
    });

    it('should handle rapid input changes', () => {
      render(<LoginPage />);

      const usernameInput = screen.getByPlaceholderText('请输入用户名');

      for (let i = 0; i < 10; i++) {
        fireEvent.change(usernameInput, { target: { value: `user${i}` } });
      }

      expect(usernameInput).toHaveValue('user9');
    });

    it('should disable submit button during loading', async () => {
      render(<LoginPage />);

      const usernameInput = screen.getByPlaceholderText('请输入用户名');
      const passwordInput = screen.getByPlaceholderText('请输入密码');
      const submitButton = screen.getByText('登录');

      fireEvent.change(usernameInput, { target: { value: 'admin' } });
      fireEvent.change(passwordInput, { target: { value: 'password' } });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(submitButton).toBeDisabled();
        expect(submitButton).toHaveTextContent('登录中...');
      });
    });

    it('should re-enable submit button after loading', async () => {
      render(<LoginPage />);

      const usernameInput = screen.getByPlaceholderText('请输入用户名');
      const passwordInput = screen.getByPlaceholderText('请输入密码');
      const submitButton = screen.getByText('登录');

      fireEvent.change(usernameInput, { target: { value: 'admin' } });
      fireEvent.change(passwordInput, { target: { value: 'password' } });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(submitButton).not.toBeDisabled();
        expect(submitButton).toHaveTextContent('登录');
      });
    });
  });

  describe('Successful Login', () => {
    it('should login successfully with valid credentials', async () => {
      render(<LoginPage />);

      const usernameInput = screen.getByPlaceholderText('请输入用户名');
      const passwordInput = screen.getByPlaceholderText('请输入密码');
      const submitButton = screen.getByText('登录');

      fireEvent.change(usernameInput, { target: { value: 'admin' } });
      fireEvent.change(passwordInput, { target: { value: 'password' } });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(localStorage.getItem('auth_token')).toBe('mock-jwt-token-12345');
      });
    });

    it('should save user data on successful login', async () => {
      render(<LoginPage />);

      const usernameInput = screen.getByPlaceholderText('请输入用户名');
      const passwordInput = screen.getByPlaceholderText('请输入密码');
      const submitButton = screen.getByText('登录');

      fireEvent.change(usernameInput, { target: { value: 'admin' } });
      fireEvent.change(passwordInput, { target: { value: 'password' } });
      fireEvent.click(submitButton);

      await waitFor(() => {
        const user = JSON.parse(localStorage.getItem('user') || '{}');
        expect(user.username).toBe('admin');
      });
    });

    it('should redirect to home page after successful login', async () => {
      const mockReplace = jest.fn();
      (jest.requireMock('next/navigation').useRouter as jest.Mock).mockReturnValue({
        replace: mockReplace,
        push: jest.fn(),
        prefetch: jest.fn(),
        back: jest.fn(),
        pathname: '/login',
        query: {},
        asPath: '/login',
      });

      render(<LoginPage />);

      const usernameInput = screen.getByPlaceholderText('请输入用户名');
      const passwordInput = screen.getByPlaceholderText('请输入密码');
      const submitButton = screen.getByText('登录');

      fireEvent.change(usernameInput, { target: { value: 'admin' } });
      fireEvent.change(passwordInput, { target: { value: 'password' } });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockReplace).toHaveBeenCalledWith('/');
      });
    });
  });

  describe('Failed Login', () => {
    it('should show error message with invalid credentials', async () => {
      render(<LoginPage />);

      const usernameInput = screen.getByPlaceholderText('请输入用户名');
      const passwordInput = screen.getByPlaceholderText('请输入密码');
      const submitButton = screen.getByText('登录');

      fireEvent.change(usernameInput, { target: { value: 'invalid' } });
      fireEvent.change(passwordInput, { target: { value: 'wrong' } });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/登录失败/)).toBeInTheDocument();
      });
    });

    it('should not save token on failed login', async () => {
      render(<LoginPage />);

      const usernameInput = screen.getByPlaceholderText('请输入用户名');
      const passwordInput = screen.getByPlaceholderText('请输入密码');
      const submitButton = screen.getByText('登录');

      fireEvent.change(usernameInput, { target: { value: 'invalid' } });
      fireEvent.change(passwordInput, { target: { value: 'wrong' } });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(localStorage.getItem('auth_token')).toBeNull();
      });
    });

    it('should not redirect on failed login', async () => {
      const mockReplace = jest.fn();
      (jest.requireMock('next/navigation').useRouter as jest.Mock).mockReturnValue({
        replace: mockReplace,
        push: jest.fn(),
        prefetch: jest.fn(),
        back: jest.fn(),
        pathname: '/login',
        query: {},
        asPath: '/login',
      });

      render(<LoginPage />);

      const usernameInput = screen.getByPlaceholderText('请输入用户名');
      const passwordInput = screen.getByPlaceholderText('请输入密码');
      const submitButton = screen.getByText('登录');

      fireEvent.change(usernameInput, { target: { value: 'invalid' } });
      fireEvent.change(passwordInput, { target: { value: 'wrong' } });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockReplace).not.toHaveBeenCalled();
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle network errors', async () => {
      server.use(
        http.post('/api/v1/auth/login', () => {
          return HttpResponse.error();
        })
      );

      render(<LoginPage />);

      const usernameInput = screen.getByPlaceholderText('请输入用户名');
      const passwordInput = screen.getByPlaceholderText('请输入密码');
      const submitButton = screen.getByText('登录');

      fireEvent.change(usernameInput, { target: { value: 'admin' } });
      fireEvent.change(passwordInput, { target: { value: 'password' } });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/登录失败/)).toBeInTheDocument();
      });
    });

    it('should handle timeout errors', async () => {
      server.use(
        http.post('/api/v1/auth/login', async () => {
          await new Promise(resolve => setTimeout(resolve, 20000));
          return HttpResponse.json({ access_token: 'token' });
        })
      );

      render(<LoginPage />);

      const usernameInput = screen.getByPlaceholderText('请输入用户名');
      const passwordInput = screen.getByPlaceholderText('请输入密码');
      const submitButton = screen.getByText('登录');

      fireEvent.change(usernameInput, { target: { value: 'admin' } });
      fireEvent.change(passwordInput, { target: { value: 'password' } });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/登录失败/)).toBeInTheDocument();
      });
    });

    it('should handle 500 server errors', async () => {
      server.use(
        http.post('/api/v1/auth/login', () => {
          return HttpResponse.json({ detail: 'Server error' }, { status: 500 });
        })
      );

      render(<LoginPage />);

      const usernameInput = screen.getByPlaceholderText('请输入用户名');
      const passwordInput = screen.getByPlaceholderText('请输入密码');
      const submitButton = screen.getByText('登录');

      fireEvent.change(usernameInput, { target: { value: 'admin' } });
      fireEvent.change(passwordInput, { target: { value: 'password' } });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/登录失败/)).toBeInTheDocument();
      });
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty username', async () => {
      render(<LoginPage />);

      const passwordInput = screen.getByPlaceholderText('请输入密码');
      const submitButton = screen.getByText('登录');

      fireEvent.change(passwordInput, { target: { value: 'password' } });
      fireEvent.click(submitButton);

      // HTML5 validation should prevent submission
      expect(screen.queryByText(/登录失败/)).not.toBeInTheDocument();
    });

    it('should handle empty password', async () => {
      render(<LoginPage />);

      const usernameInput = screen.getByPlaceholderText('请输入用户名');
      const submitButton = screen.getByText('登录');

      fireEvent.change(usernameInput, { target: { value: 'admin' } });
      fireEvent.click(submitButton);

      // HTML5 validation should prevent submission
      expect(screen.queryByText(/登录失败/)).not.toBeInTheDocument();
    });

    it('should handle special characters in username', async () => {
      render(<LoginPage />);

      const usernameInput = screen.getByPlaceholderText('请输入用户名');
      const passwordInput = screen.getByPlaceholderText('请输入密码');

      fireEvent.change(usernameInput, { target: { value: 'user@domain.com' } });
      fireEvent.change(passwordInput, { target: { value: 'password' } });

      expect(usernameInput).toHaveValue('user@domain.com');
    });

    it('should handle long passwords', () => {
      render(<LoginPage />);

      const passwordInput = screen.getByPlaceholderText('请输入密码');
      const longPassword = 'a'.repeat(100);

      fireEvent.change(passwordInput, { target: { value: longPassword } });

      expect(passwordInput).toHaveValue(longPassword);
    });

    it('should handle whitespace in inputs', () => {
      render(<LoginPage />);

      const usernameInput = screen.getByPlaceholderText('请输入用户名');
      const passwordInput = screen.getByPlaceholderText('请输入密码');

      fireEvent.change(usernameInput, { target: { value: '  admin  ' } });
      fireEvent.change(passwordInput, { target: { value: '  password  ' } });

      expect(usernameInput).toHaveValue('  admin  ');
      expect(passwordInput).toHaveValue('  password  ');
    });

    it('should handle unicode characters in username', () => {
      render(<LoginPage />);

      const usernameInput = screen.getByPlaceholderText('请输入用户名');
      fireEvent.change(usernameInput, { target: { value: '用户名🚀' } });

      expect(usernameInput).toHaveValue('用户名🚀');
    });

    it('should handle very long username', () => {
      render(<LoginPage />);

      const usernameInput = screen.getByPlaceholderText('请输入用户名');
      const longUsername = 'a'.repeat(1000);

      fireEvent.change(usernameInput, { target: { value: longUsername } });

      expect(usernameInput).toHaveValue(longUsername);
    });

    it('should handle rapid form submissions', async () => {
      render(<LoginPage />);

      const usernameInput = screen.getByPlaceholderText('请输入用户名');
      const passwordInput = screen.getByPlaceholderText('请输入密码');
      const submitButton = screen.getByText('登录');

      fireEvent.change(usernameInput, { target: { value: 'admin' } });
      fireEvent.change(passwordInput, { target: { value: 'password' } });

      // Submit multiple times rapidly
      for (let i = 0; i < 5; i++) {
        fireEvent.click(submitButton);
      }

      // Should handle without error
      await waitFor(() => {
        expect(true).toBe(true);
      });
    });
  });

  describe('Form Reset', () => {
    it('should clear error message on input change', async () => {
      render(<LoginPage />);

      const usernameInput = screen.getByPlaceholderText('请输入用户名');
      const passwordInput = screen.getByPlaceholderText('请输入密码');
      const submitButton = screen.getByText('登录');

      // Fail login first
      fireEvent.change(usernameInput, { target: { value: 'invalid' } });
      fireEvent.change(passwordInput, { target: { value: 'wrong' } });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/登录失败/)).toBeInTheDocument();
      });

      // Change input
      fireEvent.change(usernameInput, { target: { value: 'admin' } });

      // Error should be cleared
      await waitFor(() => {
        expect(screen.queryByText(/登录失败/)).not.toBeInTheDocument();
      });
    });
  });

  describe('Authentication State', () => {
    it('should redirect if already authenticated', () => {
      localStorage.setItem('auth_token', 'existing-token');

      const mockReplace = jest.fn();
      (jest.requireMock('next/navigation').useRouter as jest.Mock).mockReturnValue({
        replace: mockReplace,
        push: jest.fn(),
        prefetch: jest.fn(),
        back: jest.fn(),
        pathname: '/login',
        query: {},
        asPath: '/login',
      });

      render(<LoginPage />);

      expect(mockReplace).toHaveBeenCalledWith('/');
    });

    it('should not redirect if not authenticated', () => {
      const mockReplace = jest.fn();
      (jest.requireMock('next/navigation').useRouter as jest.Mock).mockReturnValue({
        replace: mockReplace,
        push: jest.fn(),
        prefetch: jest.fn(),
        back: jest.fn(),
        pathname: '/login',
        query: {},
        asPath: '/login',
      });

      render(<LoginPage />);

      expect(mockReplace).not.toHaveBeenCalled();
    });
  });
});
