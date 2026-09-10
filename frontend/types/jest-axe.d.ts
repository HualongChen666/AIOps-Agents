// Ambient type declarations for `jest-axe` (v11).
// NOTE: this file must remain a *script* (no top-level import/export) so that
// `declare module 'jest-axe'` is treated as an ambient module declaration.
// Placing it in a module file would turn it into an augmentation of a
// non-existent typed module and TS would still report TS7016.
// The custom matcher is augmented in ./jest-matchers.d.ts.

declare module 'jest-axe' {
  export interface AxeViolation {
    id: string;
    impact?: 'minor' | 'moderate' | 'serious' | 'critical' | null;
    tags: string[];
    description: string;
    help: string;
    helpUrl: string;
    nodes: unknown[];
  }

  export interface AxeResults {
    violations: AxeViolation[];
    passes: unknown[];
    incomplete: unknown[];
    inapplicable: unknown[];
    testEngine: unknown;
    testRunner: unknown;
    testEnvironment: unknown;
    timestamp: string;
    url: string;
  }

  export type AxeOptions = Record<string, unknown>;

  export function axe(html: Element | string, options?: AxeOptions): Promise<AxeResults>;
  export function configureAxe(options?: AxeOptions): typeof axe;
  export const toHaveNoViolations: {
    toHaveNoViolations(results: AxeResults): { pass: boolean; message(): string };
  };

  const _default: typeof axe;
  export default _default;
}
