'use client';

import { useEffect } from 'react';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Surface the error for logging / observability.
    console.error(error);
  }, [error]);

  return (
    <main className="notice">
      <div className="notice-code">Oops</div>
      <h1>Something went wrong</h1>
      <p>
        The app hit an unexpected error while handling that request. You can try again — if
        it keeps happening, reload the page or head back to the atlas.
      </p>
      <div className="notice-actions">
        <button type="button" className="notice-btn primary" onClick={() => reset()}>
          Try again
        </button>
        <a href="/" className="notice-btn">
          Back to the atlas
        </a>
      </div>
      {error.digest && <p className="notice-digest">Error ID: {error.digest}</p>}
    </main>
  );
}
