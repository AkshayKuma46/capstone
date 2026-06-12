import { useState } from 'react';
import { useWardrobe } from '../context/WardrobeContext';
import GarmentColorBlock from '../components/GarmentColorBlock';
import { CATEGORIES, FABRICS, PATTERNS, FIT_TYPES, COLORS, ALL_OCCASIONS, COLOR_MAP } from '../data/mockData';

export default function GarmentDetailPage({ garmentId, setPage }) {
  const { garments, updateGarment, deleteGarment, collections } = useWardrobe();
  const garment = garments.find(g => g.garmentId === garmentId);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState(garment || {});
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  if (!garment) {
    return (
      <div className="empty-state">
        <span className="empty-icon">🔍</span>
        <h3>Garment not found</h3>
        <button className="btn-ghost" onClick={() => setPage('wardrobe')}>← Back to Wardrobe</button>
      </div>
    );
  }

  function handleSave() {
    updateGarment(garmentId, form);
    setEditing(false);
  }

  function handleDelete() {
    deleteGarment(garmentId);
    setPage('wardrobe');
  }

  function toggleOccasion(tag) {
    setForm(prev => ({
      ...prev,
      occasionTags: prev.occasionTags.includes(tag)
        ? prev.occasionTags.filter(t => t !== tag)
        : [...prev.occasionTags, tag],
    }));
  }

  const hex = COLOR_MAP[garment.primaryColor?.toLowerCase()] || '#444466';

  return (
    <>
      <div className="top-nav">
        <button className="nav-back" onClick={() => setPage('wardrobe')} aria-label="Back">← Back</button>
        <span className="nav-title" style={{ maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {garment.name}
        </span>
        <div style={{ display: 'flex', gap: 8 }}>
          {!editing && (
            <button className="nav-action" onClick={() => { setForm({ ...garment }); setEditing(true); }}>
              Edit
            </button>
          )}
          <button
            onClick={() => setShowDeleteConfirm(true)}
            style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 20 }}
            aria-label="Delete garment"
          >
            🗑️
          </button>
        </div>
      </div>

      <div className="page">
        {garment.imageUrl ? (
          <img src={garment.imageUrl} alt={garment.name} className="garment-detail-image" />
        ) : (
          <GarmentColorBlock color={garment.primaryColor} className="garment-detail-color-block" />
        )}

        <div className="detail-rows">
          {editing ? (
            <EditForm
              form={form}
              setForm={setForm}
              toggleOccasion={toggleOccasion}
              onSave={handleSave}
              onCancel={() => setEditing(false)}
            />
          ) : (
            <ViewDetails 
              garment={garment} 
              hex={hex} 
              featuredOutfits={(collections || []).reduce((acc, col) => {
                (col.outfits || []).forEach(o => {
                  if (o.garmentIds?.includes(garmentId)) {
                    acc.push(col.name);
                  }
                });
                return acc;
              }, [])} 
            />
          )}
        </div>
      </div>

      {/* Delete confirmation modal */}
      {showDeleteConfirm && (
        <div className="modal-overlay" role="dialog" aria-modal="true" aria-label="Delete confirmation">
          <div className="modal">
            <h3>Delete {garment.name}?</h3>
            <p style={{ fontSize: 14, color: 'var(--text-muted)' }}>This cannot be undone.</p>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setShowDeleteConfirm(false)}>Cancel</button>
              <button className="btn-primary" style={{ background: 'var(--error)' }} onClick={handleDelete}>Delete</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function ViewDetails({ garment, hex, featuredOutfits }) {
  const rows = [
    { label: 'Category', value: capitalize(garment.category) },
    { label: 'Color Palette', value: (
      <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <span className="color-dot" style={{ background: hex }} />
        {capitalize(garment.primaryColor)} {garment.secondaryColor ? `· ${capitalize(garment.secondaryColor)}` : ''}
      </span>
    )},
    { label: 'Fabric Composition', value: capitalize(garment.fabricType) },
    garment.patternType && { label: 'Pattern', value: capitalize(garment.patternType) },
    garment.fitType && { label: 'Fit', value: capitalize(garment.fitType) },
    { label: 'Added', value: garment.createdAt },
  ].filter(Boolean);

  return (
    <>
      {rows.map(row => (
        <div key={row.label} className="detail-row">
          <span className="label">{row.label}</span>
          <span className="value">{row.value}</span>
        </div>
      ))}
      <div style={{ paddingTop: 16 }}>
        <p style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 8, letterSpacing: '0.08em', textTransform: 'uppercase' }}>RECOMMENDED OCCASIONS</p>
        <div className="tag-list">
          {garment.occasionTags.map(tag => (
            <span key={tag} className="tag selected" style={{ cursor: 'default' }}>{tag}</span>
          ))}
        </div>
      </div>

      {featuredOutfits && featuredOutfits.length > 0 && (
        <div style={{ paddingTop: 20, borderTop: '1px solid var(--border)', marginTop: 16 }}>
          <p style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 10, letterSpacing: '0.08em', textTransform: 'uppercase' }}>FEATURED IN</p>
          <ul style={{ listStyleType: 'none', paddingLeft: 0, color: 'var(--text)', fontSize: 14 }}>
            {Array.from(new Set(featuredOutfits)).map((name, idx) => (
              <li key={idx} style={{ marginBottom: 6, display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--primary)', display: 'inline-block' }} />
                {name}
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}

function EditForm({ form, setForm, toggleOccasion, onSave, onCancel }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div className="form-group">
        <label className="form-label">Name</label>
        <input className="form-input" value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} maxLength={100} />
      </div>

      {[
        { label: 'Category', field: 'category', options: CATEGORIES },
        { label: 'Primary Color', field: 'primaryColor', options: COLORS },
        { label: 'Secondary Color', field: 'secondaryColor', options: ['', ...COLORS] },
        { label: 'Fabric', field: 'fabricType', options: FABRICS },
        { label: 'Pattern', field: 'patternType', options: PATTERNS },
        { label: 'Fit', field: 'fitType', options: ['', ...FIT_TYPES] },
      ].map(({ label, field, options }) => (
        <div className="form-group" key={field}>
          <label className="form-label">{label}</label>
          <select className="form-select" value={form[field] || ''} onChange={e => setForm(p => ({ ...p, [field]: e.target.value }))}>
            {options.map(opt => <option key={opt} value={opt}>{opt ? capitalize(opt) : `Select ${label}`}</option>)}
          </select>
        </div>
      ))}

      <div className="form-group">
        <label className="form-label">Occasions</label>
        <div className="tag-list" role="group">
          {ALL_OCCASIONS.map(tag => (
            <button key={tag} className={`tag ${form.occasionTags?.includes(tag) ? 'selected' : ''}`}
              onClick={() => toggleOccasion(tag)} type="button" aria-pressed={form.occasionTags?.includes(tag)}>
              {tag}
            </button>
          ))}
        </div>
      </div>

      <div style={{ display: 'flex', gap: 8 }}>
        <button className="btn-secondary" style={{ flex: 1 }} onClick={onCancel}>Cancel</button>
        <button className="btn-primary" style={{ flex: 1 }} onClick={onSave}>Save Changes</button>
      </div>
    </div>
  );
}

function capitalize(str) {
  if (!str) return '';
  return str.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}
