// Mock garment data — replace with real API calls when FastAPI is ready

export const COLOR_MAP = {
  navy: '#1a2e5a',
  white: '#f0f0f0',
  black: '#1a1a1a',
  gray: '#888888',
  beige: '#c8b89a',
  brown: '#6b4226',
  khaki: '#c3a97a',
  red: '#a02020',
  blue: '#2a5fa0',
  green: '#2a6040',
  burgundy: '#6b1a2a',
  charcoal: '#3a3a3a',
  cream: '#ede0c8',
  olive: '#5a6020',
  pink: '#c05070',
};

export const OCCASIONS = [
  { id: 'casual',          label: 'Everyday',        emoji: '👔' },
  { id: 'business casual', label: 'Office',           emoji: '💼' },
  { id: 'formal',          label: 'Formal',           emoji: '🍽️' },
  { id: 'date night',      label: 'Date Night',       emoji: '💑' },
  { id: 'outdoor',         label: 'Outdoor',          emoji: '🌿' },
  { id: 'sport',           label: 'Gym',              emoji: '🏋️' },
  { id: 'travel',          label: 'Travel',           emoji: '✈️' },
  { id: 'wedding',         label: 'Wedding',          emoji: '💒' },
  { id: 'festival',        label: 'Festival',         emoji: '🎪' },
  { id: 'party',           label: 'Party',            emoji: '🎉' },
];

export const CATEGORIES = ['top', 'bottom', 'outerwear', 'footwear', 'accessory', 'full_outfit'];
export const FABRICS = ['cotton', 'wool', 'linen', 'polyester', 'denim', 'silk', 'leather', 'cashmere', 'synthetic'];
export const PATTERNS = ['solid', 'striped', 'checked', 'floral', 'plaid', 'abstract', 'printed'];
export const FIT_TYPES = ['slim fit', 'regular fit', 'relaxed fit', 'oversized fit', 'tailored fit', 'skinny fit', 'athletic fit'];
export const COLORS = Object.keys(COLOR_MAP);
export const ALL_OCCASIONS = OCCASIONS.map(o => o.id);

export let garments = [
  {
    garmentId: '1',
    name: 'Navy Blazer',
    category: 'outerwear',
    primaryColor: 'navy',
    secondaryColor: 'gray',
    fabricType: 'Wool',
    patternType: 'Solid',
    fitType: 'Tailored Fit',
    occasionTags: ['formal', 'business casual'],
    imageUrl: null,
    createdAt: '2026-06-01',
  },
  {
    garmentId: '2',
    name: 'White Oxford Shirt',
    category: 'top',
    primaryColor: 'white',
    secondaryColor: null,
    fabricType: 'Cotton',
    patternType: 'Solid',
    fitType: 'Regular Fit',
    occasionTags: ['casual', 'business casual', 'formal'],
    imageUrl: null,
    createdAt: '2026-06-02',
  },
  {
    garmentId: '3',
    name: 'Charcoal Trousers',
    category: 'bottom',
    primaryColor: 'charcoal',
    secondaryColor: null,
    fabricType: 'Wool',
    patternType: 'Solid',
    fitType: 'Slim Fit',
    occasionTags: ['formal', 'business casual'],
    imageUrl: null,
    createdAt: '2026-06-03',
  },
  {
    garmentId: '4',
    name: 'Brown Derby Shoes',
    category: 'footwear',
    primaryColor: 'brown',
    secondaryColor: null,
    fabricType: 'Leather',
    patternType: 'Solid',
    fitType: null,
    occasionTags: ['formal', 'business casual', 'casual'],
    imageUrl: null,
    createdAt: '2026-06-04',
  },
  {
    garmentId: '5',
    name: 'Khaki Chinos',
    category: 'bottom',
    primaryColor: 'khaki',
    secondaryColor: null,
    fabricType: 'Cotton',
    patternType: 'Solid',
    fitType: 'Regular Fit',
    occasionTags: ['casual', 'business casual'],
    imageUrl: null,
    createdAt: '2026-06-05',
  },
  {
    garmentId: '6',
    name: 'Black Turtleneck',
    category: 'top',
    primaryColor: 'black',
    secondaryColor: null,
    fabricType: 'Cotton',
    patternType: 'Solid',
    fitType: 'Slim Fit',
    occasionTags: ['casual', 'date night'],
    imageUrl: null,
    createdAt: '2026-06-06',
  },
];

// Mock outfit combinations scored for demo
export function generateOutfits(occasion, wardrobeItems) {
  if (wardrobeItems.length === 0) return [];

  const mock = [
    {
      outfitId: 'o1',
      garmentIds: ['1', '2', '3', '4'],
      compatibilityScore: 87,
      confidenceScore: 0.91,
      occasion,
      explanation: 'Navy and charcoal are reliable tonal companions. The tailored blazer with slim trousers creates clean proportions for office wear, grounded by classic brown leather.',
    },
    {
      outfitId: 'o2',
      garmentIds: ['2', '5', '4'],
      compatibilityScore: 79,
      confidenceScore: 0.54,
      occasion,
      explanation: 'Classic smart casual formula. The white shirt grounds the outfit and khaki chinos add relaxed elegance, making this versatile for a range of settings.',
    },
    {
      outfitId: 'o3',
      garmentIds: ['6', '3', '4'],
      compatibilityScore: 71,
      confidenceScore: 0.68,
      occasion,
      explanation: 'A black turtleneck with charcoal trousers creates a tonal monochrome look — minimal and polished. Brown shoes introduce a warm contrast that prevents the outfit from feeling flat.',
    },
  ];

  // Filter to only include garments that exist in wardrobe
  const ids = new Set(wardrobeItems.map(g => g.garmentId));
  return mock
    .map(o => ({ ...o, garmentIds: o.garmentIds.filter(id => ids.has(id)) }))
    .filter(o => o.garmentIds.length >= 2)
    .slice(0, 3);
}
