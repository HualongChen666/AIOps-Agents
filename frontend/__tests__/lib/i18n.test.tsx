import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {
  LocaleProvider,
  useLocale,
  useI18n,
  translate,
  DEFAULT_LOCALE,
  SUPPORTED_LOCALES,
  type Locale,
} from '@/lib/i18n';

function Consumer() {
  const { locale, setLocale, t } = useLocale();
  const tHook = useI18n();
  return (
    <div>
      <span data-testid="locale">{locale}</span>
      <span data-testid="t">{t('app.subtitle')}</span>
      <span data-testid="tHook">{tHook('app.subtitle')}</span>
      <span data-testid="missing">{t('does.not.exist')}</span>
      <button onClick={() => setLocale('en-US')}>to-en</button>
      <button onClick={() => setLocale('fr-FR' as Locale)}>to-invalid</button>
    </div>
  );
}

const renderProvider = () =>
  render(
    <LocaleProvider>
      <Consumer />
    </LocaleProvider>
  );

describe('lib/i18n', () => {
  beforeEach(() => {
    localStorage.clear();
    document.cookie = 'locale=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/';
    document.documentElement.lang = '';
  });

  describe('constants', () => {
    it('exposes the default and supported locales', () => {
      expect(DEFAULT_LOCALE).toBe('zh-CN');
      expect(SUPPORTED_LOCALES).toEqual(['zh-CN', 'en-US']);
    });
  });

  describe('translate', () => {
    it('returns the zh-CN string for a known key', () => {
      expect(translate('zh-CN', 'app.subtitle')).toBe('统一运维控制台');
    });

    it('returns the en-US string for a known key', () => {
      expect(translate('en-US', 'app.subtitle')).toBe('Unified Ops Console');
    });

    it('falls back to the key itself for an unknown key', () => {
      expect(translate('zh-CN', 'missing.key')).toBe('missing.key');
      expect(translate('en-US', 'missing.key')).toBe('missing.key');
    });
  });

  describe('useLocale without a provider', () => {
    it('returns the default context values', () => {
      function Bare() {
        const { locale, t } = useLocale();
        return (
          <div>
            <span data-testid="locale">{locale}</span>
            <span data-testid="t">{t('app.name')}</span>
          </div>
        );
      }
      render(<Bare />);
      expect(screen.getByTestId('locale')).toHaveTextContent('zh-CN');
      expect(screen.getByTestId('t')).toHaveTextContent('app.name');
    });
  });

  describe('LocaleProvider', () => {
    it('defaults to zh-CN when nothing is stored', () => {
      renderProvider();
      expect(screen.getByTestId('locale')).toHaveTextContent('zh-CN');
      expect(screen.getByTestId('t')).toHaveTextContent('统一运维控制台');
    });

    it('restores a supported locale from localStorage on mount', async () => {
      localStorage.setItem('locale', 'en-US');
      renderProvider();
      await waitFor(() =>
        expect(screen.getByTestId('locale')).toHaveTextContent('en-US')
      );
      expect(screen.getByTestId('t')).toHaveTextContent('Unified Ops Console');
    });

    it('restores a supported locale from a cookie when localStorage is empty', async () => {
      document.cookie = 'locale=en-US; path=/';
      renderProvider();
      await waitFor(() =>
        expect(screen.getByTestId('locale')).toHaveTextContent('en-US')
      );
    });

    it('ignores a stored locale that is not supported', async () => {
      localStorage.setItem('locale', 'fr-FR');
      renderProvider();
      await waitFor(() => expect(localStorage.getItem('locale')).toBe('fr-FR'));
      expect(screen.getByTestId('locale')).toHaveTextContent('zh-CN');
    });

    it('switches locale, persists it and updates document.lang', async () => {
      const user = userEvent.setup();
      renderProvider();

      await user.click(screen.getByText('to-en'));

      expect(screen.getByTestId('locale')).toHaveTextContent('en-US');
      expect(screen.getByTestId('t')).toHaveTextContent('Unified Ops Console');
      expect(localStorage.getItem('locale')).toBe('en-US');
      expect(document.cookie).toContain('locale=en-US');
      await waitFor(() => expect(document.documentElement.lang).toBe('en-US'));
    });

    it('ignores a setLocale call with an unsupported locale', async () => {
      const user = userEvent.setup();
      renderProvider();

      await user.click(screen.getByText('to-invalid'));

      expect(screen.getByTestId('locale')).toHaveTextContent('zh-CN');
      expect(localStorage.getItem('locale')).toBeNull();
    });

    it('useI18n returns the same t as useLocale', () => {
      renderProvider();
      expect(screen.getByTestId('tHook').textContent).toBe(
        screen.getByTestId('t').textContent
      );
    });

    it('renders an unknown key verbatim through the provider t()', () => {
      renderProvider();
      expect(screen.getByTestId('missing')).toHaveTextContent('does.not.exist');
    });

    it('sets document.lang to the active locale on mount', async () => {
      renderProvider();
      await waitFor(() => expect(document.documentElement.lang).toBe('zh-CN'));
    });
  });
});
