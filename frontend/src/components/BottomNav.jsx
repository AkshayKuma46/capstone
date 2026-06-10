export default function BottomNav({ page, setPage }) {
  const tabs = [
    {
      id: 'wardrobe',
      label: 'Wardrobe',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M3 22h18M5 22V6a2 2 0 012-2h10a2 2 0 012 2v16M9 4v18M15 4v18M12 11h.01M12 13h.01" />
        </svg>
      ),
    },
    {
      id: 'upload',
      label: 'Upload',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M12 5v14M5 12h14" />
        </svg>
      ),
    },
    {
      id: 'recommend',
      label: 'Recommend',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
        </svg>
      ),
    },
    {
      id: 'collections',
      label: 'Lookbook',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M4 19.5A2.5 2.5 0 016.5 17H20M4 19.5A2.5 2.5 0 006.5 22H20M4 19.5V5A2.5 2.5 0 016.5 2.5H20v14.5" />
        </svg>
      ),
    },
  ];

  return (
    <nav className="bottom-nav">
      {tabs.map(tab => (
        <button
          key={tab.id}
          className={`nav-tab ${page === tab.id ? 'active' : ''}`}
          onClick={() => setPage(tab.id)}
          aria-label={tab.label}
          aria-current={page === tab.id ? 'page' : undefined}
        >
          {tab.icon}
          <span>{tab.label}</span>
        </button>
      ))}
    </nav>
  );
}
