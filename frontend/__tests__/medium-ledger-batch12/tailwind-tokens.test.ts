import fs from 'fs';
import path from 'path';

const root = path.resolve(__dirname, '..', '..');
const loadConfig = () => require(path.join(root, 'tailwind.config.js'));

describe('medium-ledger batch12 — tailwind config & design tokens', () => {
  it('FE-011: the config file loads without a syntax error', () => {
    // Before the fix the file had a duplicate `module.exports` block and threw
    // `SyntaxError: Unexpected token ':'` on require.
    expect(() => loadConfig()).not.toThrow();
    expect(loadConfig()).toBeTruthy();
  });

  it('FE-011: declares the content globs so utilities are generated', () => {
    const config = loadConfig();
    expect(Array.isArray(config.content)).toBe(true);
    expect(config.content).toEqual(
      expect.arrayContaining([
        './app/**/*.{js,ts,jsx,tsx}',
        './components/**/*.{js,ts,jsx,tsx}',
      ])
    );
  });

  it('FE-090: defines the shadcn tokens used by components/ui', () => {
    const colors = loadConfig().theme.extend.colors;
    // bg-primary / border-primary
    expect(colors.primary.DEFAULT).toBeTruthy();
    // bg-secondary
    expect(colors.secondary).toBeTruthy();
    // bg-background / text-foreground
    expect(colors.background).toBe('var(--background)');
    expect(colors.foreground).toBe('var(--foreground)');
    // bg-muted / text-muted-foreground
    expect(colors.muted.DEFAULT).toBe('var(--muted)');
    expect(colors.muted.foreground).toBe('var(--muted-foreground)');
    // ring-ring
    expect(colors.ring).toBe('var(--ring)');
  });

  it('FE-090: declares the backing CSS variables in styles/globals.css', () => {
    const css = fs.readFileSync(path.join(root, 'styles', 'globals.css'), 'utf8');
    for (const variable of [
      '--background',
      '--foreground',
      '--muted',
      '--muted-foreground',
      '--border',
      '--ring',
    ]) {
      expect(css).toContain(`${variable}:`);
    }
  });
});
