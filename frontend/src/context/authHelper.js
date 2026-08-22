import * as ClerkReact from '@clerk/clerk-react';

export function useUser() {
  const key = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY || import.meta.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;
  if (!key) {
    return { user: null };
  }
  try {
    return ClerkReact.useUser();
  } catch (e) {
    return { user: null };
  }
}
