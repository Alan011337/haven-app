import { useEffect, useState } from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { Feather } from '@expo/vector-icons';
import { HavenApiNative, clearToken } from '../api/HavenApiNative';
import { getStoredToken } from '../api/auth';
import type { Journal } from 'haven-shared';
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

export default function HomeScreen() {
  const router = useRouter();
  const [journals, setJournals] = useState<Journal[]>([]);
  const [loading, setLoading] = useState(true);
  const [content, setContent] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [needsLogin, setNeedsLogin] = useState(false);

  const loadJournals = async () => {
    setError(null);
    const token = await getStoredToken();
    if (!token) {
      setNeedsLogin(true);
      setLoading(false);
      return;
    }

    try {
      const list = await HavenApiNative.getJournals();
      setJournals(list);
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
    void loadJournals();
  }, []);

  const handleCreate = async () => {
    const trimmed = content.trim();
    if (!trimmed || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      await HavenApiNative.createJournal(trimmed);
      setContent('');
      await loadJournals();
    } catch (e) {
      setError(e instanceof Error ? e.message : '發布失敗');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <BrandScreen title="正在整理你的避風港" subtitle="我們正在安靜地鋪陳今日頁面。">
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={mobileTheme.colors.primaryStrong} />
          <Text style={styles.loadingText}>載入日記中…</Text>
        </View>
      </BrandScreen>
    );
  }

  if (needsLogin) {
    return (
      <BrandScreen
        eyebrow="Couple Journal"
        title="請先登入"
        subtitle="登入後才能查看你們的日記與每日共感。"
        variant="home"
      >
        <FadeUpView>
          <EditorialCard style={styles.promptCard}>
            <View style={styles.promptIcon}>
              <Feather name="lock" size={18} color={mobileTheme.colors.primaryStrong} />
            </View>
            <Text style={styles.promptTitle}>這裡需要你的身份確認</Text>
            <Text style={styles.promptBody}>
              完成登入後，Haven 會帶你回到今天的頁面與儀式。
            </Text>
            <EditorialButton label="前往登入" onPress={() => router.push('/login')} />
          </EditorialCard>
        </FadeUpView>
      </BrandScreen>
    );
  }

  return (
    <BrandScreen
      eyebrow="Home Edition"
      title="先把今天寫下來，其他一切都可以晚一點。"
      subtitle="首頁先替你的心緒留出版面，然後再把 daily、deck 與回憶安靜地排進第二層。"
      variant="home"
    >
      {error ? (
        <FadeUpView>
          <InlineError message={error} />
        </FadeUpView>
      ) : null}

      <FadeUpView delay={20}>
        <EditorialCard style={styles.heroCard} tone="hero">
          <View style={styles.heroHeader}>
            <View style={styles.heroHeaderText}>
              <Text style={styles.heroEyebrow}>Cover Story</Text>
              <Text style={styles.heroTitle}>把今天真正想留下的那一句，放到前景。</Text>
            </View>
            <StatusPill label={`${journals.length} 篇`} tone="mutedWarm" />
          </View>
          <Text style={styles.heroBody}>
            當首頁夠安靜，重要的互動就不需要被提醒很多次。先寫一點點，再讓 Haven 幫你把今天排成一頁。
          </Text>
          <View style={styles.heroPulseRow}>
            <View style={styles.heroPulseCard}>
              <Text style={styles.heroPulseLabel}>今日頁面</Text>
              <Text style={styles.heroPulseValue}>My Journal</Text>
              <Text style={styles.heroPulseBody}>先把自己的感受寫成一頁，再決定要不要進入其他 flow。</Text>
            </View>
            <View style={styles.heroPulseCard}>
              <Text style={styles.heroPulseLabel}>Quick Ritual</Text>
              <Text style={styles.heroPulseValue}>Daily / Deck</Text>
              <Text style={styles.heroPulseBody}>需要一點互動時，再往下進入每日共感與牌組圖書館。</Text>
            </View>
          </View>
          <View style={styles.heroNote}>
            <Text style={styles.heroNoteEyebrow}>Editorial Note</Text>
            <Text style={styles.heroNoteBody}>
              先寫、再看、最後再進入 ritual。這一版首頁故意把節奏放慢，讓你不用同時處理所有提醒。
            </Text>
          </View>
        </EditorialCard>
      </FadeUpView>

      <FadeUpView delay={60}>
        <EditorialCard style={styles.composerCard} tone="paper">
          <View style={styles.composerHeader}>
            <StatusPill label="今日頁面" />
            <Text style={styles.composerHint}>先寫，不用急著完整</Text>
          </View>
          <EditorialInput
            label="今日心緒"
            placeholder="今天發生了什麼事？你想被怎麼理解？"
            multiline
            maxLength={4000}
            editable={!submitting}
            value={content}
            onChangeText={setContent}
            style={styles.textarea}
          />
          <EditorialButton
            label={submitting ? '發布中…' : '收藏這篇日記'}
            loading={submitting}
            onPress={handleCreate}
            disabled={!content.trim()}
          />
        </EditorialCard>
      </FadeUpView>

      <FadeUpView delay={110}>
        <SectionHeading
          eyebrow="Second Layer"
          title="把其餘 flow 放到後面"
        />
      </FadeUpView>

      <FadeUpView delay={130}>
        <View style={styles.navRow}>
          <EditorialButton
            label="每日共感"
            variant="secondary"
            style={styles.navButton}
            onPress={() => router.push('/daily')}
          />
          <EditorialButton
            label="牌組圖書館"
            variant="secondary"
            style={styles.navButton}
            onPress={() => router.push('/deck')}
          />
          <EditorialButton
            label="登出"
            variant="ghost"
            style={styles.logoutButton}
            onPress={async () => {
              await clearToken();
              setNeedsLogin(true);
            }}
          />
        </View>
      </FadeUpView>

      <FadeUpView delay={170}>
        <SectionHeading
          eyebrow="Memory Lane"
          title="我的日記"
          meta={`${journals.length} 篇`}
          metaPlacement="stacked"
        />
      </FadeUpView>

      {journals.length === 0 ? (
        <FadeUpView delay={210}>
          <EditorialCard style={styles.emptyCard} tone="mist">
            <View style={styles.emptyIcon}>
              <Feather name="feather" size={18} color={mobileTheme.colors.accent} />
            </View>
            <Text style={styles.emptyTitle}>第一篇日記，會從這裡開始發光</Text>
            <Text style={styles.emptyBody}>當你開始留下內容，首頁就會從空白頁，變成你們關係的編輯檯。</Text>
          </EditorialCard>
        </FadeUpView>
      ) : (
        journals.map((journal, index) => (
          <FadeUpView key={journal.id} delay={210 + index * 40}>
            <EditorialCard style={styles.journalCard} tone="paper">
              <View style={styles.journalTopRow}>
                <View style={styles.journalChapter}>
                  <Text style={styles.journalChapterEyebrow}>Chapter {String(index + 1).padStart(2, '0')}</Text>
                  <Text style={styles.journalMeta}>{new Date(journal.created_at).toLocaleDateString('zh-TW')}</Text>
                </View>
                <StatusPill label="安靜收藏" tone="sage" />
              </View>
              <Text style={styles.journalContent} numberOfLines={5}>
                {journal.content}
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
  promptIcon: {
    width: 40,
    height: 40,
    borderRadius: mobileTheme.radius.md,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: mobileTheme.colors.primarySoft,
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
    gap: mobileTheme.spacing.md,
  },
  heroHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: mobileTheme.spacing.md,
  },
  heroHeaderText: {
    flex: 1,
    gap: 6,
  },
  heroEyebrow: {
    ...mobileTheme.typography.eyebrow,
  },
  heroTitle: {
    ...mobileTheme.typography.title,
    fontSize: 24,
    lineHeight: 30,
  },
  heroBody: {
    ...mobileTheme.typography.bodyMuted,
  },
  heroPulseRow: {
    gap: mobileTheme.spacing.sm,
  },
  heroPulseCard: {
    borderRadius: mobileTheme.radius.md,
    borderWidth: 1,
    borderColor: mobileTheme.colors.borderStrong,
    backgroundColor: mobileTheme.colors.surfaceElevated,
    padding: mobileTheme.spacing.md,
    gap: 6,
  },
  heroPulseLabel: {
    ...mobileTheme.typography.eyebrow,
  },
  heroPulseValue: {
    ...mobileTheme.typography.title,
    fontSize: 18,
    lineHeight: 24,
  },
  heroPulseBody: {
    ...mobileTheme.typography.caption,
    lineHeight: 20,
  },
  heroNote: {
    borderRadius: mobileTheme.radius.md,
    borderWidth: 1,
    borderColor: mobileTheme.colors.borderStrong,
    backgroundColor: mobileTheme.colors.surfaceElevated,
    padding: mobileTheme.spacing.md,
    gap: 6,
  },
  heroNoteEyebrow: {
    ...mobileTheme.typography.eyebrow,
  },
  heroNoteBody: {
    ...mobileTheme.typography.bodyMuted,
  },
  composerCard: {
    gap: mobileTheme.spacing.md,
  },
  composerHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: mobileTheme.spacing.md,
  },
  composerHint: {
    ...mobileTheme.typography.caption,
  },
  textarea: {
    minHeight: 132,
    textAlignVertical: 'top',
  },
  navRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: mobileTheme.spacing.sm,
    flexWrap: 'wrap',
  },
  navButton: {
    flex: 1,
    minWidth: 120,
  },
  logoutButton: {
    paddingHorizontal: mobileTheme.spacing.sm,
  },
  emptyCard: {
    alignItems: 'flex-start',
  },
  emptyIcon: {
    width: 40,
    height: 40,
    borderRadius: mobileTheme.radius.md,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: mobileTheme.colors.accentSoft,
  },
  emptyTitle: {
    ...mobileTheme.typography.title,
    fontSize: 20,
    lineHeight: 26,
  },
  emptyBody: {
    ...mobileTheme.typography.bodyMuted,
  },
  journalCard: {
    gap: mobileTheme.spacing.sm,
  },
  journalTopRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: mobileTheme.spacing.sm,
  },
  journalChapter: {
    gap: 4,
  },
  journalChapterEyebrow: {
    ...mobileTheme.typography.eyebrow,
  },
  journalMeta: {
    ...mobileTheme.typography.caption,
  },
  journalContent: {
    ...mobileTheme.typography.body,
  },
});
