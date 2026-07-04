import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ConfidenceChip } from './ConfidenceChip';

describe('ConfidenceChip', () => {
  it('renders the label for each level', () => {
    const { rerender } = render(<ConfidenceChip level="high" />);
    expect(screen.getByText('High confidence')).toBeInTheDocument();
    rerender(<ConfidenceChip level="partial" />);
    expect(screen.getByText('Partial data')).toBeInTheDocument();
    rerender(<ConfidenceChip level="insufficient" />);
    expect(screen.getByText('Insufficient evidence')).toBeInTheDocument();
  });
});
