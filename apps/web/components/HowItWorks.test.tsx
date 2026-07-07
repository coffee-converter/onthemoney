import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { HowItWorks } from './HowItWorks';

vi.mock('../lib/regression.json', () => ({
  default: { case: 'ca22-funds', cases_affected: 8, clean_total: '12000.00', broken_total: '10800.00',
    before: { accuracy: 1.0, brier: 0.07, passes: true },
    after: { accuracy: 0.95, brier: 0.31, passes: false },
    delta: { accuracy: 0.05, brier: 0.24 },
    thresholds: { min_accuracy: 0.9, max_brier: 0.2 } },
}));

describe('HowItWorks', () => {
  it('renders the four pillars and the caught regression', () => {
    render(<HowItWorks />);
    expect(screen.getByText(/Grounded by construction/i)).toBeTruthy();
    expect(screen.getByRole('heading', { name: /Verify/i })).toBeTruthy();
    expect(screen.getByText(/Evaluated/i)).toBeTruthy();
    expect(screen.getByText(/Operated/i)).toBeTruthy();
    // The regression story shows the gate flipping.
    expect(screen.getByText(/ca22-funds/)).toBeTruthy();
    expect(screen.getByText(/deterministic/i)).toBeTruthy(); // honest baseline label
  });
});
