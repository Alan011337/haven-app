import { useCallback, useEffect, useState } from 'react';
import {
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
  ActivityIndicator,
  ScrollView,
} from 'react-native';
import { useRouter } from 'expo-router';
import { HavenApiNative } from '../api/HavenApiNative';
import { getStoredToken } from '../api/auth';
import { CardCategory } from 'haven-shared';
import type { CardSession, DeckHistoryEntry } from 'haven-shared';
import { DECK_CATEGORY_LABELS, DECK_CATEGORIES } from '../constants/deckLabels';

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
      // ignore
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
    init();
  }, [init]);

  const handleDraw = async (category: string) => {
    setSubmitting(true);
    setError(null);
    setSession(null);
    try {
      const s = await HavenApiNative.drawDeckCard(category);
      setSession(s);
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
          : null
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
      <View style={styles.centered}>
        <ActivityIndicator size="large" />
        <Text style={styles.hint}>載入中…</Text>
      </View>
    );
  }

  if (needsLogin) {
    return (
      <View style={styles.centered}>
        <Text style={styles.hint}>請先登入</Text>
        <TouchableOpacity style={styles.button} onPress={() => router.push('/login')}>
          <Text style={styles.buttonText}>前往登入</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {error ? <Text style={styles.error}>{error}</Text> : null}

      {!session ? (
        <>
          <Text style={styles.sectionTitle}>選擇牌組</Text>
          <View style={styles.categoryGrid}>
            {DECK_CATEGORIES.map((cat) => (
              <TouchableOpacity
                key={cat}
                style={[styles.categoryBtn, submitting && styles.buttonDisabled]}
                onPress={() => handleDraw(cat)}
                disabled={submitting}
              >
                <Text style={styles.categoryBtnText}>
                  {submitting ? '抽卡中…' : DECK_CATEGORY_LABELS[cat as CardCategory]}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </>
      ) : (
        <>
          <View style={styles.card}>
            <Text style={styles.cardCategory}>{session.category}</Text>
            <Text style={styles.cardQuestion}>{session.card?.question ?? session.card?.title ?? '—'}</Text>
          </View>

          {session.status === 'COMPLETED' ? (
            <View style={styles.actions}>
              <TouchableOpacity style={styles.button} onPress={resetCard}>
                <Text style={styles.buttonText}>再抽一張</Text>
              </TouchableOpacity>
            </View>
          ) : session.status === 'WAITING_PARTNER' ? (
            <View style={styles.waiting}>
              <Text style={styles.hint}>已送出，等待伴侶回答</Text>
              <TouchableOpacity style={styles.button} onPress={resetCard}>
                <Text style={styles.buttonText}>先回牌組</Text>
              </TouchableOpacity>
            </View>
          ) : (
            <View style={styles.inputRow}>
              <TextInput
                style={styles.input}
                placeholder="寫下你的回答…"
                placeholderTextColor="#999"
                value={answer}
                onChangeText={setAnswer}
                multiline
                maxLength={2000}
                editable={!submitting}
              />
              <TouchableOpacity
                style={[styles.button, (submitting || !answer.trim()) && styles.buttonDisabled]}
                onPress={handleSubmit}
                disabled={submitting || !answer.trim()}
              >
                <Text style={styles.buttonText}>{submitting ? '送出中…' : '送出'}</Text>
              </TouchableOpacity>
            </View>
          )}
        </>
      )}

      <Text style={styles.sectionTitle}>最近紀錄</Text>
      {history.length === 0 ? (
        <Text style={styles.hint}>尚無紀錄</Text>
      ) : (
        history.slice(0, 10).map((entry, i) => (
          <View key={`${entry.session_id}-${i}`} style={styles.historyCard}>
            <Text style={styles.historyCategory}>{entry.category}</Text>
            <Text style={styles.historyQuestion} numberOfLines={1}>{entry.card_question}</Text>
            <Text style={styles.hint}>{new Date(entry.revealed_at).toLocaleDateString('zh-TW')}</Text>
          </View>
        ))
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  content: { padding: 16 },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 12,
  },
  hint: { color: '#666', fontSize: 14, marginTop: 4 },
  error: { color: '#b91c1c', marginBottom: 8, fontSize: 14 },
  sectionTitle: { fontSize: 18, fontWeight: '700', marginTop: 16, marginBottom: 8 },
  categoryGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  categoryBtn: {
    backgroundColor: '#f3e8ff',
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 8,
  },
  categoryBtnText: { color: '#7c3aed', fontWeight: '600' },
  card: {
    borderWidth: 1,
    borderColor: '#e5e7eb',
    borderRadius: 12,
    padding: 16,
    marginTop: 8,
  },
  cardCategory: { fontSize: 12, color: '#7c3aed', marginBottom: 4 },
  cardQuestion: { fontSize: 16, color: '#333' },
  inputRow: { gap: 8, marginTop: 12 },
  input: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    padding: 12,
    minHeight: 80,
    fontSize: 16,
    textAlignVertical: 'top',
  },
  button: {
    backgroundColor: '#7c3aed',
    paddingVertical: 14,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 8,
  },
  buttonDisabled: { opacity: 0.6 },
  buttonText: { color: '#fff', fontWeight: '600' },
  actions: { marginTop: 16 },
  waiting: { marginTop: 16, gap: 8 },
  historyCard: {
    borderWidth: 1,
    borderColor: '#eee',
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
  },
  historyCategory: { fontSize: 12, color: '#666' },
  historyQuestion: { fontSize: 14, color: '#333', marginVertical: 4 },
});
