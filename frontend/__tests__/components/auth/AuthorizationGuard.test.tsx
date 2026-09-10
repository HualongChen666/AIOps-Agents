import React from 'react';
import { render, screen } from '@testing-library/react';
import { AuthorizationGuard } from '@/components/auth/AuthorizationGuard';
import { useAuthStore } from '@/store/auth';

jest.mock('next/navigation', () => {
  const push = jest.fn();
  const router = {
    push,
    replace: jest.fn(),
    prefetch: jest.fn(),
    back: jest.fn(),
    pathname: '/secure',
    query: {},
    asPath: '/secure',
  };
  return {
    useRouter: jest.fn(() => router),
    usePathname: jest.fn(() => '/secure'),
    useSearchParams: jest.fn(() => new URLSearchParams()),
    __router: router,
  };
});

const nav = jest.requireMock('next/navigation') as { __router: { push: jest.Mock } };
const pushMock = nav.__router.push;

const setUser = (user: null | Record<string, unknown>) =>
  useAuthStore.setState({ user: user as never, isAuthenticated: !!user });

describe('AuthorizationGuard', () => {
  beforeEach(() => {
    localStorage.clear();
    pushMock.mockClear();
    useAuthStore.setState({ user: null, isAuthenticated: false });
  });

  it('redirects to /login and shows a login prompt when unauthenticated', () => {
    render(
      <AuthorizationGuard>
        <div>secret content</div>
      </AuthorizationGuard>
    );

    expect(screen.getByText('需要登录')).toBeInTheDocument();
    expect(screen.queryByText('secret content')).not.toBeInTheDocument();
    expect(pushMock).toHaveBeenCalledWith('/login');
  });

  it('renders children for an authenticated user with no requirements', () => {
    setUser({ id: '1', username: 'u', email: 'u@x.io', role: 'viewer', permissions: [] });
    render(
      <AuthorizationGuard>
        <div>secret content</div>
      </AuthorizationGuard>
    );

    expect(screen.getByText('secret content')).toBeInTheDocument();
    expect(pushMock).not.toHaveBeenCalled();
  });

  describe('role requirements', () => {
    it('denies access when the role is missing and shows the required role', () => {
      setUser({ id: '1', username: 'u', email: 'u@x.io', role: 'viewer', permissions: [] });
      render(
        <AuthorizationGuard requiredRole="admin">
          <div>admin area</div>
        </AuthorizationGuard>
      );

      expect(screen.getByText('权限不足')).toBeInTheDocument();
      expect(screen.getByText(/您需要 admin 角色才能访问此页面/)).toBeInTheDocument();
      expect(screen.queryByText('admin area')).not.toBeInTheDocument();
    });

    it('renders the fallback instead of the denial card when provided', () => {
      setUser({ id: '1', username: 'u', email: 'u@x.io', role: 'viewer', permissions: [] });
      render(
        <AuthorizationGuard requiredRole="admin" fallback={<div>no access here</div>}>
          <div>admin area</div>
        </AuthorizationGuard>
      );

      expect(screen.getByText('no access here')).toBeInTheDocument();
      expect(screen.queryByText('权限不足')).not.toBeInTheDocument();
    });

    it('grants access when the user holds the required role', () => {
      setUser({ id: '1', username: 'a', email: 'a@x.io', role: 'admin', permissions: [] });
      render(
        <AuthorizationGuard requiredRole="admin">
          <div>admin area</div>
        </AuthorizationGuard>
      );

      expect(screen.getByText('admin area')).toBeInTheDocument();
    });
  });

  describe('permission requirements', () => {
    it('denies access when the permission is missing and shows the required permission', () => {
      setUser({ id: '2', username: 'u', email: 'u@x.io', role: 'user', permissions: ['read'] });
      render(
        <AuthorizationGuard requiredPermission="alerts:write">
          <div>write area</div>
        </AuthorizationGuard>
      );

      expect(screen.getByText('权限不足')).toBeInTheDocument();
      expect(screen.getByText(/您需要 alerts:write 权限才能访问此页面/)).toBeInTheDocument();
    });

    it('honors the fallback for a missing permission', () => {
      setUser({ id: '2', username: 'u', email: 'u@x.io', role: 'user', permissions: [] });
      render(
        <AuthorizationGuard requiredPermission="x" fallback={<div>fallback</div>}>
          <div>protected</div>
        </AuthorizationGuard>
      );
      expect(screen.getByText('fallback')).toBeInTheDocument();
    });

    it('grants access when the permission is held', () => {
      setUser({ id: '2', username: 'u', email: 'u@x.io', role: 'user', permissions: ['alerts:write'] });
      render(
        <AuthorizationGuard requiredPermission="alerts:write">
          <div>write area</div>
        </AuthorizationGuard>
      );
      expect(screen.getByText('write area')).toBeInTheDocument();
    });

    it('lets admins bypass an explicit permission check', () => {
      setUser({ id: '3', username: 'a', email: 'a@x.io', role: 'admin', permissions: [] });
      render(
        <AuthorizationGuard requiredPermission="something:rare">
          <div>admin only</div>
        </AuthorizationGuard>
      );
      expect(screen.getByText('admin only')).toBeInTheDocument();
    });
  });
});
