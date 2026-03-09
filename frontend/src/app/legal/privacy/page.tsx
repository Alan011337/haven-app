'use client';

import Link from 'next/link';
import { ArrowLeft, Shield } from 'lucide-react';
import { GlassCard } from '@/components/haven/GlassCard';

export default function LegalPrivacyPage() {
  return (
    <div className="min-h-screen bg-auth-gradient py-10 px-4 relative overflow-hidden">
      {/* Decorative orb */}
      <div className="absolute top-20 right-10 w-48 h-48 rounded-full bg-primary/4 blur-hero-orb animate-float pointer-events-none" aria-hidden />

      <GlassCard className="max-w-2xl mx-auto p-8 md:p-10 relative overflow-hidden animate-page-enter">
        <div className="absolute top-0 inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-primary/25 to-transparent" aria-hidden />

        {/* Header */}
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 rounded-xl bg-gradient-to-br from-primary/15 to-primary/5 border border-primary/10" aria-hidden>
            <Shield className="w-5 h-5 text-primary" />
          </div>
          <p className="text-caption text-muted-foreground/70 font-medium tracking-wide">版本 1.0.0 · 最後更新 2026-02-19</p>
        </div>
        <h1 className="text-display font-art font-bold text-card-foreground tracking-tight mb-8">Haven 隱私權政策</h1>

        <div className="prose prose-sm text-card-foreground/90 space-y-6 leading-relaxed">

          <section>
            <h2 className="text-lg font-art font-semibold text-card-foreground mt-8 mb-3">1. 適用範圍</h2>
            <p>本政策適用於 Haven 產品與服務所蒐集、使用、儲存之個人資料。使用本服務即表示您已閱讀並同意本隱私權政策。</p>
          </section>

          <div className="divider-fade" />

          <section>
            <h2 className="text-lg font-art font-semibold text-card-foreground mb-3">2. 資料收集範圍</h2>
            <p>我們蒐集以下類型之資料：</p>
            <ul className="list-disc pl-5 space-y-1.5 mt-2 marker:text-primary/40">
              <li><strong>帳號資訊</strong>：電子郵件、暱稱、密碼（經雜湊儲存）。</li>
              <li><strong>年齡確認</strong>：出生年（選填），用於確保符合年齡限制。</li>
              <li><strong>使用資料</strong>：日記內容、卡片回答、配對關係、通知紀錄。</li>
              <li><strong>AI 分析資料</strong>：AI 產生之情緒分析與建議。</li>
              <li><strong>技術資料</strong>：IP 位址、連線紀錄、裝置識別，用於安全防護與限流。</li>
              <li><strong>同意紀錄</strong>：同意類型、政策版本、同意時間，用於合規與稽核。</li>
            </ul>
          </section>

          <div className="divider-fade" />

          <section>
            <h2 className="text-lg font-art font-semibold text-card-foreground mb-3">3. 資料使用方式</h2>
            <ul className="list-disc pl-5 space-y-1.5 mt-2 marker:text-primary/40">
              <li>提供註冊、登入、配對、日記、卡牌互動與通知等核心功能。</li>
              <li>使用您的日記與回答內容進行 AI 情緒分析與互動建議。</li>
              <li>透過速率限制、稽核紀錄與濫用偵測保護您的帳號安全。</li>
              <li>以匿名化或統計方式分析使用模式，改善產品體驗。</li>
              <li>依法律要求或經您同意之其他目的。</li>
            </ul>
          </section>

          <div className="divider-fade" />

          <section>
            <h2 className="text-lg font-art font-semibold text-card-foreground mb-3">4. 資料儲存與安全</h2>
            <ul className="list-disc pl-5 space-y-1.5 mt-2 marker:text-primary/40">
              <li>資料儲存於經選定之雲端服務（如 Supabase / PostgreSQL）。</li>
              <li>密碼採用單向雜湊儲存，我們無法還原您的明文密碼。</li>
              <li>傳輸過程使用 HTTPS / TLS 加密。</li>
              <li>採取合理技術與組織措施保護個人資料。</li>
            </ul>
          </section>

          <div className="divider-fade" />

          <section>
            <h2 className="text-lg font-art font-semibold text-card-foreground mb-3">5. 第三方服務</h2>
            <p>我們不販售您的個人資料。僅在以下情況與第三方分享：</p>
            <ul className="list-disc pl-5 space-y-1.5 mt-2 marker:text-primary/40">
              <li><strong>AI 分析</strong>：傳送至 AI 服務提供者進行分析，不包含帳號識別資訊。</li>
              <li><strong>通知郵件</strong>：透過郵件服務供應商寄送通知。</li>
              <li><strong>法律要求</strong>：依法律、法院命令或政府機關合法要求。</li>
            </ul>
          </section>

          <div className="divider-fade" />

          <section>
            <h2 className="text-lg font-art font-semibold text-card-foreground mb-3">6. 使用者權利</h2>
            <div className="space-y-4 mt-2">
              <div className="pl-4 border-l-2 border-primary/20">
                <h3 className="font-medium text-card-foreground">查閱與攜出（Access / Export）</h3>
                <p className="mt-1">您可透過應用內設定匯出完整資料包，包含帳號資訊、日記、AI 分析、卡片回答與通知紀錄。</p>
              </div>
              <div className="pl-4 border-l-2 border-primary/20">
                <h3 className="font-medium text-card-foreground">刪除（Erase）</h3>
                <p className="mt-1">您可透過應用內設定請求刪除帳號與全部資料。</p>
              </div>
              <div className="pl-4 border-l-2 border-primary/20">
                <h3 className="font-medium text-card-foreground">更正</h3>
                <p className="mt-1">您可於應用內更新暱稱等個人資料。</p>
              </div>
              <div className="pl-4 border-l-2 border-primary/20">
                <h3 className="font-medium text-card-foreground">同意紀錄查詢</h3>
                <p className="mt-1">您可查詢您的同意紀錄，了解您已同意的服務條款與政策版本。</p>
              </div>
            </div>
          </section>

          <div className="divider-fade" />

          <section>
            <h2 className="text-lg font-art font-semibold text-card-foreground mb-3">7. AI 功能使用</h2>
            <ul className="list-disc pl-5 space-y-1.5 mt-2 marker:text-primary/40">
              <li>Haven 使用 AI 技術分析您的日記與互動內容，提供情緒洞察與關係建議。</li>
              <li><strong>AI 產生的內容僅供參考，不構成專業醫療、心理或法律建議。</strong></li>
              <li>AI 分析資料的傳送不包含直接識別您身份的帳號資訊。</li>
              <li>您可隨時透過同意管理功能撤銷 AI 分析之同意。</li>
            </ul>
          </section>

          <div className="divider-fade" />

          <section>
            <h2 className="text-lg font-art font-semibold text-card-foreground mb-3">8. 聯絡方式</h2>
            <p>若對本政策有疑問或欲行使您的資料權利，請透過產品內「設定」頁面或電子郵件與我們聯繫。</p>
          </section>

        </div>

        <div className="mt-10 pt-5 border-t border-border/40 flex items-center justify-between">
          <p className="text-caption text-muted-foreground/60">
            完整政策以 <code className="bg-muted/50 px-1.5 py-0.5 rounded-md text-caption">docs/legal/PRIVACY_POLICY.md</code> 為準。
          </p>
          <Link
            href="/register"
            className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:text-primary/80 transition-colors duration-haven ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            返回註冊
          </Link>
        </div>
      </GlassCard>
    </div>
  );
}
