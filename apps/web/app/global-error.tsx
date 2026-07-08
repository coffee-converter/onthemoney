'use client';

import { useEffect } from 'react';

// Catches errors thrown in the root layout itself. It replaces the whole
// document, so it must render its own <html>/<body>. Styles are inline
// because globals.css may not have loaded when this renders.
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '0.75rem',
          textAlign: 'center',
          padding: '2rem 1.25rem',
          background: '#0d1117',
          color: '#e6edf3',
          fontFamily: 'ui-sans-serif, system-ui, sans-serif',
        }}
      >
        <div style={{ fontSize: '3rem', fontWeight: 800, color: '#4aa3ff', lineHeight: 1 }}>
          Oops
        </div>
        <h1 style={{ fontSize: '1.35rem', margin: 0 }}>Something went wrong</h1>
        <p style={{ color: '#9aa4b2', maxWidth: '32rem', margin: 0, lineHeight: 1.5 }}>
          The app hit an unexpected error. Try again, or reload the page.
        </p>
        <div style={{ display: 'flex', gap: '0.6rem', marginTop: '0.75rem' }}>
          <button
            type="button"
            onClick={() => reset()}
            style={{
              padding: '0.5rem 1rem',
              borderRadius: 8,
              border: '1px solid #4aa3ff',
              background: '#4aa3ff',
              color: '#06121f',
              fontSize: '0.9rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Try again
          </button>
          <a
            href="/"
            style={{
              padding: '0.5rem 1rem',
              borderRadius: 8,
              border: '1px solid #2a3038',
              background: '#161b22',
              color: '#e6edf3',
              fontSize: '0.9rem',
              fontWeight: 600,
              textDecoration: 'none',
            }}
          >
            Back to the atlas
          </a>
        </div>
        {error.digest && (
          <p
            style={{
              fontFamily: 'ui-monospace, monospace',
              fontSize: '0.72rem',
              color: '#9aa4b2',
              opacity: 0.7,
              marginTop: '0.5rem',
            }}
          >
            Error ID: {error.digest}
          </p>
        )}
      </body>
    </html>
  );
}
