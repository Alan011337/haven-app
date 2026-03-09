"use client";

import { useState, useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Timer, Loader2, Pause, Wind } from "lucide-react";
import { GlassCard } from "@/components/haven/GlassCard";
import Button from "@/components/ui/Button";
import { useCooldownStatus } from "@/hooks/queries";
import { queryKeys } from "@/lib/query-keys";
import { startCooldown, rewriteMessage } from "@/services/api-client";
import { logClientError } from "@/lib/safe-error-log";
import { useToast } from "@/hooks/useToast";

function formatRemaining(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export default function CooldownSOSCard() {
  const queryClient = useQueryClient();
  const { data: status, isLoading: loading, refetch } = useCooldownStatus();
  const [starting, setStarting] = useState(false);
  const [tickNow, setTickNow] = useState(Date.now());
  const [rewriteDraft, setRewriteDraft] = useState("");
  const [rewritten, setRewritten] = useState<string | null>(null);
  const [rewriting, setRewriting] = useState(false);
  const { showToast } = useToast();

  // Countdown tick when in cooldown (derive from ends_at_iso for accuracy)
  useEffect(() => {
    if (!status?.in_cooldown || !status.ends_at_iso) return;
    const id = setInterval(() => setTickNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [status?.in_cooldown, status?.ends_at_iso]);

  const displaySeconds =
    status?.in_cooldown && status.ends_at_iso
      ? Math.max(0, Math.floor((new Date(status.ends_at_iso).getTime() - tickNow) / 1000))
      : 0;

  useEffect(() => {
    if (status?.in_cooldown && displaySeconds <= 0) void refetch();
  }, [displaySeconds, status?.in_cooldown, refetch]);

  const handleRewrite = async () => {
    const text = rewriteDraft.trim();
    if (!text) {
      showToast("請先輸入想說的話", "error");
      return;
    }
    setRewriting(true);
    setRewritten(null);
    try {
      const res = await rewriteMessage(text);
      setRewritten(res.rewritten);
      showToast("已改寫為我訊息風格，可複製使用", "success");
    } catch (err) {
      logClientError("cooldown-rewrite-failed", err);
      showToast("改寫失敗，請稍後再試", "error");
    } finally {
      setRewriting(false);
    }
  };

  const handleStart = async (durationMinutes: number) => {
    setStarting(true);
    try {
      await startCooldown(durationMinutes);
      setTickNow(Date.now());
      await queryClient.invalidateQueries({ queryKey: queryKeys.cooldownStatus() });
      showToast("已啟動冷卻時間，伴侶會收到通知", "success");
    } catch (err) {
      logClientError("cooldown-start-failed", err);
      showToast("啟動失敗，請稍後再試", "error");
    } finally {
      setStarting(false);
    }
  };

  if (loading || !status) {
    return (
      <GlassCard className="mb-6 p-6 flex items-center justify-center min-h-[120px]">
        <Loader2 className="w-6 h-6 animate-spin text-primary" aria-hidden />
      </GlassCard>
    );
  }

  return (
    <GlassCard className="mb-6 p-6 md:p-8">
      <h3 className="font-art text-lg font-semibold text-card-foreground mb-2 flex items-center gap-2">
        <span className="icon-badge">
          <Pause className="w-5 h-5 text-primary" aria-hidden />
        </span>
        冷卻模式（SOS）
      </h3>
      <p className="text-caption text-muted-foreground mb-4">
        需要暫停一下時，可啟動冷卻時間，伴侶會收到通知。建議 20–60 分鐘後再好好聊聊。
      </p>
      {status.in_cooldown ? (
        <div className="space-y-4 animate-slide-up-fade">
          <div className="stat-box flex items-center gap-3">
            <span className="icon-badge">
              <Timer className="w-5 h-5 text-primary shrink-0" aria-hidden />
            </span>
            <div>
              <p className="text-body font-medium text-foreground">
                {status.started_by_me ? "你已啟動冷卻" : "伴侶已啟動冷卻"}
              </p>
              <p className="text-title font-semibold text-gradient-gold tabular-nums">
                {formatRemaining(displaySeconds)}
              </p>
            </div>
          </div>
          <div className="rounded-card border border-border bg-background/60 p-4 animate-slide-up-fade-1 shadow-glass-inset">
            <label htmlFor="cooldown-rewrite-input" className="block text-body font-medium text-foreground mb-2">
              寫給對方（改寫成我訊息）
            </label>
            <div className="rounded-xl transition-all duration-haven ease-haven focus-within:shadow-focus-glow focus-within:ring-2 focus-within:ring-primary/20 mb-2">
              <textarea
                id="cooldown-rewrite-input"
                value={rewriteDraft}
                onChange={(e) => setRewriteDraft(e.target.value)}
                placeholder="輸入想說的話，可改寫成較溫和的「我訊息」..."
                className="w-full rounded-xl border border-input bg-muted/30 px-4 py-3 text-foreground placeholder:text-muted-foreground/50 placeholder:font-light focus-visible:bg-card focus-visible:border-transparent outline-none min-h-[72px] resize-y transition-all duration-haven ease-haven"
                maxLength={2000}
              />
            </div>
            <button
              type="button"
              onClick={handleRewrite}
              disabled={rewriting}
              className="rounded-full bg-gradient-to-b from-primary to-primary/90 text-primary-foreground px-5 py-2 text-body font-medium border-t border-t-white/30 shadow-satin-button hover:shadow-lift hover:-translate-y-0.5 active:scale-[0.97] transition-all duration-haven ease-haven focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 disabled:pointer-events-none"
              aria-label="改寫預覽"
            >
              {rewriting ? <Loader2 className="w-4 h-4 animate-spin inline" aria-hidden /> : "改寫預覽"}
            </button>
            {rewritten !== null && (
              <>
                <div className="section-divider" aria-hidden />
                <div className="list-item-premium">
                  <p className="text-caption text-muted-foreground mb-1">改寫建議</p>
                  <p className="text-body text-foreground">{rewritten}</p>
                </div>
              </>
            )}
            <div className="section-divider" aria-hidden />
            <a
              href="https://www.nhs.uk/mental-health/self-help/guides/breathing-exercises/"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-caption font-medium text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
              aria-label="放鬆引導：深呼吸練習（另開新視窗）"
            >
              <span className="icon-badge !w-5 !h-5" aria-hidden><Wind className="w-3 h-3" /></span>
              放鬆引導：深呼吸練習
            </a>
          </div>
        </div>
      ) : (
        <div className="flex flex-wrap gap-2 animate-slide-up-fade">
          {[20, 30, 45, 60].map((mins) => (
            <Button
              key={mins}
              type="button"
              variant="outline"
              size="sm"
              disabled={starting}
              onClick={() => handleStart(mins)}
              className="rounded-full hover:border-primary/30 hover:bg-primary/5 hover:shadow-lift active:scale-[0.97] transition-all duration-haven ease-haven"
              aria-label={`啟動 ${mins} 分鐘冷卻`}
            >
              {starting ? (
                <Loader2 className="w-4 h-4 animate-spin" aria-hidden />
              ) : (
                `${mins} 分鐘`
              )}
            </Button>
          ))}
        </div>
      )}
    </GlassCard>
  );
}
