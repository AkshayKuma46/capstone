import { UserButton } from '@clerk/clerk-react';

export default function Header({ setPage }) {
  const hasClerk = !!(import.meta.env.VITE_CLERK_PUBLISHABLE_KEY || import.meta.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);

  return (
    <header className="app-header">
      <h1 
        className="header-logo" 
        onClick={() => setPage && setPage('wardrobe')} 
        style={{ cursor: 'pointer' }}
      >
        AI Wardrobe Stylist
      </h1>
      <p className="header-tagline">Curating intelligent style recommendations.</p>
      <div className="header-user-btn">
        {hasClerk ? (
          <UserButton 
            appearance={{
              variables: {
                colorPrimary: '#1e2a38',
                colorBackground: '#ffffff',
                colorText: '#222222',
                colorTextSecondary: '#666666',
                borderRadius: '4px',
                fontFamily: "'Inter', sans-serif",
              },
              elements: {
                userButtonPopoverCard: {
                  border: '1px solid #d9d4cc',
                  boxShadow: '0 4px 16px rgba(30, 42, 56, 0.08)',
                  background: '#ffffff',
                },
                userButtonPopoverFooter: {
                  display: 'none',
                }
              }
            }}
          />
        ) : (
          <div className="mock-user-btn" style={{
            width: 32,
            height: 32,
            borderRadius: '50%',
            background: '#e2dcd0',
            color: '#1e2a38',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '12px',
            fontWeight: 'bold',
            border: '1px solid #d9d4cc'
          }}>
            DU
          </div>
        )}
      </div>
    </header>
  );
}
