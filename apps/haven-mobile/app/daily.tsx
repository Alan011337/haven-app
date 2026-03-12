import { useEffect, useState } from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { Feather } from '@expo/vector-icons';
import { HavenApiNative, clearToken } from '../api/HavenApiNative';
import { getStoredToken } from '../api/auth';
import type { Card } from 'haven-shared';
import { BrandScreen } from '../components/BrandScreen';
import {
  EditorialButton,
  EditorialCard,
  EditorialInput,
  FadeUpView,
  InlineError,
  SectionHeading,
  StatusPill,
} from '../components/BrandPrimitives';
import { mobileTheme } from '../theme/editorial';

type DailyState = 'IDLE' | 'PARTNER_STARTED' | 'WAITING_PARTNER' | 'COMPLETED';

interface DailyStatus {
  state: DailyState;
  card: Card | null;
  my_content?: string;
  partner_content?: string;
  session_id?: string | null;
}

function generateOperationId(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `rn-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export default function DailyCardScreen() {
  const router = useRouter();
  const [status, setStatus] = useState<DailyStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [answer, setAnswer] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [needsLogin, setNeedsLogin] = useState(false);

  const loadStatus = async () => {
    setError(null);
    const token = await getStoredToken();
    if (!token) {
      setNeedsLogin(true);
      setLoading(false);
      return;
    }
    try {
      const data = await HavenApiNative.getDailyStatus();
      setStatus(data as DailyStatus);
      setNeedsLogin(false);
    } catch (e) {
      const msg = e instanceof Error ? e.message : '載入失敗';
      if (msg.includes('Unauthorized') || msg.includes('401')) {
        await clearToken();
        setNeedsLogin(true);
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadStatus();
  }, []);

  const handleDraw = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const card = await HavenApiNative.drawDailyCard();
      setStatus((prev) => ({
        state: prev?.state ?? 'IDLE',
        card,
        my_content: prev?.my_content,
        partner_content: prev?.partner_content,
        session_id: prev?.session_id,
      }));
    } catch (e) {
      setError(e instanceof Error ? e.message : '抽卡失敗');
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmit = async () => {
    const trimmed = answer.trim();
    if (!status?.card || !trimmed || submitting) return;
    setSubmitting(true);
    setError(null);
    const operationId = generateOperationId();
    try {
      const res = await HavenApiNative.respondDailyCard(status.card.id, trimmed, {
        idempotencyKey: operationId,
      });
      setStatus((prev) =>
        prev
          ? {
              ...prev,
              state: res.status === 'REVEALED' ? 'COMPLETED' : 'WAITING_PARTNER',
              my_content: trimmed,
              partner_content: prev.partner_content,
            }
          : null,
      );
      setAnswer('');
      await loadStatus();
    } catch (e) {
      setError(e instanceof Error ? e.message : '送出失敗');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <BrandScreen title="每日共感" subtitle="正在鋪好今天的儀式頁。">
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={mobileTheme.colors.primaryStrong} />
          <Text style={styles.loadingText}>載入每日卡片…</Text>
        </View>
      </BrandScreen>
    );
  }

  if (needsLogin) {
    return (
      <BrandScreen title="請先登入" subtitle="登入後才能開始今天的雙人儀式。">
        <EditorialCard style={styles.promptCard}>
          <Text style={styles.promptTitle}>你還沒登入 Haven</Text>
          <Text style={styles.promptBody}>登入後即可抽取今日共感卡片並寫下你的回應。</Text>
          <EditorialButton label="前往登入" onPress={() => router.push('/login')} />
        </EditorialCard>
      </BrandScreen>
    );
  }

  const stateLabel =
    status?.state === 'COMPLETED'
      ? '雙方已揭曉'
      : status?.state === 'WAITING_PARTNER'
        ? '等待伴侶'
        : status?.card
          ? '輪到你回答'
          : '尚未抽卡';

  return (
    <BrandScreen
      eyebrow="Daily Ritual"
      title="每日共感"
      subtitle="一張卡片，一段回答，讓你們在同一天裡靠近一點。"
    >
      {error ? (
        <FadeUpView>
          <InlineError message={error} />
        </FadeUpView>
      ) : null}

      <FadeUpView delay={40}>
        <SectionHeading
          eyebrow="Today"
          title="今天的儀式"
          meta={stateLabel}
        />
      </FadeUpView>

      {!status?.card ? (
        <FadeUpView delay={100}>
          <EditorialCard style={styles.heroCard}>
            <View style={styles.heroIcon}>
              <Feather name="star" size={20} color={mobileTheme.colors.primaryStrong} />
            </View>
            <Text style={styles.heroTitle}>抽一張今日共感卡片</Text>
            <Text style={styles.heroBody}>
              今天的問題會讓你更靠近彼此的內在世界。準備好了就開始吧。
            </Text>
            <EditorialButton
              label={submitting ? '抽卡中…' : '開始今天的儀式'}
              loading={submitting}
              onPress={handleDraw}
            />
          </EditorialCard>
        </FadeUpView>
      ) : (
        <>
          <FadeUpView delay={100}>
            <EditorialCard style={styles.ritualCard}>
              <View style={styles.cardHeader}>
                <StatusPill label={status.card.category} tone="sage" />
                <StatusPill label={status.state === 'COMPLETED' ? 'Revealed' : 'Private'} />
              </View>
              <Text style={styles.question}>{status.card.question}</Text>
            </EditorialCard>
          </FadeUpView>

          {status.state === 'COMPLETED' ? (
            <FadeUpView delay={140}>
              <View style={styles.revealStack}>
                <EditorialCard>
                  <Text style={styles.responseLabel}>我的回答</Text>
                  <Text style={styles.responseText}>{status.my_content || '—'}</Text>
                </EditorialCard>
                <EditorialCard>
                  <Text style={styles.responseLabel}>伴侶的回答</Text>
                  <Text style={styles.responseText}>{status.partner_content || '—'}</Text>
                </EditorialCard>
              </View>
            </FadeUpView>
          ) : status.state === 'WAITING_PARTNER' ? (
            <FadeUpView delay={140}>
              <EditorialCard style={styles.waitingCard}>
                <StatusPill label="已送出" tone="warm" />
                <Text style={styles.waitingTitle}>你的回答已悄悄放好</Text>
                <Text style={styles.waitingBody}>現在等待伴侶寫下她/他的版本，完成後會一起揭曉。</Text>
                <Text style={styles.responseText}>{status.my_content || '—'}</Text>
                <EditorialButton label="重新整理狀態" variant="secondary" onPress={loadStatus} />
              </EditorialCard>
            </FadeUpView>
          ) : (
            <FadeUpView delay={140}>
              <EditorialCard style={styles.answerCard}>
                <EditorialInput
                  label="你的回答"
                  placeholder="把此刻最真實的念頭寫下來…"
                  multiline
                  maxLength={2000}
                  editable={!submitting}
                  value={answer}
                  onChangeText={setAnswer}
                  style={styles.textarea}
                />
                <EditorialButton
                  label={submitting ? '送出中…' : '封存這段回應'}
                  loading={submitting}
                  disabled={!answer.trim()}
                  onPress={handleSubmit}
                />
              </EditorialCard>
            </FadeUpView>
          )}
        </>
      )}
    </BrandScreen>
  );
}

const styles = StyleSheet.create({
  centered: {
    alignItems: 'center',
    justifyContent: 'center',
    gap: mobileTheme.spacing.sm,
    paddingTop: mobileTheme.spacing.xxl,
  },
  loadingText: {
    ...mobileTheme.typography.bodyMuted,
  },
  promptCard: {
    gap: mobileTheme.spacing.sm,
  },
  promptTitle: {
    ...mobileTheme.typography.title,
    fontSize: 20,
    lineHeight: 26,
  },
  promptBody: {
    ...mobileTheme.typography.bodyMuted,
  },
  heroCard: {
    gap: mobileTheme.spacing.sm,
  },
  heroIcon: {
    width: 44,
    height: 44,
    borderRadius: mobileTheme.radius.md,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: mobileTheme.colors.primarySoft,
  },
  heroTitle: {
    ...mobileTheme.typography.title,
  },
  heroBody: {
    ...mobileTheme.typography.bodyMuted,
  },
  ritualCard: {
    gap: mobileTheme.spacing.md,
  },
  cardHeader: {
    flexDirection: 'row',
    gap: mobileTheme.spacing.sm,
    flexWrap: 'wrap',
  },
  question: {
    ...mobileTheme.typography.title,
    fontSize: 22,
    lineHeight: 30,
  },
  answerCard: {
    gap: mobileTheme.spacing.md,
  },
  textarea: {
    minHeight: 148,
    textAlignVertical: 'top',
  },
  waitingCard: {
    gap: mobileTheme.spacing.sm,
  },
  waitingTitle: {
    ...mobileTheme.typography.title,
    fontSize: 20,
    lineHeight: 26,
  },
  waitingBody: {
    ...mobileTheme.typography.bodyMuted,
  },
  revealStack: {
    gap: mobileTheme.spacing.md,
  },
  responseLabel: {
    ...mobileTheme.typography.eyebrow,
  },
  responseText: {
    ...mobileTheme.typography.body,
  },
});
