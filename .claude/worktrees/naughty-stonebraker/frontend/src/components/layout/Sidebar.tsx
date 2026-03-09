// frontend/src/components/layout/Sidebar.tsx

"use client";

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { Home, Library, Settings, LogOut, Heart, BarChart2, Bell } from 'lucide-react'; 
import { useConfirm } from '@/contexts/ConfirmContext';
import { useToast } from '@/contexts/ToastContext';
import { fetchPartnerStatus } from '@/services/api-client';

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { confirm } = useConfirm();
  const { showToast } = useToast();
  const [unreadNotificationCount, setUnreadNotificationCount] = useState(0);

  const loadNotificationCount = useCallback(async () => {
    if (typeof window === 'undefined') return;
    const token = localStorage.getItem('token');
    if (!token) {
      setUnreadNotificationCount(0);
      return;
    }

    try {
      const status = await fetchPartnerStatus();
      setUnreadNotificationCount(Number(status.unread_notification_count || 0));
    } catch (error) {
      console.warn('讀取通知數量失敗', error);
    }
  }, []);

  useEffect(() => {
    const kickoff = setTimeout(() => {
      void loadNotificationCount();
    }, 0);
    const timer = setInterval(() => {
      void loadNotificationCount();
    }, 30000);
    return () => {
      clearTimeout(kickoff);
      clearInterval(timer);
    };
  }, [loadNotificationCount]);

  const handleLogout = async () => {
    const shouldLogout = await confirm({
      title: '登出',
      message: '確定要登出嗎？',
      confirmText: '登出',
      cancelText: '取消',
    });
    if (shouldLogout) {
      localStorage.removeItem('token');
      showToast('已登出', 'info');
      router.push('/login');
    }
  };

  const navItems = [
    { name: '首頁', href: '/', icon: Home },
    { name: '牌組圖書館', href: '/decks', icon: Library }, 
    { name: '通知中心', href: '/notifications', icon: Bell },
    { name: '情緒分析', href: '/analysis', icon: BarChart2, badge: 'Coming Soon' }, 
    { name: '伴侶連結 / 設定', href: '/settings', icon: Settings },
  ];

  // 👇 修正重點：
  // 原本是 "hidden md:flex" (預設隱藏)，導致你看不到側邊欄。
  // 現在改為 "flex" (永遠顯示)，並加上 "z-50" 確保它浮在最上層。
  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-white border-r border-gray-100 flex flex-col z-50 transition-transform duration-300">
      {/* 1. Logo */}
      <div className="p-8 pb-4">
        <h1 className="text-2xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent flex items-center gap-2">
          <Heart className="w-6 h-6 text-pink-500 fill-pink-500" />
          Haven
        </h1>
        <p className="text-xs text-gray-400 mt-2 font-medium tracking-wider">COUPLE JOURNAL</p>
      </div>

      {/* 2. 導航選單 */}
      <nav className="flex-1 px-4 space-y-2 mt-4">
        {navItems.map((item) => {
          const isActive = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href));
          const isNotificationTab = item.href === '/notifications';
          const notificationBadgeCount = isNotificationTab ? unreadNotificationCount : 0;
          
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`
                flex items-center justify-between px-4 py-3.5 rounded-xl transition-all duration-200 group
                ${isActive 
                  ? 'bg-indigo-50 text-indigo-600 font-bold shadow-sm' 
                  : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900'}
              `}
            >
              <div className="flex items-center gap-3">
                <item.icon className={`w-5 h-5 ${isActive ? 'text-indigo-600' : 'text-gray-400 group-hover:text-gray-600'}`} />
                {item.name}
              </div>
              
              {notificationBadgeCount > 0 && (
                <span className="text-[10px] bg-rose-500 text-white px-2 py-0.5 rounded-full whitespace-nowrap min-w-[22px] text-center">
                  {notificationBadgeCount > 99 ? '99+' : notificationBadgeCount}
                </span>
              )}

              {item.badge && notificationBadgeCount <= 0 && (
                <span className="text-[10px] bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full whitespace-nowrap">
                  {item.badge}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* 3. 底部登出區 */}
      <div className="p-4 border-t border-gray-100">
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 w-full px-4 py-3 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-xl transition-all duration-200 text-sm font-medium"
        >
          <LogOut className="w-5 h-5" />
          登出
        </button>
      </div>
    </aside>
  );
}
