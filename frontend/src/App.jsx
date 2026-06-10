import { useState } from 'react';
import { WardrobeProvider } from './context/WardrobeContext';
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
        return <WardrobePage page={page} setPage={setPage} setSelectedGarmentId={setSelectedGarmentId} />;
      case 'upload':
        return <UploadPage setPage={setPage} />;
      case 'garment-detail':
        return <GarmentDetailPage garmentId={selectedGarmentId} setPage={setPage} />;
      case 'recommend':
        return <RecommendPage page={page} setPage={setPage} />;
      case 'collections':
        return <CollectionsPage page={page} setPage={setPage} />;
      default:
        return <WardrobePage page={page} setPage={setPage} setSelectedGarmentId={setSelectedGarmentId} />;
    }
  }

  return (
    <div className="app">
      {renderPage()}
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
