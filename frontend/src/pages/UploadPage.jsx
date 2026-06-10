import { useState, useRef } from 'react';
import { useWardrobe } from '../context/WardrobeContext';
import { CATEGORIES, FABRICS, PATTERNS, FIT_TYPES, COLORS, ALL_OCCASIONS } from '../data/mockData';

const MOCK_EXTRACTION = {
  category: 'outerwear',
  primaryColor: 'navy',
  secondaryColor: 'gray',
  fabricType: 'Wool',
  patternType: 'Solid',
  fitType: 'Tailored Fit',
  lowConfidenceFields: ['patternType'],
};

export default function UploadPage({ setPage }) {
  const { addGarment } = useWardrobe();
  const [step, setStep] = useState('select'); // select | processing | review | manual
  const [imagePreview, setImagePreview] = useState(null);
  const [uploadError, setUploadError] = useState('');
  const [progress, setProgress] = useState(0);
  const [dragOver, setDragOver] = useState(false);
  const fileRef = useRef();

  // Form state
  const [form, setForm] = useState({
    name: '',
    category: '',
    primaryColor: '',
    secondaryColor: '',
    fabricType: '',
    patternType: '',
    fitType: '',
    occasionTags: [],
  });
  const [formErrors, setFormErrors] = useState({});
  const [lowConfidenceFields, setLowConfidenceFields] = useState([]);

  function handleFile(file) {
    setUploadError('');
    if (!file) return;
    if (!['image/jpeg', 'image/png'].includes(file.type)) {
      setUploadError('Only JPEG and PNG files are accepted.');
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setUploadError('File too large. Maximum size is 5 MB.');
      return;
    }
    const url = URL.createObjectURL(file);
    setImagePreview(url);
    runMockProcessing();
  }

  function runMockProcessing() {
    setStep('processing');
    setProgress(0);
    let p = 0;
    const interval = setInterval(() => {
      p += 20;
      setProgress(p);
      if (p >= 100) {
        clearInterval(interval);
        // Populate form with mock extraction
        const attrs = MOCK_EXTRACTION;
        setForm({
          name: `${capitalize(attrs.primaryColor)} ${capitalize(attrs.category)}`,
          category: attrs.category,
          primaryColor: attrs.primaryColor,
          secondaryColor: attrs.secondaryColor || '',
          fabricType: attrs.fabricType,
          patternType: attrs.patternType,
          fitType: attrs.fitType,
          occasionTags: ['formal', 'business casual'],
        });
        setLowConfidenceFields(attrs.lowConfidenceFields || []);
        setStep('review');
      }
    }, 300);
  }

  function handleDrop(e) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    handleFile(file);
  }

  function validateForm() {
    const errors = {};
    if (!form.name.trim()) errors.name = 'Name is required';
    if (form.name.length > 100) errors.name = 'Name must be 100 characters or less';
    if (!form.category) errors.category = 'Category is required';
    if (!form.primaryColor) errors.primaryColor = 'Primary color is required';
    if (!form.fabricType) errors.fabricType = 'Fabric is required';
    if (form.occasionTags.length === 0) errors.occasionTags = 'Select at least one occasion';
    return errors;
  }

  function handleSave() {
    const errors = validateForm();
    if (Object.keys(errors).length > 0) {
      setFormErrors(errors);
      return;
    }
    addGarment({ ...form, imageUrl: imagePreview });
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

  // ── Select step ──
  if (step === 'select') {
    return (
      <>
        <div className="top-nav">
          <button className="nav-back" onClick={() => setPage('wardrobe')} aria-label="Back">
            ← Back
          </button>
          <span className="nav-title">Add Garment</span>
          <div style={{ width: 60 }} />
        </div>
        <div className="page" style={{ paddingTop: 16 }}>
          <div
            className={`upload-dropzone ${dragOver ? 'drag-over' : ''}`}
            onDragOver={e => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileRef.current?.click()}
            role="button"
            tabIndex={0}
            onKeyDown={e => e.key === 'Enter' && fileRef.current?.click()}
            aria-label="Upload garment photo"
          >
            <div className="upload-icon">📷</div>
            <h3>Upload Photo</h3>
            <p>Drag and drop or click to browse</p>
            <p style={{ marginTop: 4 }}>JPEG / PNG only · Max 5 MB</p>
          </div>
          <input
            ref={fileRef}
            type="file"
            accept="image/jpeg,image/png"
            style={{ display: 'none' }}
            onChange={e => handleFile(e.target.files[0])}
          />
          {uploadError && <p className="error-text">{uploadError}</p>}

          <div className="upload-divider">— or —</div>

          <div className="upload-actions">
            <button className="btn-secondary" onClick={() => setStep('manual')}>
              Enter Details Manually
            </button>
          </div>
        </div>
      </>
    );
  }

  // ── Processing step ──
  if (step === 'processing') {
    return (
      <>
        <div className="top-nav">
          <button className="nav-back" onClick={() => setStep('select')} aria-label="Back">← Back</button>
          <span className="nav-title">Add Garment</span>
          <div style={{ width: 60 }} />
        </div>
        <div className="page">
          {imagePreview && (
            <img src={imagePreview} alt="Uploaded garment" style={{ width: '100%', maxHeight: 280, objectFit: 'cover' }} />
          )}
          <div className="processing-state">
            <div className="spinner" aria-label="Processing" />
            <p style={{ fontWeight: 600 }}>Analysing garment...</p>
            <div style={{ width: '100%', maxWidth: 320 }}>
              <div className="progress-wrap">
                <div className="progress-bar" style={{ width: `${progress}%` }} />
              </div>
              <p style={{ fontSize: 12, color: 'var(--text-muted)', textAlign: 'center' }}>{progress}%</p>
            </div>
            <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
              {progress < 40 ? 'Identifying garment type...' : progress < 80 ? 'Extracting colors and fabric...' : 'Finalising...'}
            </p>
          </div>
        </div>
      </>
    );
  }

  // ── Review / Manual step ──
  const isManual = step === 'manual';
  return (
    <>
      <div className="top-nav">
        <button className="nav-back" onClick={() => setStep('select')} aria-label="Back">← Back</button>
        <span className="nav-title">Review Details</span>
        <button className="nav-action" onClick={handleSave} aria-label="Save garment">Save</button>
      </div>
      <div className="page" style={{ paddingTop: 16 }}>
        {imagePreview && (
          <img src={imagePreview} alt="Garment" style={{ width: '100%', maxHeight: 220, objectFit: 'cover', marginBottom: 16 }} />
        )}

        <div className="form-section">
          {/* Name */}
          <div className="form-group">
            <label className="form-label">
              Garment Name <span className="required">*</span>
            </label>
            <input
              className={`form-input ${formErrors.name ? 'warn' : ''}`}
              value={form.name}
              maxLength={100}
              onChange={e => setForm(p => ({ ...p, name: e.target.value }))}
              placeholder="e.g. Navy Blazer"
              aria-label="Garment name"
            />
            <div className={`char-count ${form.name.length > 100 ? 'over' : ''}`}>
              {form.name.length}/100
            </div>
            {formErrors.name && <p className="error-text">{formErrors.name}</p>}
          </div>

          {/* Category */}
          <FormSelect
            label="Garment Type"
            required
            field="category"
            options={CATEGORIES}
            form={form}
            setForm={setForm}
            errors={formErrors}
            lowConf={lowConfidenceFields}
          />

          {/* Primary Color */}
          <FormSelect
            label="Primary Color"
            required
            field="primaryColor"
            options={COLORS}
            form={form}
            setForm={setForm}
            errors={formErrors}
            lowConf={lowConfidenceFields}
          />

          {/* Secondary Color */}
          <FormSelect
            label="Secondary Color"
            field="secondaryColor"
            options={['', ...COLORS]}
            form={form}
            setForm={setForm}
            errors={formErrors}
            lowConf={lowConfidenceFields}
          />

          {/* Fabric */}
          <FormSelect
            label="Fabric"
            required
            field="fabricType"
            options={FABRICS}
            form={form}
            setForm={setForm}
            errors={formErrors}
            lowConf={lowConfidenceFields}
          />

          {/* Pattern */}
          <FormSelect
            label="Pattern"
            field="patternType"
            options={PATTERNS}
            form={form}
            setForm={setForm}
            errors={formErrors}
            lowConf={lowConfidenceFields}
          />

          {/* Fit */}
          <FormSelect
            label="Fit"
            field="fitType"
            options={FIT_TYPES}
            form={form}
            setForm={setForm}
            errors={formErrors}
            lowConf={lowConfidenceFields}
          />

          {/* Occasion Tags */}
          <div className="form-group">
            <label className="form-label">
              Occasion Tags <span className="required">*</span>
            </label>
            <div className="tag-list" role="group" aria-label="Occasion tags">
              {ALL_OCCASIONS.map(tag => (
                <button
                  key={tag}
                  className={`tag ${form.occasionTags.includes(tag) ? 'selected' : ''}`}
                  onClick={() => toggleOccasion(tag)}
                  type="button"
                  aria-pressed={form.occasionTags.includes(tag)}
                >
                  {tag}
                </button>
              ))}
            </div>
            {formErrors.occasionTags && <p className="error-text">{formErrors.occasionTags}</p>}
          </div>

          <button className="btn-primary" style={{ width: '100%', marginTop: 8 }} onClick={handleSave}>
            Save Garment
          </button>
        </div>
      </div>
    </>
  );
}

function FormSelect({ label, required, field, options, form, setForm, errors, lowConf }) {
  const isLow = lowConf.includes(field);
  return (
    <div className="form-group">
      <label className="form-label">
        {label}
        {required && <span className="required"> *</span>}
        {isLow && <span className="warn-badge">⚠ Verify</span>}
      </label>
      <select
        className={`form-select ${errors[field] ? 'warn' : isLow ? 'warn' : ''}`}
        value={form[field] || ''}
        onChange={e => setForm(p => ({ ...p, [field]: e.target.value }))}
        aria-label={label}
      >
        <option value="">Select {label}</option>
        {options.filter(Boolean).map(opt => (
          <option key={opt} value={opt}>{capitalize(opt)}</option>
        ))}
      </select>
      {errors[field] && <p className="error-text">{errors[field]}</p>}
    </div>
  );
}

function capitalize(str) {
  if (!str) return '';
  return str.charAt(0).toUpperCase() + str.slice(1);
}
