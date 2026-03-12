// frontend/src/components/layout/Sidebar.tsx

"use client";

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Home, Library, Settings, LogOut, Heart, BarChart2, Bell, Menu, X, Sparkles, BookMarked, HandHeart, ListTodo } from 'lucide-react';
import { GlassPanel } from '@/components/haven/GlassPanel';
import { useConfirm } from '@/hooks/useConfirm';
import { useToast } from '@/hooks/useToast';
import { useAuth } from '@/hooks/use-auth';
import { usePartnerStatus } from '@/hooks/queries';
import { getAdaptiveIntervalMs } from '@/lib/polling-policy';
import { logClientError } from '@/lib/safe-error-log';
import { createCheckoutSession } from '@/services/api-client';

interface SidebarProps {
  variant?: 'default' | 'home';
}

export default function Sidebar({ variant = 'default' }: SidebarProps) {
  const pathname = usePathname();
  const { logout } = useAuth();
  const { confirm } = useConfirm();
  const { showToast } = useToast();
  const { data: partnerStatus, refetch: refetchPartnerStatus } = usePartnerStatus();
  const unreadNotificationCount = Number(partnerStatus?.unread_notification_count ?? 0);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [upgradeLoading, setUpgradeLoading] = useState(false);
  const isHomeVariant = variant === 'home';

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | null = null;
    let active = true;
    const scheduleNextPoll = () => {
      const nextInterval = getAdaptiveIntervalMs(30_000, { hiddenMultiplier: 4 });
      timer = setTimeout(poll, nextInterval === false ? 5_000 : nextInterval);
    };
    const poll = async () => {
      if (!active) return;
      try {
        await refetchPartnerStatus();
      } finally {
        scheduleNextPoll();
      }
    };
    scheduleNextPoll();
    return () => {
      active = false;
      if (timer) clearTimeout(timer);
    };
  }, [refetchPartnerStatus]);

  const handleLogout = async () => {
    const shouldLogout = await confirm({
      title: '登出',
      message: '確定要登出嗎？',
      confirmText: '登出',
      cancelText: '取消',
    });
    if (shouldLogout) {
      logout();
      showToast('已登出', 'info');
    }
  };

  const handleUpgrade = useCallback(async () => {
    if (upgradeLoading) return;
    setUpgradeLoading(true);
    try {
      const { url } = await createCheckoutSession();
      if (url) {
        window.location.href = url;
        return;
      }
    } catch (error) {
      logClientError('sidebar-create-checkout-failed', error);
      showToast('無法開啟付費頁面，請稍後再試。', 'error');
    } finally {
      setUpgradeLoading(false);
    }
  }, [upgradeLoading, showToast]);

  const navItems = [
    { name: '首頁', href: '/', icon: Home },
    { name: '牌組圖書館', href: '/decks', icon: Library },
    { name: '愛情地圖', href: '/love-map', icon: Heart },
    { name: '調解模式', href: '/mediation', icon: HandHeart },
    { name: '藍圖與願望', href: '/blueprint', icon: ListTodo },
    { name: '回憶長廊', href: '/memory', icon: BookMarked },
    { name: '通知中心', href: '/notifications', icon: Bell },
    { name: '情緒分析', href: '/analysis', icon: BarChart2, badge: 'Coming Soon' },
    { name: '伴侶連結 / 設定', href: '/settings', icon: Settings },
  ];

  const upgradeNavItem = { name: '升級方案', icon: Sparkles, isUpgrade: true as const };

  const renderHomeRailLink = (item: (typeof navItems)[number]) => {
    const isActive = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href));
    const isNotificationTab = item.href === '/notifications';
    const notificationBadgeCount = isNotificationTab ? unreadNotificationCount : 0;
    return (
      <Link
        key={item.href}
        href={item.href}
        className={`
          group relative flex h-12 w-12 items-center justify-center rounded-[1.35rem] border transition-all duration-haven ease-haven
          ${isActive ? 'border-primary/15 bg-white/82 text-card-foreground shadow-soft' : 'border-transparent bg-white/38 text-muted-foreground hover:border-primary/10 hover:bg-white/72 hover:text-card-foreground'}
        `}
        aria-label={item.name}
      >
        <item.icon className={`h-[18px] w-[18px] ${isActive ? 'text-primary' : ''}`} />
        {notificationBadgeCount > 0 ? (
          <span className="absolute -right-1 -top-1 min-w-[20px] rounded-full bg-destructive px-1.5 py-0.5 text-center text-[10px] font-semibold text-destructive-foreground shadow-soft">
            {notificationBadgeCount > 99 ? '99+' : notificationBadgeCount}
          </span>
        ) : null}
        <span
          className={`
            pointer-events-none absolute left-[calc(100%+0.85rem)] top-1/2 -translate-y-1/2 whitespace-nowrap rounded-full border border-white/50 bg-white/90 px-3 py-1.5 text-xs font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven
            ${isActive ? 'opacity-100 translate-x-0' : 'translate-x-1 opacity-0 group-hover:translate-x-0 group-hover:opacity-100'}
          `}
        >
          {item.name}
        </span>
      </Link>
    );
  };

  const renderNavLink = (item: (typeof navItems)[number], onNavClick?: () => void, index?: number) => {
    const isActive = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href));
    const isNotificationTab = item.href === '/notifications';
    const notificationBadgeCount = isNotificationTab ? unreadNotificationCount : 0;
    const staggerStyle = typeof index === 'number' ? { animationDelay: `${index * 40}ms` } : undefined;
    return (
      <Link
        key={item.href}
        href={item.href}
        onClick={onNavClick}
        style={staggerStyle}
        className={`
          relative flex items-center justify-between rounded-[1.3rem] transition-all duration-haven ease-haven group border
          ${isHomeVariant ? 'px-3.5 py-3' : 'px-4 py-3.5'}
          ${isActive ? 'border-primary/15 bg-white/78 text-card-foreground font-semibold shadow-soft' : 'border-transparent text-muted-foreground hover:border-primary/10 hover:bg-white/52 hover:text-card-foreground'}
          ${staggerStyle ? 'animate-slide-up-fade' : ''}
        `}
      >
        {isActive && (
          <span className="absolute left-0 top-3 bottom-3 w-0.5 rounded-full bg-primary" aria-hidden />
        )}
        <div className="flex items-center gap-3">
          <span className={isActive ? 'icon-badge animate-glow-pulse' : ''}>
            <item.icon className={`w-5 h-5 ${isActive ? 'text-primary' : 'text-muted-foreground group-hover:text-card-foreground'}`} />
          </span>
          {item.name}
        </div>
        {notificationBadgeCount > 0 && (
          <span className="text-[10px] bg-destructive text-destructive-foreground px-2 py-0.5 rounded-full whitespace-nowrap min-w-[22px] text-center font-semibold">
            {notificationBadgeCount > 99 ? '99+' : notificationBadgeCount}
          </span>
        )}
        {item.badge && notificationBadgeCount <= 0 && (
          <span className="text-[10px] bg-muted text-foreground px-2 py-0.5 rounded-full whitespace-nowrap font-medium">
            {item.badge}
          </span>
        )}
      </Link>
    );
  };

  const renderNavContent = (closeDrawer?: () => void) => (
    <>
      <div className={isHomeVariant ? 'p-6 pb-5' : 'p-8 pb-6'}>
        <div className={`rounded-[1.8rem] border border-white/45 bg-white/68 shadow-soft backdrop-blur-xl ${isHomeVariant ? 'p-4' : 'p-5'}`}>
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className="absolute inset-0 bg-primary/18 rounded-2xl blur-lg animate-breathe" aria-hidden />
              <div className="relative w-10 h-10 rounded-2xl bg-gradient-to-br from-primary to-primary/80 flex items-center justify-center shadow-soft">
                <Heart className="w-5 h-5 text-primary-foreground fill-primary-foreground" />
              </div>
            </div>
            <div>
              <h1 className="text-xl font-art font-bold text-gradient-gold tracking-tight">
                Haven
              </h1>
              <p className="text-[10px] text-muted-foreground font-medium tracking-[0.2em] uppercase">
                {isHomeVariant ? 'Home Edition' : 'Couple Journal'}
              </p>
              <p className="mt-2 text-xs leading-6 text-muted-foreground">
                {isHomeVariant
                  ? '首頁這一版刻意放低導航音量，讓內容區成為主舞台。'
                  : '首頁現在先服務你們今天真正重要的情緒與儀式。'}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className={isHomeVariant ? 'px-5 mb-3' : 'px-6 mb-4'}>
        <div className="section-divider" />
      </div>

      <nav className={`flex-1 overflow-y-auto ${isHomeVariant ? 'px-3.5 space-y-1.5' : 'px-4 space-y-1'}`}>
        {navItems.map((item, i) => renderNavLink(item, closeDrawer, closeDrawer ? i : undefined))}

        <div className="px-2 pt-3 pb-1">
          <div className="section-divider" />
        </div>

        <button
          type="button"
          onClick={() => {
            void handleUpgrade();
            closeDrawer?.();
          }}
          disabled={upgradeLoading}
          className="flex items-center gap-3 w-full px-4 py-3 rounded-button transition-all duration-haven ease-haven text-muted-foreground hover:text-primary group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background relative overflow-hidden"
        >
          <div className="absolute inset-0 bg-gradient-to-r from-primary/5 to-primary/10 opacity-0 group-hover:opacity-100 transition-opacity duration-haven ease-haven rounded-button" aria-hidden />
          <upgradeNavItem.icon className="w-5 h-5 text-muted-foreground group-hover:text-primary transition-colors duration-haven ease-haven relative" />
          <span className="relative">{upgradeNavItem.name}</span>
          {upgradeLoading && <span className="text-xs text-muted-foreground relative">載入中…</span>}
        </button>
      </nav>

      <div className={isHomeVariant ? 'p-4 mx-3.5 mb-4' : 'p-4 mx-4 mb-4'}>
        <div className="section-divider mb-4" />
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 w-full px-4 py-2.5 text-muted-foreground hover:text-destructive hover:bg-destructive/5 rounded-button transition-all duration-haven ease-haven text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
        >
          <LogOut className="w-4 h-4" />
          登出
        </button>
      </div>
    </>
  );

  const renderHomeRail = () => (
    <>
      <div className="px-4 pb-4 pt-5">
        <div className="flex flex-col items-center gap-4">
          <div className="relative">
            <div className="absolute inset-0 rounded-[1.4rem] bg-primary/18 blur-md" aria-hidden />
            <div className="relative flex h-12 w-12 items-center justify-center rounded-[1.4rem] bg-gradient-to-br from-primary to-primary/80 shadow-soft">
              <Heart className="h-5 w-5 fill-primary-foreground text-primary-foreground" />
            </div>
          </div>
          <div className="rounded-full border border-white/50 bg-white/70 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.24em] text-primary/80 shadow-soft">
            Home
          </div>
        </div>
      </div>

      <div className="mx-4 mb-4 section-divider" />

      <nav className="flex flex-1 flex-col items-center gap-3 px-4">
        {navItems.map(renderHomeRailLink)}

        <div className="my-1 h-4 w-px rounded-full bg-gradient-to-b from-primary/20 to-transparent" aria-hidden />

        <button
          type="button"
          onClick={() => {
            void handleUpgrade();
          }}
          disabled={upgradeLoading}
          className="group relative flex h-12 w-12 items-center justify-center rounded-[1.35rem] border border-transparent bg-white/40 text-muted-foreground transition-all duration-haven ease-haven hover:border-primary/10 hover:bg-white/74 hover:text-card-foreground"
          aria-label={upgradeNavItem.name}
        >
          <upgradeNavItem.icon className="h-[18px] w-[18px]" />
          <span className="pointer-events-none absolute left-[calc(100%+0.85rem)] top-1/2 -translate-y-1/2 whitespace-nowrap rounded-full border border-white/50 bg-white/90 px-3 py-1.5 text-xs font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven translate-x-1 opacity-0 group-hover:translate-x-0 group-hover:opacity-100">
            {upgradeLoading ? '載入中…' : upgradeNavItem.name}
          </span>
        </button>
      </nav>

      <div className="mx-4 mb-4 mt-5 section-divider" />

      <div className="px-4 pb-5">
        <button
          onClick={handleLogout}
          className="group relative flex h-12 w-12 items-center justify-center rounded-[1.35rem] border border-transparent bg-white/34 text-muted-foreground transition-all duration-haven ease-haven hover:border-destructive/10 hover:bg-destructive/8 hover:text-destructive"
          aria-label="登出"
        >
          <LogOut className="h-[18px] w-[18px]" />
          <span className="pointer-events-none absolute left-[calc(100%+0.85rem)] top-1/2 -translate-y-1/2 whitespace-nowrap rounded-full border border-white/50 bg-white/90 px-3 py-1.5 text-xs font-medium text-card-foreground shadow-soft transition-all duration-haven ease-haven translate-x-1 opacity-0 group-hover:translate-x-0 group-hover:opacity-100">
            登出
          </span>
        </button>
      </div>
    </>
  );

  return (
    <>
      <GlassPanel
        as="aside"
        variant="sidebar"
        className={`hidden md:flex fixed flex-col z-50 transition-transform duration-haven ease-haven ${
          isHomeVariant
            ? 'left-5 top-5 h-[calc(100vh-2.5rem)] w-[88px] rounded-[2.4rem] border border-white/45 bg-[linear-gradient(180deg,rgba(255,251,246,0.62),rgba(249,244,237,0.44))] shadow-lift'
            : 'left-0 top-0 h-screen w-64 bg-[linear-gradient(180deg,rgba(255,251,246,0.82),rgba(249,244,237,0.72))]'
        }`}
      >
        {isHomeVariant ? renderHomeRail() : renderNavContent()}
      </GlassPanel>

      <header
        className={`md:hidden fixed left-0 right-0 z-50 flex items-center justify-between px-4 backdrop-blur-xl ${
          isHomeVariant
            ? 'top-3 mx-3 h-12 rounded-full border border-white/45 bg-[linear-gradient(180deg,rgba(255,252,248,0.82),rgba(248,243,237,0.68))] shadow-soft'
            : 'top-0 h-14 border-b border-border/50 bg-[linear-gradient(180deg,rgba(255,252,248,0.92),rgba(248,243,237,0.86))]'
        }`}
        aria-label="頂部導航"
      >
        <div className="flex items-center gap-2.5">
          <div className="relative">
            <div className="absolute inset-0 bg-primary/15 rounded-xl blur-md" aria-hidden />
            <div className="relative w-8 h-8 rounded-xl bg-gradient-to-br from-primary to-primary/80 flex items-center justify-center shadow-soft">
              <Heart className="w-4 h-4 text-primary-foreground fill-primary-foreground" />
            </div>
          </div>
          <span className={`${isHomeVariant ? 'text-base' : 'text-lg'} font-art font-bold text-gradient-gold`}>
            Haven
          </span>
        </div>
        <button
          type="button"
          onClick={() => setDrawerOpen(true)}
          className="p-2 rounded-button hover:bg-primary/5 text-muted-foreground hover:text-primary transition-colors duration-haven ease-haven"
          aria-label="開啟選單"
        >
          <Menu className="w-5 h-5" />
        </button>
      </header>

      {/* Mobile drawer overlay + panel */}
      {drawerOpen && (
        <div className="md:hidden fixed inset-0 z-[60]" role="dialog" aria-modal="true" aria-label="導航選單">
          <button
            type="button"
            onClick={() => setDrawerOpen(false)}
            className="absolute inset-0 bg-black/40 backdrop-blur-sm"
            aria-label="關閉選單"
          />
          <div className="absolute left-0 top-0 h-full w-64 bg-card/95 backdrop-blur-2xl border-r border-border/30 shadow-modal flex flex-col animate-in slide-in-from-left duration-300">
            <div className="absolute top-4 right-4 z-10">
              <button
                type="button"
                onClick={() => setDrawerOpen(false)}
                className="p-2 rounded-button hover:bg-primary/5 text-muted-foreground hover:text-primary transition-colors duration-haven ease-haven"
                aria-label="關閉選單"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            {renderNavContent(() => setDrawerOpen(false))}
          </div>
        </div>
      )}
    </>
  );
}
