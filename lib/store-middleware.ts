// Middleware for zustand store to handle persistence edge cases

export const storageMiddleware = (config: any) => (set: any, get: any, api: any) => {
  // Check if window is defined (SSR safety)
  if (typeof window === 'undefined') {
    return config(set, get, api);
  }

  // Wrap the original config
  const wrappedConfig = config(
    (...args: any[]) => {
      set(...args);
      // You can add side effects here if needed
    },
    get,
    api
  );

  return wrappedConfig;
};

// Helper to safely access localStorage
export const safeLocalStorage = {
  getItem: (key: string): string | null => {
    if (typeof window === 'undefined') return null;
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  },
  setItem: (key: string, value: string): void => {
    if (typeof window === 'undefined') return;
    try {
      localStorage.setItem(key, value);
    } catch {
      // Ignore quota exceeded errors
    }
  },
  removeItem: (key: string): void => {
    if (typeof window === 'undefined') return;
    try {
      localStorage.removeItem(key);
    } catch {
      // Ignore errors
    }
  },
};
