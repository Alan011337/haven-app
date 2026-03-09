import { useEffect, useState } from 'react';
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
import { HavenApiNative, clearToken } from '../api/HavenApiNative';
import { getStoredToken } from '../api/auth';
import type { Card } from 'haven-shared';

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
    loadStatus();
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
          : null
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

      {!status?.card ? (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>今日共感卡片</Text>
          <Text style={styles.hint}>抽一張卡片，與伴侶一起回答</Text>
          <TouchableOpacity
            style={[styles.button, submitting && styles.buttonDisabled]}
            onPress={handleDraw}
            disabled={submitting}
          >
            <Text style={styles.buttonText}>{submitting ? '抽卡中…' : '抽今日卡片'}</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <>
          <View style={styles.card}>
            <Text style={styles.cardCategory}>{status.card.category}</Text>
            <Text style={styles.cardQuestion}>{status.card.question}</Text>
          </View>

          {status.state === 'COMPLETED' ? (
            <View style={styles.reveal}>
              <Text style={styles.revealLabel}>我的回答</Text>
              <Text style={styles.revealContent}>{status.my_content || '—'}</Text>
              <Text style={styles.revealLabel}>伴侶的回答</Text>
              <Text style={styles.revealContent}>{status.partner_content || '—'}</Text>
            </View>
          ) : status.state === 'WAITING_PARTNER' ? (
            <View style={styles.waiting}>
              <Text style={styles.hint}>已送出，等待伴侶回答</Text>
              <Text style={styles.revealContent}>{status.my_content}</Text>
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
  hint: { color: '#666', fontSize: 14, marginTop: 8 },
  error: { color: '#b91c1c', marginBottom: 8, fontSize: 14 },
  card: {
    borderWidth: 1,
    borderColor: '#e5e7eb',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  },
  cardCategory: { fontSize: 12, color: '#7c3aed', marginBottom: 4 },
  cardTitle: { fontSize: 18, fontWeight: '700', marginBottom: 4 },
  cardQuestion: { fontSize: 16, color: '#333' },
  inputRow: { gap: 8, marginTop: 8 },
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
  reveal: { marginTop: 16, gap: 8 },
  revealLabel: { fontSize: 12, color: '#666' },
  revealContent: { fontSize: 15, color: '#333', marginBottom: 12 },
  waiting: { marginTop: 16 },
});
