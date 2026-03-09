/**
 * P2-A3: Single LazyMotion boundary for card-ritual (flip/swipe/glow).
 * Use m from framer-motion only inside this provider. Strict mode prevents
 * accidental full motion bundle load. Do not use outside card-ritual flows.
 */

'use client';

import { LazyMotion, domAnimation } from 'framer-motion';

interface MotionProviderProps {
  children: React.ReactNode;
}

export function MotionProvider({ children }: MotionProviderProps) {
  return (
    <LazyMotion strict features={domAnimation}>
      {children}
    </LazyMotion>
  );
}
