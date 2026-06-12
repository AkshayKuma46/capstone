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
        <UserButton />
      </div>
    </header>
  );
}
