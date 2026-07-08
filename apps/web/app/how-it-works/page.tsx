import type { Metadata } from 'next';
import { HowItWorks } from '../../components/HowItWorks';

export const metadata: Metadata = {
  title: 'Under the hood',
  description:
    'How the agent works: every figure grounded in a tool result, calibrated confidence with an explicit insufficient-evidence state, a golden-set eval gate in CI, and live operability.',
  alternates: { canonical: '/how-it-works' },
};

export default function HowItWorksPage() {
  return (
    <main className="page">
      <HowItWorks />
    </main>
  );
}
