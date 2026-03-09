// frontend/src/app/fonts.ts — next/font loaders for Haven typography (Art + Utility)
// Token-first: variables are applied in layout and consumed in globals.css + Tailwind.

import { Playfair_Display, Inter } from 'next/font/google';

/** Art font: elegant serif for headings/display (editorial, intimate). */
export const fontArt = Playfair_Display({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  display: 'swap',
  variable: '--font-art',
});

/** Utility font: clean sans for body/UI. */
export const fontSans = Inter({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  display: 'swap',
  variable: '--font-sans',
});
