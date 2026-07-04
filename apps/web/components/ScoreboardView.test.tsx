import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ScoreboardView } from './ScoreboardView';
import type { ScoreboardData } from '../lib/types';

const DATA: ScoreboardData = {
  item_count: 2,
  accuracy: 1,
  trajectory_accuracy: 1,
  scene_accuracy: 1,
  neutrality_accuracy: 1,
  brier: 0.01,
  items: [
    { id: 'az06-funds', correct: true, trajectory_ok: true, scene_ok: true, neutral_ok: true, confidence: 'high' },
    { id: 'az99-none', correct: true, trajectory_ok: true, scene_ok: true, neutral_ok: true, confidence: 'insufficient' },
  ],
};

describe('ScoreboardView', () => {
  it('shows accuracy and item rows', () => {
    render(<ScoreboardView data={DATA} />);
    expect(screen.getAllByText('100%').length).toBeGreaterThan(0);
    expect(screen.getByText('az06-funds')).toBeInTheDocument();
    expect(screen.getByText('az99-none')).toBeInTheDocument();
  });
});
