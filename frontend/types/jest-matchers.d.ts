// Global jest matcher augmentations.
// This file is an external module (it imports), which is required for
// `declare global` to be valid. It pulls in the @testing-library/jest-dom
// matcher types and declares the jest-axe matcher.
import '@testing-library/jest-dom';
import type { AxeResults } from 'jest-axe';

declare global {
  namespace jest {
    interface Matchers<R, T = {}> {
      /** Assert that axe-core found no accessibility violations. */
      toHaveNoViolations(): R;
    }
  }
}

export {};
