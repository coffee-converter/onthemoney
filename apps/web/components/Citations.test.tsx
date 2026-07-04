import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Citations } from './Citations';

describe('Citations', () => {
  it('renders a link per citation', () => {
    render(
      <Citations
        items={[
          { label: 'C00770886', url: 'https://www.fec.gov/data/committee/C00770886/' },
        ]}
      />,
    );
    const link = screen.getByRole('link', { name: 'C00770886' });
    expect(link).toHaveAttribute(
      'href',
      'https://www.fec.gov/data/committee/C00770886/',
    );
  });

  it('renders nothing when empty', () => {
    const { container } = render(<Citations items={[]} />);
    expect(container.firstChild).toBeNull();
  });
});
