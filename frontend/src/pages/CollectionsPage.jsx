import { useState } from 'react';
import { useWardrobe } from '../context/WardrobeContext';
import GarmentColorBlock from '../components/GarmentColorBlock';

export default function CollectionsPage({ page, setPage }) {
  const { collections, renameCollection, deleteCollection, garments } = useWardrobe();
  const [selectedCollection, setSelectedCollection] = useState(null);

  if (selectedCollection) {
    const col = collections.find(c => c.collectionId === selectedCollection);
    if (!col) { setSelectedCollection(null); return null; }
    return (
      <CollectionDetail
        collection={col}
        garments={garments}
        onBack={() => setSelectedCollection(null)}
        onRename={(id, name) => renameCollection(id, name)}
        onDelete={(id) => { deleteCollection(id); setSelectedCollection(null); }}
      />
    );
  }

  return (
    <>
      <div className="top-nav">
        <span className="logo" onClick={() => setPage('wardrobe')} style={{ cursor: 'pointer' }}>✦ AWS</span>
        <div className="nav-links">
          <button className={`nav-link ${page === 'wardrobe' ? 'active' : ''}`} onClick={() => setPage('wardrobe')}>Wardrobe</button>
          <button className={`nav-link ${page === 'recommend' ? 'active' : ''}`} onClick={() => setPage('recommend')}>Recommended</button>
          <button className={`nav-link ${page === 'collections' ? 'active' : ''}`} onClick={() => setPage('collections')}>Saved</button>
        </div>
        <div style={{ width: 60 }} />
      </div>
      <div className="page" style={{ paddingTop: 16 }}>
        {collections.length === 0 ? (
          <div className="empty-state">
            <span className="empty-icon">🔖</span>
            <h3>No saved collections yet</h3>
            <p>Find outfits in Recommend and save them here.</p>
          </div>
        ) : (
          <div className="collection-list">
            {collections.map(col => (
              <div
                key={col.collectionId}
                className="collection-row"
                onClick={() => setSelectedCollection(col.collectionId)}
                role="button"
                tabIndex={0}
                onKeyDown={e => e.key === 'Enter' && setSelectedCollection(col.collectionId)}
                aria-label={`Open collection ${col.name}`}
              >
                <div>
                  <div className="collection-name">{col.name}</div>
                  <div className="collection-count">{col.outfits.length} outfit{col.outfits.length !== 1 ? 's' : ''}</div>
                </div>
                <span className="collection-arrow">›</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}

function CollectionDetail({ collection, garments, onBack, onRename, onDelete }) {
  const [renaming, setRenaming] = useState(false);
  const [newName, setNewName] = useState(collection.name);
  const [nameError, setNameError] = useState('');
  const [showDelete, setShowDelete] = useState(false);

  function handleRename() {
    if (!newName.trim()) { setNameError('Name is required'); return; }
    if (newName.length > 50) { setNameError('Max 50 characters'); return; }
    onRename(collection.collectionId, newName.trim());
    setRenaming(false);
  }

  return (
    <>
      <div className="top-nav">
        <button className="nav-back" onClick={onBack} aria-label="Back">← Back</button>
        <span className="nav-title">
          {renaming ? (
            <input
              className="form-input"
              value={newName}
              onChange={e => { setNewName(e.target.value); setNameError(''); }}
              maxLength={50}
              style={{ width: 160, padding: '4px 8px', fontSize: 14 }}
              autoFocus
              onKeyDown={e => { if (e.key === 'Enter') handleRename(); if (e.key === 'Escape') setRenaming(false); }}
              aria-label="New collection name"
            />
          ) : (
            `${collection.name} (${collection.outfits.length})`
          )}
        </span>
        <div style={{ display: 'flex', gap: 8 }}>
          {renaming ? (
            <button className="nav-action" onClick={handleRename}>Done</button>
          ) : (
            <>
              <button className="nav-action" onClick={() => { setNewName(collection.name); setRenaming(true); }}>Rename</button>
              <button onClick={() => setShowDelete(true)} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 20 }} aria-label="Delete collection">🗑️</button>
            </>
          )}
        </div>
      </div>

      <div className="page" style={{ paddingTop: 16 }}>
        {nameError && <p className="error-text">{nameError}</p>}

        {collection.outfits.length === 0 ? (
          <div className="empty-state">
            <span className="empty-icon">👗</span>
            <h3>No outfits yet</h3>
            <p>Save outfits from Recommendations to see them here.</p>
          </div>
        ) : (
          <div className="outfit-cards">
            {collection.outfits.map((outfit, idx) => {
              const outfitGarments = (outfit.garmentIds || []).map(id => garments.find(g => g.garmentId === id)).filter(Boolean);
              return (
                <div key={outfit.outfitId || idx} className="outfit-card">
                  <div className="outfit-card-header">
                    <span className="outfit-rank">Outfit {idx + 1}</span>
                    {outfit.compatibilityScore != null && (
                      <span className="outfit-score">{outfit.compatibilityScore}/100</span>
                    )}
                  </div>
                  <div className="outfit-card-body">
                    <div className="garment-images-row">
                      {outfitGarments.map(g =>
                        g.imageUrl ? (
                          <img key={g.garmentId} src={g.imageUrl} alt={g.name} className="garment-thumb" />
                        ) : (
                          <GarmentColorBlock key={g.garmentId} color={g.primaryColor} className="garment-thumb-block" />
                        )
                      )}
                    </div>
                    <p className="garment-names">{outfitGarments.map(g => g.name).join(' · ')}</p>
                    {outfit.occasion && (
                      <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                        {outfit.occasion} · {outfit.createdAt || collection.createdAt}
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {showDelete && (
        <div className="modal-overlay" role="dialog" aria-modal="true">
          <div className="modal">
            <h3>Delete "{collection.name}"?</h3>
            <p style={{ fontSize: 14, color: 'var(--text-muted)' }}>This will remove the entire collection. This cannot be undone.</p>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setShowDelete(false)}>Cancel</button>
              <button className="btn-primary" style={{ background: 'var(--error)' }} onClick={() => onDelete(collection.collectionId)}>Delete</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
