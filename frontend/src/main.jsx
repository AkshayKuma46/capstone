import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { ClerkProvider } from '@clerk/clerk-react'

// Import Clerk publishable key
const PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY || import.meta.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;

if (!PUBLISHABLE_KEY) {
  createRoot(document.getElementById('root')).render(
    <StrictMode>
      <div className="auth-wrapper" style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div className="auth-card" style={{ maxWidth: 520, padding: '40px 32px' }}>
          <div className="auth-logo" style={{ color: 'var(--error)', fontSize: '32px', marginBottom: '16px' }}>⚠️ Setup Required</div>
          <h2 className="auth-title">Missing Clerk Publishable Key</h2>
          <p className="auth-description" style={{ fontSize: '14px', marginBottom: '24px' }}>
            The app requires the <strong>VITE_CLERK_PUBLISHABLE_KEY</strong> variable to initialize Google authentication.
          </p>
          <div style={{
            background: 'var(--warning-bg)',
            border: '1px solid #e8d080',
            padding: '20px',
            borderRadius: '4px',
            fontSize: '13px',
            color: 'var(--warning)',
            textAlign: 'left',
            lineHeight: '1.6',
            width: '100%'
          }}>
            <strong style={{ display: 'block', marginBottom: '8px' }}>How to resolve:</strong>
            <ol style={{ marginLeft: '16px' }}>
              <li style={{ marginBottom: '8px' }}>
                Go to your <strong>Vercel Settings</strong> &rarr; <strong>Environment Variables</strong>.
              </li>
              <li style={{ marginBottom: '8px' }}>
                Add <code>VITE_CLERK_PUBLISHABLE_KEY</code> with your Clerk publishable key.
              </li>
              <li>
                Go to the <strong>Deployments</strong> tab in Vercel, click the three dots on the latest deployment, and choose <strong>Redeploy</strong>.
              </li>
            </ol>
          </div>
        </div>
      </div>
    </StrictMode>
  );
} else {
  createRoot(document.getElementById('root')).render(
    <StrictMode>
      <ClerkProvider publishableKey={PUBLISHABLE_KEY}>
        <App />
      </ClerkProvider>
    </StrictMode>,
  );
}
