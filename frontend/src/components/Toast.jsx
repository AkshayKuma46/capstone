import { useWardrobe } from '../context/WardrobeContext';

export default function Toast() {
  const { toast } = useWardrobe();
  if (!toast) return null;

  return (
    <div className={`toast ${toast.type}`} role="status" aria-live="polite">
      {toast.type === 'success' && '✓'}
      {toast.type === 'error' && '✗'}
      {toast.message}
    </div>
  );
}
