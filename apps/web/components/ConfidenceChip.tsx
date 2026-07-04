import type { Confidence } from '../lib/types';

const LABELS: Record<Confidence, string> = {
  high: 'High confidence',
  partial: 'Partial data',
  insufficient: 'Insufficient evidence',
};

export function ConfidenceChip({ level }: { level: Confidence }) {
  return (
    <span className={`chip chip-${level}`} role="status">
      {LABELS[level]}
    </span>
  );
}
