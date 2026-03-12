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
      eyebrow="Couple Journal"
      title="今天，想留下什麼？"
      subtitle="把一句心緒、一段想念，安放進你們的靜奢日記裡。"
    >
      {error ? (
        <FadeUpView>
          <InlineError message={error} />
        </FadeUpView>
      ) : null}

      <FadeUpView delay={40}>
        <EditorialCard style={styles.composerCard}>
          <View style={styles.composerHeader}>
            <StatusPill label="今日頁面" />
            <Text style={styles.composerHint}>2000 字以內，慢慢寫就好</Text>
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

      <FadeUpView delay={100}>
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

      <FadeUpView delay={150}>
        <SectionHeading
          eyebrow="Memory Lane"
          title="我的日記"
          meta={`${journals.length} 篇`}
        />
      </FadeUpView>

      {journals.length === 0 ? (
        <FadeUpView delay={200}>
          <EditorialCard style={styles.emptyCard}>
            <View style={styles.emptyIcon}>
              <Feather name="feather" size={18} color={mobileTheme.colors.accent} />
            </View>
            <Text style={styles.emptyTitle}>第一篇日記，會在這裡發光</Text>
            <Text style={styles.emptyBody}>寫下今天的片刻，讓 Haven 為你收好。</Text>
          </EditorialCard>
        </FadeUpView>
      ) : (
        journals.map((journal, index) => (
          <FadeUpView key={journal.id} delay={200 + index * 40}>
            <EditorialCard style={styles.journalCard}>
              <View style={styles.journalTopRow}>
                <StatusPill label={new Date(journal.created_at).toLocaleDateString('zh-TW')} tone="sage" />
                <Text style={styles.journalMeta}>私人札記</Text>
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
  },
  navButton: {
    flex: 1,
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
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: mobileTheme.spacing.sm,
  },
  journalMeta: {
    ...mobileTheme.typography.caption,
  },
  journalContent: {
    ...mobileTheme.typography.body,
  },
});
