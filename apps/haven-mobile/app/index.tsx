import { useEffect, useState } from 'react';
import { StyleSheet, Text, TextInput, TouchableOpacity, View, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import { HavenApiNative, clearToken } from '../api/HavenApiNative';
import { getStoredToken } from '../api/auth';
import type { Journal } from 'haven-shared';

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
    loadJournals();
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
      <View style={styles.centered}>
        <ActivityIndicator size="large" />
        <Text style={styles.hint}>載入日記…</Text>
      </View>
    );
  }

  if (needsLogin) {
    return (
      <View style={styles.centered}>
        <Text style={styles.hint}>請先登入以查看與撰寫日記</Text>
        <TouchableOpacity style={styles.button} onPress={() => router.push('/login')}>
          <Text style={styles.buttonText}>前往登入</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.inputRow}>
        <TextInput
          style={styles.input}
          placeholder="今天發生了什麼事？"
          placeholderTextColor="#999"
          value={content}
          onChangeText={setContent}
          multiline
          maxLength={4000}
          editable={!submitting}
        />
        <TouchableOpacity
          style={[styles.button, submitting && styles.buttonDisabled]}
          onPress={handleCreate}
          disabled={submitting || !content.trim()}
        >
          <Text style={styles.buttonText}>{submitting ? '送出中…' : '發布'}</Text>
        </TouchableOpacity>
      </View>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <View style={styles.topRow}>
        <View style={styles.navLinks}>
          <TouchableOpacity style={styles.linkBtn} onPress={() => router.push('/daily')}>
            <Text style={styles.linkBtnText}>今日抽卡</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.linkBtn} onPress={() => router.push('/deck')}>
            <Text style={styles.linkBtnText}>牌組</Text>
          </TouchableOpacity>
        </View>
        <TouchableOpacity
          style={styles.logoutBtn}
          onPress={async () => {
            await clearToken();
            setNeedsLogin(true);
          }}
        >
          <Text style={styles.logoutBtnText}>登出</Text>
        </TouchableOpacity>
      </View>
      <Text style={styles.sectionTitle}>我的日記</Text>
      {journals.length === 0 ? (
        <Text style={styles.hint}>尚無日記，寫下第一則吧</Text>
      ) : (
        journals.map((j) => (
          <View key={j.id} style={styles.card}>
            <Text style={styles.cardDate}>{new Date(j.created_at).toLocaleDateString('zh-TW')}</Text>
            <Text style={styles.cardContent} numberOfLines={3}>{j.content}</Text>
          </View>
        ))
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
    padding: 16,
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 12,
  },
  hint: {
    color: '#666',
    fontSize: 14,
  },
  inputRow: {
    flexDirection: 'row',
    gap: 8,
    alignItems: 'flex-end',
    marginBottom: 8,
  },
  input: {
    flex: 1,
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
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 8,
    justifyContent: 'center',
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: '#fff',
    fontWeight: '600',
  },
  error: {
    color: '#b91c1c',
    marginBottom: 8,
    fontSize: 14,
  },
  topRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  navLinks: { flexDirection: 'row', gap: 16 },
  linkBtn: { paddingVertical: 6, paddingHorizontal: 0 },
  linkBtnText: { color: '#7c3aed', fontSize: 14, fontWeight: '600' },
  logoutBtn: { paddingVertical: 6, paddingHorizontal: 12 },
  logoutBtnText: { color: '#666', fontSize: 14 },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    marginTop: 16,
    marginBottom: 8,
  },
  card: {
    borderWidth: 1,
    borderColor: '#eee',
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
  },
  cardDate: {
    fontSize: 12,
    color: '#666',
    marginBottom: 4,
  },
  cardContent: {
    fontSize: 15,
    color: '#333',
  },
});
