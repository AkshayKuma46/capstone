import { createContext, useContext, useState, useEffect } from 'react';

const WardrobeContext = createContext(null);
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export function WardrobeProvider({ children }) {
  const [garments, setGarments] = useState([]);
  const [collections, setCollections] = useState([]);
  const [toast, setToast] = useState(null);

  function showToast(message, type = 'success') {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  }

  function groupOutfitsIntoCollections(outfits) {
    const map = {};
    outfits.forEach(o => {
      const name = o.collectionName;
      if (!name) return;
      if (!map[name]) {
        map[name] = {
          collectionId: name,
          name: name,
          outfits: [],
          createdAt: o.createdAt ? o.createdAt.split('T')[0] : new Date().toISOString().split('T')[0]
        };
      }
      map[name].outfits.push(o);
    });
    return Object.values(map);
  }

  async function fetchGarments() {
    try {
      const res = await fetch(`${API_BASE}/garments?user_id=demo-user`);
      if (!res.ok) throw new Error('Failed to fetch garments');
      const data = await res.json();
      setGarments(data.garments || []);
    } catch (err) {
      console.error('Error fetching garments:', err);
    }
  }

  async function fetchCollections() {
    try {
      const res = await fetch(`${API_BASE}/outfits?user_id=demo-user`);
      if (!res.ok) throw new Error('Failed to fetch outfits');
      const data = await res.json();
      setCollections(groupOutfitsIntoCollections(data.outfits || []));
    } catch (err) {
      console.error('Error fetching collections:', err);
    }
  }

  useEffect(() => {
    fetchGarments();
    fetchCollections();
  }, []);

  async function addGarment(garment) {
    try {
      const response = await fetch(`${API_BASE}/garments?user_id=demo-user`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: garment.name,
          category: garment.category,
          primaryColor: garment.primaryColor,
          secondaryColor: garment.secondaryColor || null,
          fabricType: garment.fabricType,
          patternType: garment.patternType || null,
          fitType: garment.fitType || null,
          styleTag: garment.styleTag || null,
          occasionTags: garment.occasionTags,
          imageUrl: garment.imageUrl || null,
        }),
      });
      if (!response.ok) throw new Error('Failed to add garment');
      const saved = await response.json();
      setGarments(prev => [...prev, saved]);
      showToast('Garment added to wardrobe ✓');
      return saved;
    } catch (err) {
      console.error(err);
      showToast('Failed to save garment', 'error');
    }
  }

  async function updateGarment(garmentId, updates) {
    try {
      const response = await fetch(`${API_BASE}/garments/${garmentId}?user_id=demo-user`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: updates.name,
          category: updates.category,
          primaryColor: updates.primaryColor,
          secondaryColor: updates.secondaryColor || null,
          fabricType: updates.fabricType,
          patternType: updates.patternType || null,
          fitType: updates.fitType || null,
          styleTag: updates.styleTag || null,
          occasionTags: updates.occasionTags,
          imageUrl: updates.imageUrl || null,
        }),
      });
      if (!response.ok) throw new Error('Failed to update garment');
      const updated = await response.json();
      setGarments(prev => prev.map(g => g.garmentId === garmentId ? updated : g));
      showToast('Garment updated ✓');
    } catch (err) {
      console.error(err);
      showToast('Failed to update garment', 'error');
    }
  }

  async function deleteGarment(garmentId) {
    try {
      const response = await fetch(`${API_BASE}/garments/${garmentId}?user_id=demo-user`, {
        method: 'DELETE',
      });
      if (!response.ok) throw new Error('Failed to delete garment');
      setGarments(prev => prev.filter(g => g.garmentId !== garmentId));
      showToast('Garment deleted');
    } catch (err) {
      console.error(err);
      showToast('Failed to delete garment', 'error');
    }
  }

  async function saveOutfitToCollection(outfit, collectionName) {
    try {
      const response = await fetch(`${API_BASE}/outfits?user_id=demo-user`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          outfitId: outfit.outfitId,
          collectionName: collectionName,
          garmentIds: outfit.garmentIds,
          occasion: outfit.occasion,
          compatibilityScore: outfit.compatibilityScore,
          confidenceScore: outfit.confidenceScore,
          explanation: outfit.explanation,
          corpusVersion: outfit.corpusVersion || '1.1.0',
        }),
      });
      if (!response.ok) throw new Error('Failed to save outfit');
      await fetchCollections();
      showToast(`Saved to "${collectionName}" ✓`);
    } catch (err) {
      console.error(err);
      showToast('Failed to save outfit', 'error');
    }
  }

  function renameCollection(collectionId, newName) {
    setCollections(prev =>
      prev.map(c => c.collectionId === collectionId ? { ...c, name: newName } : c)
    );
  }

  function deleteCollection(collectionId) {
    setCollections(prev => prev.filter(c => c.collectionId !== collectionId));
    showToast('Collection deleted');
  }

  return (
    <WardrobeContext.Provider value={{
      garments,
      collections,
      toast,
      addGarment,
      updateGarment,
      deleteGarment,
      saveOutfitToCollection,
      renameCollection,
      deleteCollection,
      showToast,
    }}>
      {children}
    </WardrobeContext.Provider>
  );
}

export function useWardrobe() {
  return useContext(WardrobeContext);
}
