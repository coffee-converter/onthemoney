import type { Metadata } from 'next';
import { Scoreboard } from '../../components/Scoreboard';

export const metadata: Metadata = {
  title: 'Accuracy scoreboard',
  description:
    'How On The Money scores against provable FEC ground truth: accuracy, calibration (Brier score), trajectory, scene, and neutrality — graded by a deterministic eval in CI.',
  alternates: { canonical: '/scoreboard' },
};

export default function ScoreboardPage() {
  return (
    <main className="page">
      <Scoreboard />
    </main>
  );
}
