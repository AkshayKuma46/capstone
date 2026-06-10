import { useState } from 'react';
import { WardrobeProvider } from './context/WardrobeContext';
import BottomNav from './components/BottomNav';
import Toast from './components/Toast';
import WardrobePage from './pages/WardrobePage';
import UploadPage from './pages/UploadPage';
import GarmentDetailPage from './pages/GarmentDetailPage';
import RecommendPage from './pages/RecommendPage';
import CollectionsPage from './pages/CollectionsPage';

function AppContent() {
  const [page, setPage] = useState('wardrobe');
  const [selectedGarmentId, setSelectedGarmentId] = useState(null);

  function renderPage() {
    switch (page) {
      case 'wardrobe':
        return <WardrobePage setPage={setPage} setSelectedGarmentId={setSelectedGarmentId} />;
      case 'upload':
        return <UploadPage setPage={setPage} />;
      case 'garment-detail':
        return <GarmentDetailPage garmentId={selectedGarmentId} setPage={setPage} />;
      case 'recommend':
        return <RecommendPage setPage={setPage} />;
      case 'collections':
        return <CollectionsPage />;
      default:
        return <WardrobePage setPage={setPage} setSelectedGarmentId={setSelectedGarmentId} />;
    }
  }

  // Pages that show bottom nav
  const showBottomNav = ['wardrobe', 'recommend', 'collections'].includes(page);

  return (
    <div className="app">
      {renderPage()}
      {showBottomNav && (
        <BottomNav
          page={page}
          setPage={p => {
            setPage(p);
            setSelectedGarmentId(null);
          }}
        />
      )}
      <Toast />
    </div>
  );
}

export default function App() {
  return (
    <WardrobeProvider>
      <AppContent />
    </WardrobeProvider>
  );
}
