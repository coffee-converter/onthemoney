import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
const track = vi.fn();
vi.mock('@vercel/analytics', () => ({ track: (...a: unknown[]) => track(...a) }));
// EventSource isn't in jsdom; stub it so runQuery can construct one without erroring.
vi.stubGlobal('EventSource', class { close() {} addEventListener() {} } as unknown as typeof EventSource);
import { Chat } from './Chat';

describe('Chat analytics', () => {
  it('emits an ask analytics event on submit', () => {
    render(<Chat onScene={() => {}} onCandidate={() => {}} onReset={() => {}} />);
    fireEvent.change(screen.getByLabelText('question'), { target: { value: 'Where is IL-04?' } });
    fireEvent.submit(screen.getByLabelText('question').closest('form')!);
    expect(track).toHaveBeenCalledWith('ask', expect.objectContaining({ queryLength: 15 }));
  });
});
