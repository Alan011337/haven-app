/**
 * P2-A1: Shared card-back chrome (radius, shadow, paper/glass surface).
 * Use only via CardBackVariant; do not scatter card-back styles elsewhere.
 */

interface CardBackBaseProps {
  children: React.ReactNode;
  /** Optional extra class for the outer wrapper (e.g. for flip transform). */
  className?: string;
}

export function CardBackBase({ children, className = '' }: CardBackBaseProps) {
  return (
    <div
      className={`rounded-card shadow-card overflow-hidden ${className}`.trim()}
      style={{
        backfaceVisibility: 'hidden',
        WebkitBackfaceVisibility: 'hidden',
      }}
    >
      {children}
    </div>
  );
}
