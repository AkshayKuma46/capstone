import { createContext, useContext, useState } from 'react';
import { garments as initialGarments } from '../data/mockData';

const WardrobeContext = createContext(null);

export function WardrobeProvider({ children }) {
  const [garments, setGarments] = useState(initialGarments);
  const [collections, setCollections] = useState([]);
  const [toast, setToast] = useState(null);

  function showToast(message, type = 'success') {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  }

  function addGarment(garment) {
    const newGarment = {
      ...garment,
      garmentId: Date.now().toString(),
      createdAt: new Date().toISOString().split('T')[0],
    };
    setGarments(prev => [...prev, newGarment]);
    showToast('Garment added to wardrobe ✓');
    return newGarment;
  }

  function updateGarment(garmentId, updates) {
    setGarments(prev =>
      prev.map(g => g.garmentId === garmentId ? { ...g, ...updates } : g)
    );
    showToast('Garment updated ✓');
  }

  function deleteGarment(garmentId) {
    setGarments(prev => prev.filter(g => g.garmentId !== garmentId));
    showToast('Garment deleted');
  }

  function saveOutfitToCollection(outfit, collectionName) {
    setCollections(prev => {
      const existing = prev.find(c => c.name === collectionName);
      if (existing) {
        return prev.map(c =>
          c.name === collectionName
            ? { ...c, outfits: [...c.outfits, outfit] }
            : c
        );
      }
      return [...prev, {
        collectionId: Date.now().toString(),
        name: collectionName,
        outfits: [outfit],
        createdAt: new Date().toISOString().split('T')[0],
      }];
    });
    showToast(`Saved to "${collectionName}" ✓`);
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
