import { create } from 'zustand';
import { useEffect } from 'react';

interface PersistConfig<T> {
  name: string;
  storage: 'localStorage' | 'sessionStorage';
}

export function createPersistedStore<T>(
  initialState: T,
  config: PersistConfig<T>
) {
  const { name, storage } = config;

  // Load from storage on initialization
  const loadFromStorage = (): T => {
    if (typeof window === 'undefined') return initialState;
    try {
      const stored = window[storage].getItem(name);
      return stored ? JSON.parse(stored) : initialState;
    } catch (error) {
      console.error(`Failed to load ${name} from ${storage}:`, error);
      return initialState;
    }
  };

  const store = create<T>((set) => ({
    ...initialState,
    ...loadFromStorage(),
  }));

  // Subscribe to store changes and persist
  if (typeof window !== 'undefined') {
    store.subscribe((state) => {
      try {
        window[storage].setItem(name, JSON.stringify(state));
      } catch (error) {
        console.error(`Failed to save ${name} to ${storage}:`, error);
      }
    });
  }

  return store;
}