// Loads @testing-library/jest-dom's matcher typings for BOTH matcher surfaces:
//   - the global `jest.Matchers` (used when tests rely on jest globals), and
//   - the `@jest/expect` Matchers (used when tests import { expect } from '@jest/globals').
// A side-effect import is required (a type-only import would not register the
// `declare global` / `declare module` augmentations).
import '@testing-library/jest-dom';
import '@testing-library/jest-dom/jest-globals';
export {};
