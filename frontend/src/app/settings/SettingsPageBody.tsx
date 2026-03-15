'use client';

import Link from 'next/link';
import type { LucideIcon } from 'lucide-react';
import { Shield, Target, Heart, ShieldAlert, BarChart2, ShieldCheck } from 'lucide-react';
import PartnerSettings from '@/components/features/PartnerSettings';
import OnboardingConsentCard from '@/components/features/OnboardingConsentCard';
import RelationshipRadarCard from '@/components/features/RelationshipRadarCard';
import CooldownSOSCard from '@/components/features/CooldownSOSCard';
import WeeklyReportCard from '@/components/features/WeeklyReportCard';

function SectionHeader({ icon: Icon, title }: { icon: LucideIcon; title: string }) {
  return (
    <div className="mb-4 flex items-center gap-3">
      <Icon className="h-5 w-5 text-primary/60" aria-hidden />
      <h2 className="font-art text-lg font-medium text-card-foreground">{title}</h2>
    </div>
  );
}

export default function SettingsPageBody() {
  return (
    <>
      <div className="animate-slide-up-fade-1">
        <SectionHeader icon={Shield} title="隱私與 AI" />
        <OnboardingConsentCard mode="settings" />
      </div>

      <div className="animate-slide-up-fade-1">
        <SectionHeader icon={Target} title="關係雷達" />
        <RelationshipRadarCard />
      </div>

      <div className="animate-slide-up-fade-2">
        <SectionHeader icon={Heart} title="伴侶連結" />
        <PartnerSettings />
      </div>

      <div className="animate-slide-up-fade-2">
        <SectionHeader icon={ShieldAlert} title="冷靜空間" />
        <CooldownSOSCard />
      </div>

      <div className="animate-slide-up-fade-3">
        <SectionHeader icon={BarChart2} title="每週回顧" />
        <WeeklyReportCard />
      </div>

      {/* Footer */}
      <div className="animate-slide-up-fade-3">
        <div className="section-divider mb-4" />
        <p className="type-caption leading-relaxed text-muted-foreground/80">
          您可隨時匯出或刪除自己的資料；若需伴侶一併刪除，請伴侶登入後於設定中執行刪除。
        </p>
        <Link
          href="/admin/moderation"
          className="mt-3 inline-flex items-center gap-[var(--space-inline)] type-caption text-muted-foreground transition-colors duration-haven ease-haven hover:text-primary"
        >
          <span className="icon-badge !h-6 !w-6" aria-hidden>
            <ShieldCheck className="h-3 w-3" />
          </span>
          內容審核（管理員）
        </Link>
      </div>
    </>
  );
}
