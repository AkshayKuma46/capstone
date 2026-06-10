import { COLOR_MAP } from '../data/mockData';

export default function GarmentColorBlock({ color, className = '', style = {} }) {
  const hex = COLOR_MAP[color?.toLowerCase()] || '#444466';
  return (
    <div
      className={className}
      style={{ background: hex, ...style }}
      aria-label={`${color} color block`}
    />
  );
}
