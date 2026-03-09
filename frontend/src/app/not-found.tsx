// frontend/src/app/not-found.tsx — App Router not-found UI (Haven tokens only)

import Link from 'next/link';
import { Home, Search } from 'lucide-react';
import { GlassCard } from '@/components/haven/GlassCard';

export default function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-auth-gradient px-4 relative overflow-hidden">
      {/* Decorative orbs */}
      <div className="absolute top-1/3 right-1/4 w-56 h-56 rounded-full bg-primary/5 blur-hero-orb animate-float pointer-events-none" aria-hidden />
      <div className="absolute bottom-1/3 left-1/3 w-40 h-40 rounded-full bg-accent/5 blur-hero-orb-sm animate-float-delayed pointer-events-none" aria-hidden />

      <GlassCard className="w-full max-w-md p-10 text-center animate-scale-in relative">
        <div className="absolute top-0 inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-primary/25 to-transparent" aria-hidden />

        <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/15 to-primary/5 ring-4 ring-primary/10" aria-hidden>
          <Search className="h-7 w-7 text-primary" />
        </div>
        <p className="mb-2 text-caption font-semibold tracking-[0.2em] text-muted-foreground uppercase">404</p>
        <h1 className="mb-3 text-title font-art font-bold text-card-foreground tracking-tight">
          找不到頁面
        </h1>
        <p className="mb-8 text-body text-muted-foreground leading-relaxed">
          您造訪的頁面不存在或已被移除。
        </p>
        <Link
          href="/"
          className="w-full inline-flex items-center justify-center gap-2 rounded-button bg-gradient-to-b from-primary to-primary/90 border-t border-t-white/30 px-5 py-3 text-sm font-semibold text-primary-foreground shadow-satin-button transition-all duration-haven ease-haven hover:shadow-lift hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background active:scale-[0.98]"
        >
          <Home className="w-4 h-4" />
          回到首頁
        </Link>
      </GlassCard>
    </div>
  );
}
