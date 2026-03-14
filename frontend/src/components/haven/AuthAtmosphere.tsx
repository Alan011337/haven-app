import type { ReactNode } from 'react';

interface AuthAtmosphereProps {
  headingId: string;
  brandLine: string;
  children: ReactNode;
}

export function AuthAtmosphere({
  headingId,
  brandLine,
  children,
}: AuthAtmosphereProps) {
  return (
    <div className="relative min-h-screen overflow-hidden bg-auth-gradient">
      {/* Decorative orbs */}
      <div
        className="pointer-events-none absolute left-[12%] top-[18%] h-64 w-64 rounded-full bg-primary/10 blur-hero-orb animate-float"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute bottom-[15%] right-[8%] h-48 w-48 rounded-full bg-accent/12 blur-hero-orb-sm animate-float-delayed"
        aria-hidden
      />

      {/* Content column — vertically + horizontally centered */}
      <div className="relative z-10 mx-auto flex min-h-screen w-full max-w-md flex-col items-center justify-center px-6 py-12 sm:py-16">
        {/* Brand mark zone */}
        <div className="mb-10 text-center sm:mb-14 animate-slide-up-fade">
          <h1 className="font-art text-5xl text-gradient-gold tracking-tight sm:text-6xl lg:text-7xl">
            Haven
          </h1>
          <p className="mt-4 font-art text-lg leading-relaxed text-foreground/70 sm:text-xl animate-slide-up-fade-1">
            {brandLine}
          </p>
        </div>

        {/* Form zone */}
        <div className="w-full surface-glass-panel p-7 sm:p-8 animate-slide-up-fade-2">
          <h2 id={headingId} className="sr-only">
            Haven 登入
          </h2>
          <div className="section-divider mb-6" />
          {children}
        </div>
      </div>
    </div>
  );
}
