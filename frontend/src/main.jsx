import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { ClerkProvider } from '@clerk/clerk-react'

// Import Clerk publishable key with a placeholder fallback
const PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

if (!PUBLISHABLE_KEY) {
  console.warn("Warning: VITE_CLERK_PUBLISHABLE_KEY is missing. Please set it in your environment or Vercel dashboard.");
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ClerkProvider publishableKey={PUBLISHABLE_KEY || "pk_test_cGxlYXNlLXNldC12aXRlLWNsZXJrLXB1Ymxpc2hhYmxlLWtleS5jbGVyay5hY2NvdW50cy5kZXYk"}>
      <App />
    </ClerkProvider>
  </StrictMode>,
)
