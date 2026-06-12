import { useState } from 'react';
import { useWardrobe } from '../context/WardrobeContext';
import GarmentColorBlock from '../components/GarmentColorBlock';
import { COLOR_MAP } from '../data/mockData';
import Header from '../components/Header';

const CATEGORY_OPTIONS = ['All', 'top', 'bottom', 'outerwear', 'footwear', 'accessory', 'full_outfit'];
const COLOR_OPTIONS = ['All', ...Object.keys(COLOR_MAP)];
const OCCASION_OPTIONS = ['All', 'casual', 'business casual', 'formal', 'outdoor', 'sport', 'date night', 'travel', 'wedding', 'festival', 'party'];

export default function WardrobePage({ page, setPage, setSelectedGarmentId }) {
  const { garments, seedWardrobe } = useWardrobe();
  const [seeding, setSeeding] = useState(false);

  async function handleSeed() {
    setSeeding(true);
    await seedWardrobe();
    setSeeding(false);
  }
  const [filterCategory, setFilterCategory] = useState('All');
  const [filterColor, setFilterColor] = useState('All');
  const [filterOccasion, setFilterOccasion] = useState('All');

  const hasFilters = filterCategory !== 'All' || filterColor !== 'All' || filterOccasion !== 'All';

  const filtered = garments.filter(g => {
    if (filterCategory !== 'All' && g.category !== filterCategory) return false;
    if (filterColor !== 'All' && g.primaryColor !== filterColor) return false;
    if (filterOccasion !== 'All' && !g.occasionTags.includes(filterOccasion)) return false;
    return true;
  });

  function clearFilters() {
    setFilterCategory('All');
    setFilterColor('All');
    setFilterOccasion('All');
  }

  return (
    <>
      <Header setPage={setPage} />

      <div className="page">
        {/* Filter bar */}
        <div className="filter-bar">
          <select
            className={`filter-select ${filterCategory !== 'All' ? 'active' : ''}`}
            value={filterCategory}
            onChange={e => setFilterCategory(e.target.value)}
            aria-label="Filter by category"
          >
            {CATEGORY_OPTIONS.map(o => (
              <option key={o} value={o}>{o === 'All' ? 'Category' : capitalize(o)}</option>
            ))}
          </select>

          <select
            className={`filter-select ${filterColor !== 'All' ? 'active' : ''}`}
            value={filterColor}
            onChange={e => setFilterColor(e.target.value)}
            aria-label="Filter by color"
          >
            {COLOR_OPTIONS.map(o => (
              <option key={o} value={o}>{o === 'All' ? 'Color' : capitalize(o)}</option>
            ))}
          </select>

          <select
            className={`filter-select ${filterOccasion !== 'All' ? 'active' : ''}`}
            value={filterOccasion}
            onChange={e => setFilterOccasion(e.target.value)}
            aria-label="Filter by occasion"
          >
            {OCCASION_OPTIONS.map(o => (
              <option key={o} value={o}>{o === 'All' ? 'Occasion' : capitalize(o)}</option>
            ))}
          </select>

          {hasFilters && (
            <button className="clear-filters" onClick={clearFilters}>Clear</button>
          )}
        </div>

        {/* Grid or empty state */}
        {garments.length === 0 ? (
          <div className="empty-state">
            <span className="empty-icon">👔</span>
            <h3>Your wardrobe is empty</h3>
            <p>Upload your first garment or load a sample collection to get started</p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 8 }}>
              <button className="btn-primary" onClick={() => setPage('upload')}>
                Upload a Garment
              </button>
              <button className="btn-secondary" onClick={handleSeed} disabled={seeding}>
                {seeding ? 'Loading Sample...' : 'Load Sample Wardrobe'}
              </button>
            </div>
          </div>
        ) : filtered.length === 0 ? (
          <div className="empty-state">
            <span className="empty-icon">🔍</span>
            <h3>No matches</h3>
            <p>No garments match your current filters</p>
            <button className="btn-ghost" onClick={clearFilters}>Clear filters</button>
          </div>
        ) : (
          <div className="garment-grid">
            {filtered.map(garment => (
              <GarmentCard
                key={garment.garmentId}
                garment={garment}
                onClick={() => { setSelectedGarmentId(garment.garmentId); setPage('garment-detail'); }}
              />
            ))}
          </div>
        )}
      </div>
    </>
  );
}

function GarmentCard({ garment, onClick }) {
  const hex = COLOR_MAP[garment.primaryColor?.toLowerCase()] || '#444466';

  return (
    <div className="garment-card" onClick={onClick} role="button" tabIndex={0}
      onKeyDown={e => e.key === 'Enter' && onClick()}
      aria-label={`View ${garment.name}`}
    >
      {garment.imageUrl ? (
        <img src={garment.imageUrl} alt={garment.name} className="garment-image" />
      ) : (
        <GarmentColorBlock color={garment.primaryColor} className="garment-color-block" />
      )}
      <div className="garment-info">
        <div className="garment-name" title={garment.name}>{garment.name}</div>
        <div className="garment-category">{capitalize(garment.category)}</div>
        <div className="garment-color-label">
          <span className="color-dot" style={{ background: hex }} />
          {capitalize(garment.primaryColor)}
        </div>
      </div>
    </div>
  );
}

function capitalize(str) {
  if (!str) return '';
  return str.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}
