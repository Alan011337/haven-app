'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, ShieldAlert, CheckCircle2, XCircle, EyeOff, Loader2 } from 'lucide-react';
import { api } from '@/lib/api';
import { GlassCard } from '@/components/haven/GlassCard';
import { useToast } from '@/hooks/useToast';

export interface ModerationReport {
  id: string;
  created_at: string;
  resource_type: string;
  resource_id: string;
  reporter_user_id: string;
  reason: string | null;
  status: string;
  reviewed_at: string | null;
  reviewer_admin_id: string | null;
  resolution_note: string | null;
}

const STATUS_LABELS: Record<string, string> = {
  pending: '待審核',
  approved: '已通過',
  dismissed: '已駁回',
  hidden: '已隱藏',
};

const RESOURCE_TYPE_LABELS: Record<string, string> = {
  whisper_wall: 'Whisper Wall',
  deck_marketplace: '牌組市集',
  journal: '日記',
  card: '卡片',
};

export default function AdminModerationPage() {
  const [reports, setReports] = useState<ModerationReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('pending');
  const [forbidden, setForbidden] = useState(false);
  const [resolvingId, setResolvingId] = useState<string | null>(null);
  const { showToast } = useToast();

  const loadQueue = useCallback(async () => {
    setLoading(true);
    setForbidden(false);
    try {
      const { data } = await api.get<ModerationReport[]>('/admin/moderation/queue', {
        params: { status_filter: statusFilter, limit: 100 },
      });
      setReports(Array.isArray(data) ? data : []);
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 403) {
        setForbidden(true);
        setReports([]);
      } else {
        showToast('無法載入檢舉佇列', 'error');
        setReports([]);
      }
    } finally {
      setLoading(false);
    }
  }, [statusFilter, showToast]);

  useEffect(() => {
    loadQueue();
  }, [loadQueue]);

  const handleResolve = async (reportId: string, status: 'approved' | 'dismissed' | 'hidden', note?: string) => {
    if (resolvingId) return;
    setResolvingId(reportId);
    try {
      await api.post(`/admin/moderation/${reportId}/resolve`, { status, resolution_note: note || null });
      showToast(`已標記為「${STATUS_LABELS[status] || status}」`, 'success');
      await loadQueue();
    } catch (err: unknown) {
      const statusCode = (err as { response?: { status?: number; data?: { detail?: string } } })?.response?.status;
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      if (statusCode === 403) {
        setForbidden(true);
        showToast('無審核權限', 'error');
      } else {
        showToast(detail || '操作失敗', 'error');
      }
    } finally {
      setResolvingId(null);
    }
  };

  if (forbidden) {
    return (
      <div className="min-h-screen bg-muted/40 flex items-center justify-center p-6">
        <GlassCard className="max-w-md w-full p-6 text-center">
          <ShieldAlert className="w-12 h-12 text-destructive mx-auto mb-4" aria-hidden />
          <h1 className="text-title font-semibold text-foreground mb-2">需要管理員權限</h1>
          <p className="text-body text-muted-foreground mb-6">此頁面僅供管理員審核檢舉內容使用。</p>
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-primary hover:underline font-medium"
          >
            <ArrowLeft className="w-4 h-4" />
            返回首頁
          </Link>
        </GlassCard>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-muted/40 space-page">
      <div className="max-w-4xl mx-auto">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-muted-foreground hover:text-foreground font-medium mb-6"
        >
          <ArrowLeft className="w-4 h-4" />
          返回首頁
        </Link>

        <GlassCard className="p-6 mb-6 relative overflow-hidden animate-slide-up-fade">
          <div className="absolute top-0 inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-primary/25 to-transparent" aria-hidden />
          <h1 className="text-title font-art font-bold text-foreground mb-1 flex items-center gap-2.5">
            <span className="icon-badge !w-9 !h-9" aria-hidden><ShieldAlert className="w-4.5 h-4.5" /></span>
            內容審核後台
          </h1>
          <p className="text-caption text-muted-foreground mb-4">
            Whisper Wall 與牌組市集檢舉內容人工審核（P2-I [ADMIN-02]）
          </p>
          <div className="flex flex-wrap gap-2">
            {['pending', 'approved', 'dismissed', 'hidden', 'all'].map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => setStatusFilter(s)}
                className={`px-3 py-1.5 rounded-button text-sm font-medium transition-all duration-haven-fast ease-haven ${
                  statusFilter === s
                    ? 'bg-gradient-to-b from-primary to-primary/90 text-primary-foreground shadow-satin-button'
                    : 'bg-muted text-muted-foreground hover:bg-muted/80'
                }`}
              >
                {s === 'all' ? '全部' : STATUS_LABELS[s] || s}
              </button>
            ))}
          </div>
        </GlassCard>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" aria-hidden />
          </div>
        ) : reports.length === 0 ? (
          <GlassCard className="p-8 text-center text-muted-foreground">
            目前沒有符合條件的檢舉紀錄。
          </GlassCard>
        ) : (
          <ul className="space-y-4">
            {reports.map((r) => (
              <li key={r.id}>
                <GlassCard className="p-4">
                  <div className="flex flex-wrap items-start justify-between gap-2 mb-2">
                    <span className="text-caption text-muted-foreground tabular-nums">
                      {new Date(r.created_at).toLocaleString('zh-TW')} ·{' '}
                      {RESOURCE_TYPE_LABELS[r.resource_type] || r.resource_type} · {r.resource_id}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-medium ${
                        r.status === 'pending'
                          ? 'bg-primary/20 text-primary'
                          : 'bg-muted text-muted-foreground'
                      }`}
                    >
                      {STATUS_LABELS[r.status] || r.status}
                    </span>
                  </div>
                  {r.reason && (
                    <p className="text-body text-foreground mb-3">{r.reason}</p>
                  )}
                  <p className="text-caption text-muted-foreground mb-3">
                    檢舉者 ID: {r.reporter_user_id}
                    {r.reviewed_at && (
                      <> · 審核於 {new Date(r.reviewed_at).toLocaleString('zh-TW')}</>
                    )}
                    {r.resolution_note && <> · {r.resolution_note}</>}
                  </p>
                  {r.status === 'pending' && (
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => handleResolve(r.id, 'approved')}
                        disabled={resolvingId === r.id}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-button bg-accent text-accent-foreground text-sm font-medium shadow-soft hover:shadow-lift disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      >
                        {resolvingId === r.id ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <CheckCircle2 className="w-4 h-4" />
                        )}
                        通過
                      </button>
                      <button
                        type="button"
                        onClick={() => handleResolve(r.id, 'dismissed')}
                        disabled={resolvingId === r.id}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-button bg-muted text-foreground text-sm font-medium hover:bg-muted/80 disabled:opacity-50"
                      >
                        {resolvingId === r.id ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <XCircle className="w-4 h-4" />
                        )}
                        駁回
                      </button>
                      <button
                        type="button"
                        onClick={() => handleResolve(r.id, 'hidden')}
                        disabled={resolvingId === r.id}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-button bg-primary text-primary-foreground text-sm font-medium shadow-soft hover:shadow-lift disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      >
                        {resolvingId === r.id ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <EyeOff className="w-4 h-4" />
                        )}
                        隱藏
                      </button>
                    </div>
                  )}
                </GlassCard>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
