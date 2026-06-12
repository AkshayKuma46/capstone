import { UserButton } from '@clerk/clerk-react';

export default function Header({ setPage }) {
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
      </div>
    </header>
  );
}
