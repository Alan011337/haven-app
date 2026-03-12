import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { Feather } from '@expo/vector-icons';
import { HavenApiNative } from '../api/HavenApiNative';
import { getStoredToken } from '../api/auth';
import { CardCategory } from 'haven-shared';
import type { CardSession, DeckHistoryEntry } from 'haven-shared';
import { DECK_CATEGORY_LABELS, DECK_CATEGORIES } from '../constants/deckLabels';
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

function generateOperationId(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `rn-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export default function DeckScreen() {
  const router = useRouter();
  const [session, setSession] = useState<CardSession | null>(null);
  const [history, setHistory] = useState<DeckHistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [answer, setAnswer] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [needsLogin, setNeedsLogin] = useState(false);

  const loadHistory = async () => {
    try {
      const list = await HavenApiNative.getDeckHistory({ limit: 10 });
      setHistory(list);
    } catch {
      // keep history best-effort
    }
  };

  const init = useCallback(async () => {
    setError(null);
    const token = await getStoredToken();
    if (!token) {
      setNeedsLogin(true);
      setLoading(false);
      return;
    }
    setNeedsLogin(false);
    await loadHistory();
    setLoading(false);
  }, []);

  useEffect(() => {
    void init();
  }, [init]);

  const handleDraw = async (category: string) => {
    setSubmitting(true);
    setError(null);
    setSession(null);
    try {
      const result = await HavenApiNative.drawDeckCard(category);
      setSession(result);
      await loadHistory();
    } catch (e) {
      setError(e instanceof Error ? e.message : '抽卡失敗');
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmit = async () => {
    const trimmed = answer.trim();
    if (!session || !trimmed || submitting) return;
    setSubmitting(true);
    setError(null);
    const operationId = generateOperationId();
    try {
      const res = await HavenApiNative.respondToDeckCard(session.id, trimmed, {
        idempotencyKey: operationId,
      });
      setAnswer('');
      setSession((prev) =>
        prev
          ? {
              ...prev,
              status: res.session_status as 'COMPLETED' | 'WAITING_PARTNER',
            }
          : null,
      );
      await loadHistory();
    } catch (e) {
      setError(e instanceof Error ? e.message : '送出失敗');
    } finally {
      setSubmitting(false);
    }
  };

  const resetCard = () => {
    setSession(null);
    setAnswer('');
    setError(null);
  };

  if (loading) {
    return (
      <BrandScreen title="牌組圖書館" subtitle="正在整理你們的題庫與最近紀錄。">
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={mobileTheme.colors.primaryStrong} />
          <Text style={styles.loadingText}>載入牌組中…</Text>
        </View>
      </BrandScreen>
    );
  }

  if (needsLogin) {
    return (
      <BrandScreen title="請先登入" subtitle="登入後才能使用牌組圖書館。">
        <EditorialCard style={styles.promptCard}>
          <Text style={styles.promptTitle}>登入後即可開始抽卡</Text>
          <Text style={styles.promptBody}>登入完成後，你可以立即抽取任何一組對話牌卡。</Text>
          <EditorialButton label="前往登入" onPress={() => router.push('/login')} />
        </EditorialCard>
      </BrandScreen>
    );
  }

  return (
    <BrandScreen
      eyebrow="Deck Library"
      title="牌組圖書館"
      subtitle="選一個今天想探索的方向，讓一張卡片替你打開對話。"
    >
      {error ? (
        <FadeUpView>
          <InlineError message={error} />
        </FadeUpView>
      ) : null}

      {!session ? (
        <FadeUpView delay={60}>
          <EditorialCard style={styles.libraryHero}>
            <View style={styles.libraryIcon}>
              <Feather name="book-open" size={20} color={mobileTheme.colors.primaryStrong} />
            </View>
            <Text style={styles.heroTitle}>選擇一組牌卡主題</Text>
            <Text style={styles.heroBody}>
              每個分類都對應一種關係深度，從輕鬆互動到更深的理解。
            </Text>
            <View style={styles.categoryGrid}>
              {DECK_CATEGORIES.map((cat, index) => (
                <FadeUpView key={cat} delay={90 + index * 30} style={styles.categoryCell}>
                  <EditorialButton
                    label={submitting ? '抽卡中…' : DECK_CATEGORY_LABELS[cat as CardCategory]}
                    variant="secondary"
                    onPress={() => handleDraw(cat)}
                    disabled={submitting}
                    style={styles.categoryButton}
                    textStyle={styles.categoryButtonText}
                  />
                </FadeUpView>
              ))}
            </View>
          </EditorialCard>
        </FadeUpView>
      ) : (
        <>
          <FadeUpView delay={60}>
            <EditorialCard style={styles.activeCard}>
              <View style={styles.cardTopRow}>
                <StatusPill label={session.category} tone="sage" />
                <StatusPill
                  label={session.status === 'WAITING_PARTNER' ? '等待伴侶' : session.status === 'COMPLETED' ? '已完成' : '正在作答'}
                />
              </View>
              <Text style={styles.questionText}>
                {session.card?.question ?? session.card?.title ?? '—'}
              </Text>
            </EditorialCard>
          </FadeUpView>

          {session.status === 'COMPLETED' ? (
            <FadeUpView delay={110}>
              <EditorialCard style={styles.completedCard}>
                <Text style={styles.completedTitle}>這張卡片已完成</Text>
                <Text style={styles.heroBody}>你可以回到牌組，或繼續抽下一張。</Text>
                <EditorialButton label="再抽一張" onPress={resetCard} />
              </EditorialCard>
            </FadeUpView>
          ) : session.status === 'WAITING_PARTNER' ? (
            <FadeUpView delay={110}>
              <EditorialCard style={styles.completedCard}>
                <Text style={styles.completedTitle}>你的回應已封存</Text>
                <Text style={styles.heroBody}>伴侶完成後，這輪對話就會正式收束。</Text>
                <EditorialButton label="回到牌組" variant="secondary" onPress={resetCard} />
              </EditorialCard>
            </FadeUpView>
          ) : (
            <FadeUpView delay={110}>
              <EditorialCard style={styles.answerCard}>
                <EditorialInput
                  label="你的回答"
                  placeholder="慢慢寫下你真正想說的話…"
                  multiline
                  maxLength={2000}
                  editable={!submitting}
                  value={answer}
                  onChangeText={setAnswer}
                  style={styles.textarea}
                />
                <EditorialButton
                  label={submitting ? '送出中…' : '送出這張卡片'}
                  loading={submitting}
                  disabled={!answer.trim()}
                  onPress={handleSubmit}
                />
              </EditorialCard>
            </FadeUpView>
          )}
        </>
      )}

      <FadeUpView delay={180}>
        <SectionHeading eyebrow="Archive" title="最近紀錄" meta={`${history.length} 則`} />
      </FadeUpView>

      {history.length === 0 ? (
        <FadeUpView delay={220}>
          <EditorialCard>
            <Text style={styles.emptyTitle}>你的牌卡紀錄會收藏在這裡</Text>
            <Text style={styles.heroBody}>開始第一輪對話後，這裡就會留下你們的痕跡。</Text>
          </EditorialCard>
        </FadeUpView>
      ) : (
        history.slice(0, 10).map((entry, index) => (
          <FadeUpView key={`${entry.session_id}-${index}`} delay={220 + index * 35}>
            <EditorialCard style={styles.historyCard}>
              <View style={styles.historyTopRow}>
                <StatusPill label={entry.category} tone="sage" />
                <Text style={styles.historyDate}>
                  {new Date(entry.revealed_at).toLocaleDateString('zh-TW')}
                </Text>
              </View>
              <Text style={styles.historyQuestion} numberOfLines={2}>
                {entry.card_question}
              </Text>
            </EditorialCard>
          </FadeUpView>
        ))
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
  libraryHero: {
    gap: mobileTheme.spacing.md,
  },
  libraryIcon: {
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
  categoryGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginHorizontal: -4,
  },
  categoryCell: {
    width: '50%',
    paddingHorizontal: 4,
    paddingBottom: 8,
  },
  categoryButton: {
    minHeight: 48,
    borderRadius: mobileTheme.radius.md,
  },
  categoryButtonText: {
    fontSize: 14,
  },
  activeCard: {
    gap: mobileTheme.spacing.md,
  },
  cardTopRow: {
    flexDirection: 'row',
    gap: mobileTheme.spacing.sm,
    flexWrap: 'wrap',
  },
  questionText: {
    ...mobileTheme.typography.title,
    fontSize: 22,
    lineHeight: 30,
  },
  answerCard: {
    gap: mobileTheme.spacing.md,
  },
  textarea: {
    minHeight: 132,
    textAlignVertical: 'top',
  },
  completedCard: {
    gap: mobileTheme.spacing.sm,
  },
  completedTitle: {
    ...mobileTheme.typography.title,
    fontSize: 20,
    lineHeight: 26,
  },
  historyCard: {
    gap: mobileTheme.spacing.sm,
  },
  historyTopRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: mobileTheme.spacing.sm,
  },
  historyDate: {
    ...mobileTheme.typography.caption,
  },
  historyQuestion: {
    ...mobileTheme.typography.body,
  },
  emptyTitle: {
    ...mobileTheme.typography.title,
    fontSize: 20,
    lineHeight: 26,
  },
});
