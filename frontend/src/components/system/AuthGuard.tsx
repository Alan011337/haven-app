'use client';

import { useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/use-auth';

/** Paths that do not require login. All other routes redirect to /login when not authenticated. */
const PUBLIC_PATHS = new Set([
  '/login',
  '/register',
  '/legal/privacy',
  '/legal/terms',
]);

function isPublicPath(pathname: string | null): boolean {
  if (!pathname) return true;
  if (PUBLIC_PATHS.has(pathname)) return true;
  if (pathname.startsWith('/legal/')) return true;
  return false;
}

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, isLoading } = useAuth();

  useEffect(() => {
    if (isLoading) return;
    if (user) return;
    if (isPublicPath(pathname)) return;

    const loginUrl = pathname
      ? `/login?redirect=${encodeURIComponent(pathname)}`
      : '/login';
    router.replace(loginUrl);
  }, [isLoading, user, router, pathname]);

  if (!isLoading && !user && !isPublicPath(pathname)) {
    return null;
  }

  return <>{children}</>;
}
