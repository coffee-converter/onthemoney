'use client';
import { useState, type FormEvent } from 'react';
import { streamAsk } from '../lib/api';
import type { Answer, Scene, Step } from '../lib/types';
import { ConfidenceChip } from './ConfidenceChip';
import { Citations } from './Citations';

const SAMPLE = 'Who funds the representative in IL-5?';

function stepLabel(step: Step): string {
  if (step.type === 'tool_use') return `Calling ${step.name}`;
  if (step.type === 'tool_result') return `${step.name} returned`;
  if (step.type === 'text') return step.text ?? '';
  return step.type;
}

export function Chat({ onScene }: { onScene: (s: Scene) => void }) {
  const [query, setQuery] = useState(SAMPLE);
  const [steps, setSteps] = useState<Step[]>([]);
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [busy, setBusy] = useState(false);

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!query.trim() || busy) return;
    setSteps([]);
    setAnswer(null);
    setBusy(true);
    streamAsk(query, (step) => {
      if (step.type === 'answer') {
        const a = step as unknown as Answer;
        setAnswer(a);
        if (a.scene) onScene(a.scene);
        setBusy(false);
        return;
      }
      setSteps((prev) => [...prev, step]);
      if (
        step.type === 'tool_result' &&
        step.name === 'emit_scene' &&
        step.payload &&
        'highlight' in step.payload
      ) {
        onScene(step.payload as unknown as Scene);
      }
    });
  }

  return (
    <div className="chat">
      <h1>On The Money</h1>
      <p className="subtle">Ask how House campaign money flows. 2024 cycle.</p>
      <form onSubmit={submit}>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="question"
        />
        <button type="submit" disabled={busy}>
          {busy ? 'Working' : 'Ask'}
        </button>
      </form>

      <ol className="trace">
        {steps.map((s, i) => (
          <li key={i} className={`trace-${s.type}`}>
            {stepLabel(s)}
          </li>
        ))}
      </ol>

      {answer && (
        <div className="answer">
          <ConfidenceChip level={answer.confidence} />
          <p>{answer.text}</p>
          <Citations items={answer.citations} />
        </div>
      )}
    </div>
  );
}
