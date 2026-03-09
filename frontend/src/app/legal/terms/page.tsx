'use client';

import Link from 'next/link';
import { ArrowLeft, FileText } from 'lucide-react';
import { GlassCard } from '@/components/haven/GlassCard';

export default function LegalTermsPage() {
  return (
    <div className="min-h-screen bg-auth-gradient py-10 px-4 relative overflow-hidden">
      {/* Decorative orb */}
      <div className="absolute bottom-20 left-10 w-48 h-48 rounded-full bg-accent/4 blur-hero-orb animate-float-delayed pointer-events-none" aria-hidden />

      <GlassCard className="max-w-2xl mx-auto p-8 md:p-10 relative overflow-hidden animate-page-enter">
        <div className="absolute top-0 inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-primary/25 to-transparent" aria-hidden />

        {/* Header */}
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 rounded-xl bg-gradient-to-br from-primary/15 to-primary/5 border border-primary/10" aria-hidden>
            <FileText className="w-5 h-5 text-primary" />
          </div>
          <p className="text-caption text-muted-foreground/70 font-medium tracking-wide">版本 1.0.0 · 最後更新 2026-02-19</p>
        </div>
        <h1 className="text-display font-art font-bold text-card-foreground tracking-tight mb-8">Haven 服務條款</h1>

        <div className="prose prose-sm text-card-foreground/90 space-y-6 leading-relaxed">

          <section>
            <h2 className="text-lg font-art font-semibold text-card-foreground mt-8 mb-3">1. 服務說明</h2>
            <p>
              Haven 是一款伴侶關係健康應用程式，提供日記撰寫與情緒記錄、伴侶卡牌互動遊戲、AI 情緒分析與關係洞察、以及伴侶配對與通知系統等核心功能。本服務旨在促進伴侶間的溝通與理解，但不替代專業心理諮詢或治療。
            </p>
          </section>

          <div className="divider-fade" />

          <section>
            <h2 className="text-lg font-art font-semibold text-card-foreground mb-3">2. 帳號與使用</h2>
            <p>您須提供有效的電子郵件地址註冊帳號，並應提供正確資料、妥善保管帳號與密碼。每個電子郵件地址僅能註冊一個帳號，您對帳號內所有活動負責。</p>
          </section>

          <div className="divider-fade" />

          <section>
            <h2 className="text-lg font-art font-semibold text-card-foreground mb-3">3. 年齡限制</h2>
            <p>
              您必須年滿 <strong>18 歲</strong>（或您所在司法管轄區之法定成年年齡）始得使用本服務。註冊時須確認年齡資格並同意本服務條款。部分內容可能涉及親密或敏感話題，僅供成年使用者於知情同意下使用。
            </p>
          </section>

          <div className="divider-fade" />

          <section>
            <h2 className="text-lg font-art font-semibold text-card-foreground mb-3">4. 使用規範</h2>
            <p>使用本服務時，您同意不得利用本服務從事違法、騷擾、濫用或侵害他人權益之行為；不得傳播不實、誤導、仇恨或暴力內容；不得嘗試規避安全機制、速率限制或存取控制。</p>
          </section>

          <div className="divider-fade" />

          <section>
            <h2 className="text-lg font-art font-semibold text-card-foreground mb-3">5. 智慧財產</h2>
            <p>本服務之產品內容、設計與程式碼之智慧財產權屬於 Haven 或其授權人。您對自身上傳之內容保留所有權利，並授權我們於提供與改善服務所需範圍內使用。</p>
          </section>

          <div className="divider-fade" />

          <section>
            <h2 className="text-lg font-art font-semibold text-card-foreground mb-3">6. 免責聲明</h2>
            <p>本服務依「現狀」提供。在法律允許之最大範圍內，我們不對因使用本服務所生之間接、衍生或懲罰性損害負責。我們不保證服務永遠可用、不中斷或無錯誤。</p>
          </section>

          <div className="divider-fade" />

          <section>
            <h2 className="text-lg font-art font-semibold text-card-foreground mb-3">7. AI 功能限制</h2>
            <p>
              AI 分析與建議僅供參考，<strong>不構成專業醫療、心理諮詢或法律建議</strong>。AI 模型可能產生不準確或不適當之內容。若您遇到心理健康困境，請尋求專業協助。
            </p>
          </section>

          <div className="divider-fade" />

          <section>
            <h2 className="text-lg font-art font-semibold text-card-foreground mb-3">8. 隱私保護</h2>
            <p>
              我們重視您的隱私，詳細資料處理方式請參閱{' '}
              <Link href="/legal/privacy" className="text-primary hover:text-primary/80 underline underline-offset-2 transition-colors duration-haven ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background">隱私權政策</Link>。
              您的資料不會被販售予第三方，且您享有查閱、匯出與刪除個人資料之權利。
            </p>
          </section>

          <div className="divider-fade" />

          <section>
            <h2 className="text-lg font-art font-semibold text-card-foreground mb-3">9. 服務終止</h2>
            <p>您可隨時請求刪除帳號與資料。我們得於違反條款或法律時暫停或終止您的存取。終止後，您的資料將依資料保留政策處理。</p>
          </section>

          <div className="divider-fade" />

          <section>
            <h2 className="text-lg font-art font-semibold text-card-foreground mb-3">10. 準據法與爭議解決</h2>
            <p>本條款以中華民國法律為準據法。爭議應先以善意協商解決；如協商未果，由台灣台北地方法院為第一審管轄法院。</p>
          </section>

          <div className="divider-fade" />

          <section>
            <h2 className="text-lg font-art font-semibold text-card-foreground mb-3">11. 條款修訂</h2>
            <p>我們保留修訂本條款之權利。重大變更將透過應用內通知或電子郵件事先告知。修訂後繼續使用本服務即視為同意新條款。</p>
          </section>

        </div>

        <div className="mt-10 pt-5 border-t border-border/40 flex items-center justify-between">
          <p className="text-caption text-muted-foreground/60">
            完整條款以 <code className="bg-muted/50 px-1.5 py-0.5 rounded-md text-caption">docs/legal/TERMS_OF_SERVICE.md</code> 為準。
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
