import './globals.css';
import type { ReactNode } from 'react';

export const metadata = {
  title: 'On The Money',
  description: 'A conversational accountability atlas.',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <nav className="topnav">
          <a href="/">Atlas</a>
          <a href="/scoreboard">Scoreboard</a>
        </nav>
        {children}
      </body>
    </html>
  );
}
