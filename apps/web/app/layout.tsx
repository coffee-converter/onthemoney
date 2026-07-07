import './globals.css';
import type { ReactNode } from 'react';
import { Analytics } from '@vercel/analytics/react';

export const metadata = {
  title: 'On The Money',
  description: 'A conversational accountability atlas.',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <nav className="topnav">
          <a href="/" className="brand">On The Money</a>
          <div className="topnav-links">
            <a href="/">Atlas</a>
            <a href="/scoreboard">Scoreboard</a>
            <a href="/how-it-works">Under the hood</a>
          </div>
        </nav>
        {children}
        <Analytics />
      </body>
    </html>
  );
}
