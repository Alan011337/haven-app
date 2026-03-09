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

export default function Sidebar() {
  const pathname = usePathname();
  const { logout } = useAuth();
  const { confirm } = useConfirm();
  const { showToast } = useToast();
  const { data: partnerStatus, refetch: refetchPartnerStatus } = usePartnerStatus();
  const unreadNotificationCount = Number(partnerStatus?.unread_notification_count ?? 0);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [upgradeLoading, setUpgradeLoading] = useState(false);

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | null = null;
    let active = true;
    const poll = async () => {
      if (!active) return;
      try {
        await refetchPartnerStatus();
      } finally {
        const nextInterval = getAdaptiveIntervalMs(30_000, { hiddenMultiplier: 4 });
        timer = setTimeout(poll, nextInterval === false ? 5_000 : nextInterval);
      }
    };
    void poll();
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
          relative flex items-center justify-between px-4 py-3.5 rounded-button transition-all duration-haven ease-haven group
          ${isActive ? 'bg-primary/10 text-primary font-bold shadow-soft' : 'text-muted-foreground hover:bg-primary/5 hover:text-card-foreground'}
          ${staggerStyle ? 'animate-slide-up-fade' : ''}
        `}
      >
        {isActive && (
          <span className="absolute left-0 top-2 bottom-2 w-0.5 rounded-full bg-primary" aria-hidden />
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
      {/* Logo area with refined typography */}
      <div className="p-8 pb-6">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="absolute inset-0 bg-primary/20 rounded-2xl blur-lg animate-breathe" aria-hidden />
            <div className="relative w-10 h-10 rounded-2xl bg-gradient-to-br from-primary to-primary/80 flex items-center justify-center shadow-soft">
              <Heart className="w-5 h-5 text-primary-foreground fill-primary-foreground" />
            </div>
          </div>
          <div>
            <h1 className="text-xl font-art font-bold text-gradient-gold tracking-tight">
              Haven
            </h1>
            <p className="text-[10px] text-muted-foreground font-medium tracking-[0.2em] uppercase">Couple Journal</p>
          </div>
        </div>
      </div>

      <div className="px-6 mb-4">
        <div className="section-divider" />
      </div>

      <nav className="flex-1 px-4 space-y-1 overflow-y-auto">
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

      <div className="p-4 mx-4 mb-4">
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

  return (
    <>
      {/* Desktop sidebar: visible from md up */}
      <GlassPanel as="aside" variant="sidebar" className="hidden md:flex fixed left-0 top-0 h-screen w-64 flex-col z-50 transition-transform duration-haven ease-haven">
        {renderNavContent()}
      </GlassPanel>

      {/* Mobile: top bar with hamburger */}
      <header
        className="md:hidden fixed top-0 left-0 right-0 h-14 z-50 bg-card/80 backdrop-blur-xl border-b border-border/50 flex items-center justify-between px-4"
        aria-label="頂部導航"
      >
        <div className="flex items-center gap-2.5">
          <div className="relative">
            <div className="absolute inset-0 bg-primary/15 rounded-xl blur-md" aria-hidden />
            <div className="relative w-8 h-8 rounded-xl bg-gradient-to-br from-primary to-primary/80 flex items-center justify-center shadow-soft">
              <Heart className="w-4 h-4 text-primary-foreground fill-primary-foreground" />
            </div>
          </div>
          <span className="text-lg font-art font-bold text-gradient-gold">
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
