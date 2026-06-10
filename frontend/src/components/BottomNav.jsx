export default function BottomNav({ page, setPage }) {
  const tabs = [
    {
      id: 'wardrobe',
      label: 'Wardrobe',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="2" y="3" width="20" height="14" rx="2"/>
          <path d="M8 21h8M12 17v4"/>
        </svg>
      ),
    },
    {
      id: 'recommend',
      label: 'Recommend',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 2l2.4 7.4H22l-6.2 4.5 2.4 7.4L12 17 5.8 21.3l2.4-7.4L2 9.4h7.6z"/>
        </svg>
      ),
    },
    {
      id: 'collections',
      label: 'Collections',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M19 21l-7-4-7 4V5a2 2 0 012-2h10a2 2 0 012 2z"/>
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
          {tab.label}
        </button>
      ))}
    </nav>
  );
}
