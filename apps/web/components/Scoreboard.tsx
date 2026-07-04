'use client';
import { useEffect, useState } from 'react';
import { fetchScoreboard } from '../lib/api';
import type { ScoreboardData } from '../lib/types';
import { ScoreboardView } from './ScoreboardView';

export function Scoreboard() {
  const [data, setData] = useState<ScoreboardData | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetchScoreboard()
      .then(setData)
      .catch(() => setError(true));
  }, []);

  if (error) return <p className="error">Could not load the scoreboard.</p>;
  if (!data) return <p>Loading...</p>;
  return <ScoreboardView data={data} />;
}
