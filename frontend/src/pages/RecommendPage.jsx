import { useState } from 'react';
import { useWardrobe } from '../context/WardrobeContext';
import { OCCASIONS, COLOR_MAP } from '../data/mockData';
import GarmentColorBlock from '../components/GarmentColorBlock';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function RecommendPage({ page, setPage }) {
  const { garments, saveOutfitToCollection, showToast } = useWardrobe();
  const [selectedOccasion, setSelectedOccasion] = useState(null);
  const [loading, setLoading] = useState(false);
  const [outfits, setOutfits] = useState([]);
  const [saveModal, setSaveModal] = useState(null); // outfit to save

  async function handleOccasionSelect(occ) {
    if (garments.length === 0) return;
    setSelectedOccasion(occ);
    setLoading(true);
    setOutfits([]);
    try {
      const res = await fetch(`${API_BASE}/recommend`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          userId: 'demo-user',
          occasion: occ.id,
          k: 5
        })
      });
      if (!res.ok) throw new Error('Failed to get recommendations');
      const data = await res.json();
      setOutfits(data.recommendations || []);
    } catch (err) {
      console.error(err);
      showToast('Failed to load recommendations', 'error');
    } finally {
      setLoading(false);
    }
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
      <header className="app-header">
        <h1 className="header-logo" onClick={() => setPage('wardrobe')} style={{ cursor: 'pointer' }}>AI Wardrobe Stylist</h1>
        <p className="header-tagline">Curating intelligent style recommendations.</p>
      </header>

      <div className="page" style={{ paddingTop: 16 }}>
        {/* Occasion grid — visible only when no occasion is selected */}
        {!selectedOccasion && !loading && (
          <>
            <h2 className="section-heading">Today's Recommendations</h2>
            <p className="section-subheading">Select an occasion to consult your stylist</p>
            <div className="occasion-grid">
              {OCCASIONS.map(occ => (
                <button
                  key={occ.id}
                  className="occasion-tile"
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
        {selectedOccasion && !loading && (
          <>
            <div style={{ padding: '4px 16px 8px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <button className="btn-ghost" style={{ fontSize: 13 }} onClick={() => { setOutfits([]); setSelectedOccasion(null); }}>
                ← Select Occasion
              </button>
              {outfits.length > 0 && (
                <button className="btn-ghost" style={{ fontSize: 13 }} onClick={handleRefresh}>
                  Generate Alternatives ↻
                </button>
              )}
            </div>

            {outfits.length > 0 ? (
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
            ) : (
              <div className="empty-state">
                <span className="empty-icon">👗</span>
                <h3>No outfits found for {selectedOccasion.label}</h3>
                <p>Try tagging some garments in your wardrobe as "{selectedOccasion.label}" or upload new ones.</p>
                <button className="btn-primary" onClick={() => setPage('upload')}>
                  Add Garments
                </button>
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

        {/* Stylist Notes */}
        <div className="stylist-notes-section">
          <h4 className="stylist-section-title">Stylist Notes</h4>
          <p className="outfit-explanation">"{outfit.explanation}"</p>
        </div>

        {/* Why it works */}
        <div className="why-it-works-section">
          <h4 className="stylist-section-title">Why It Works</h4>
          <ul className="why-list">
            <li><strong>Color Harmony:</strong> Excellent color coordination between upper and lower garments.</li>
            <li><strong>Proportions:</strong> The silhouette and proportions create a balanced appearance.</li>
            <li><strong>Suitability:</strong> Highly suitable choice for maintaining a refined {outfit.occasion || 'everyday'} style.</li>
          </ul>
        </div>

        {/* Save button */}
        <button className="save-outfit-btn" onClick={onSave} aria-label="Save look to lookbook">
          ♡ Save Look
        </button>
      </div>
    </div>
  );
}

function SaveModal({ outfit, onClose, onSave }) {
  const [name, setName] = useState('');
  const [error, setError] = useState('');

  function handleSave() {
    if (!name.trim()) { setError('Lookbook name is required'); return; }
    if (name.length > 50) { setError('Name must be 50 characters or less'); return; }
    onSave(name.trim());
  }

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-label="Save look">
      <div className="modal">
        <h3>Save to Lookbook</h3>
        <div className="form-group">
          <label className="form-label">Lookbook Name</label>
          <input
            className={`form-input ${error ? 'warn' : ''}`}
            value={name}
            maxLength={50}
            onChange={e => { setName(e.target.value); setError(''); }}
            placeholder="e.g. Weekend Lookbook"
            autoFocus
            aria-label="Lookbook name"
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
