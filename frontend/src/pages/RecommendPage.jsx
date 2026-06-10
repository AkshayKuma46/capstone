import { useState } from 'react';
import { useWardrobe } from '../context/WardrobeContext';
import { OCCASIONS, generateOutfits, COLOR_MAP } from '../data/mockData';
import GarmentColorBlock from '../components/GarmentColorBlock';

export default function RecommendPage({ setPage }) {
  const { garments, saveOutfitToCollection, showToast } = useWardrobe();
  const [selectedOccasion, setSelectedOccasion] = useState(null);
  const [loading, setLoading] = useState(false);
  const [outfits, setOutfits] = useState([]);
  const [saveModal, setSaveModal] = useState(null); // outfit to save

  function handleOccasionSelect(occ) {
    if (garments.length === 0) return;
    setSelectedOccasion(occ);
    setLoading(true);
    setOutfits([]);
    // Simulate scoring delay
    setTimeout(() => {
      const results = generateOutfits(occ.id, garments);
      setOutfits(results);
      setLoading(false);
    }, 1800);
  }

  function handleRefresh() {
    if (selectedOccasion) handleOccasionSelect(selectedOccasion);
  }

  if (garments.length === 0) {
    return (
      <>
        <div className="top-nav">
          <span className="logo">✦ AWS</span>
          <span className="nav-title">Recommendations</span>
          <div style={{ width: 60 }} />
        </div>
        <div className="page">
          <div className="empty-state">
            <span className="empty-icon">✨</span>
            <h3>Add some clothes first</h3>
            <p>Upload garments to your wardrobe to get outfit recommendations.</p>
            <button className="btn-primary" onClick={() => setPage('upload')}>
              Add Garments
            </button>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <div className="top-nav">
        <span className="logo">✦ AWS</span>
        <span className="nav-title">
          {selectedOccasion && !loading ? `Outfits for ${selectedOccasion.label}` : 'Recommendations'}
        </span>
        {selectedOccasion && !loading && outfits.length > 0 ? (
          <button className="nav-action" onClick={handleRefresh} aria-label="Refresh outfits">↻</button>
        ) : (
          <div style={{ width: 60 }} />
        )}
      </div>

      <div className="page" style={{ paddingTop: 16 }}>
        {/* Occasion grid — always visible */}
        {!loading && outfits.length === 0 && (
          <>
            <p style={{ padding: '0 16px 12px', fontSize: 18, fontWeight: 700 }}>What's the occasion?</p>
            <div className="occasion-grid">
              {OCCASIONS.map(occ => (
                <button
                  key={occ.id}
                  className={`occasion-tile ${selectedOccasion?.id === occ.id ? 'selected' : ''}`}
                  onClick={() => handleOccasionSelect(occ)}
                  aria-label={`Select ${occ.label} occasion`}
                >
                  <span className="occasion-emoji">{occ.emoji}</span>
                  <span className="occasion-label">{occ.label}</span>
                </button>
              ))}
            </div>
          </>
        )}

        {/* Loading state */}
        {loading && (
          <div style={{ padding: '48px 16px', textAlign: 'center' }}>
            <div style={{ fontSize: 32, marginBottom: 16 }}>✨</div>
            <p style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>Finding your best outfits...</p>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16 }}>Scoring outfit combinations...</p>
            {/* Skeleton cards */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {[1, 2, 3].map(i => (
                <div key={i} style={{ height: 140, borderRadius: 12 }} className="skeleton" />
              ))}
            </div>
          </div>
        )}

        {/* Results */}
        {!loading && outfits.length > 0 && (
          <>
            <div style={{ padding: '4px 16px 8px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                {outfits.length} outfit{outfits.length !== 1 ? 's' : ''} for <strong style={{ color: 'var(--text)' }}>{selectedOccasion.label}</strong>
              </p>
              <button className="btn-ghost" style={{ fontSize: 13 }} onClick={() => { setOutfits([]); setSelectedOccasion(null); }}>
                ← Back
              </button>
            </div>
            <div className="outfit-cards">
              {outfits.map((outfit, idx) => (
                <OutfitCard
                  key={outfit.outfitId}
                  outfit={outfit}
                  rank={idx + 1}
                  garments={garments}
                  onSave={() => setSaveModal(outfit)}
                />
              ))}
            </div>
            {outfits.length === 0 && (
              <div className="empty-state">
                <span className="empty-icon">👗</span>
                <h3>No outfits found</h3>
                <p>Try adding more garments or selecting a different occasion.</p>
                <button className="btn-primary" onClick={() => setPage('upload')}>Add Garments</button>
              </div>
            )}
          </>
        )}
      </div>

      {saveModal && (
        <SaveModal
          outfit={saveModal}
          onClose={() => setSaveModal(null)}
          onSave={(name) => {
            saveOutfitToCollection(saveModal, name);
            setSaveModal(null);
          }}
        />
      )}
    </>
  );
}

function OutfitCard({ outfit, rank, garments: allGarments, onSave }) {
  const outfitGarments = outfit.garmentIds.map(id => allGarments.find(g => g.garmentId === id)).filter(Boolean);
  const score = outfit.compatibilityScore;
  const isLowConf = outfit.confidenceScore < 0.6;
  const scoreClass = score >= 75 ? 'high' : score >= 50 ? 'mid' : 'low';

  const rankLabel = rank === 1 ? '#1 Best Match' : `#${rank}`;

  return (
    <div className="outfit-card">
      <div className="outfit-card-header">
        <span className="outfit-rank">{rankLabel}</span>
        <span className="outfit-score">{score}/100</span>
      </div>
      <div className="outfit-card-body">
        {isLowConf && (
          <div className="low-confidence-badge" role="status">
            ⚠ Low confidence ({outfit.confidenceScore.toFixed(2)})
          </div>
        )}

        {/* Garment thumbnails */}
        <div className="garment-images-row">
          {outfitGarments.map(g => (
            g.imageUrl ? (
              <img key={g.garmentId} src={g.imageUrl} alt={g.name} className="garment-thumb" />
            ) : (
              <GarmentColorBlock
                key={g.garmentId}
                color={g.primaryColor}
                className="garment-thumb-block"
              />
            )
          ))}
        </div>

        {/* Garment names */}
        <p className="garment-names">
          {outfitGarments.map(g => g.name).join(' · ')}
        </p>

        {/* Score bar */}
        <div className="score-bar-row">
          <div className="score-bar-wrap">
            <div className={`score-bar-fill ${scoreClass}`} style={{ width: `${score}%` }} />
          </div>
          <span className="score-label" style={{ color: scoreClass === 'high' ? 'var(--score-high)' : scoreClass === 'mid' ? 'var(--score-mid)' : 'var(--score-low)' }}>
            {score}%
          </span>
        </div>

        {/* LLM explanation */}
        <p className="outfit-explanation">"{outfit.explanation}"</p>

        {/* Save button */}
        <button className="save-outfit-btn" onClick={onSave} aria-label="Save outfit to collection">
          ♡ Save to Collection
        </button>
      </div>
    </div>
  );
}

function SaveModal({ outfit, onClose, onSave }) {
  const [name, setName] = useState('');
  const [error, setError] = useState('');

  function handleSave() {
    if (!name.trim()) { setError('Collection name is required'); return; }
    if (name.length > 50) { setError('Name must be 50 characters or less'); return; }
    onSave(name.trim());
  }

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-label="Save outfit">
      <div className="modal">
        <h3>Save Outfit</h3>
        <div className="form-group">
          <label className="form-label">Collection name</label>
          <input
            className={`form-input ${error ? 'warn' : ''}`}
            value={name}
            maxLength={50}
            onChange={e => { setName(e.target.value); setError(''); }}
            placeholder="e.g. My Office Looks"
            autoFocus
            aria-label="Collection name"
            onKeyDown={e => e.key === 'Enter' && handleSave()}
          />
          <div className={`char-count ${name.length > 50 ? 'over' : ''}`}>{name.length}/50</div>
          {error && <p className="error-text">{error}</p>}
        </div>
        <div className="modal-actions">
          <button className="btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn-primary" onClick={handleSave}>Save</button>
        </div>
      </div>
    </div>
  );
}
