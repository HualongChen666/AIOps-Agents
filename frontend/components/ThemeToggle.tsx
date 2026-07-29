'use client'

import { useTheme } from '@/components/ThemeProvider';

export const ThemeToggle = () => {
  const { theme, toggleTheme } = useTheme();
  return (
    <button
      onClick={toggleTheme}
      className="text-sm px-2 py-1 border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition"
      aria-label="toggle theme"
    >
      {theme === 'dark' ? '☀' : '☾'}
    </button>
  );
};
