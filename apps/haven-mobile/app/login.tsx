import { useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Feather } from '@expo/vector-icons';
import { login } from '../api/auth';
import { BrandScreen } from '../components/BrandScreen';
import {
  EditorialButton,
  EditorialCard,
  EditorialInput,
  FadeUpView,
  InlineError,
  StatusPill,
} from '../components/BrandPrimitives';
import { mobileTheme } from '../theme/editorial';

export default function LoginScreen() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async () => {
    const e = email.trim();
    const p = password;
    if (!e || !p) {
      setError('請輸入 Email 與密碼');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      await login(e, p);
      router.replace('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : '登入失敗');
    } finally {
      setLoading(false);
    }
  };

  return (
    <BrandScreen scroll={false} centered>
      <KeyboardAvoidingView
        style={styles.keyboardWrap}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <FadeUpView>
          <View style={styles.brandIntro}>
            <StatusPill label="Private Couple Journal" />
            <Text style={styles.title}>回到 Haven</Text>
            <Text style={styles.subtitle}>
              讓今天的情緒、想念與對話，都有一個安靜而精緻的容器。
            </Text>
          </View>
        </FadeUpView>

        <FadeUpView delay={80}>
          <EditorialCard style={styles.card}>
            <View style={styles.iconBadge}>
              <Feather name="heart" size={20} color={mobileTheme.colors.primaryStrong} />
            </View>

            {error ? <InlineError message={error} /> : null}

            <EditorialInput
              label="Email"
              placeholder="user@example.com"
              keyboardType="email-address"
              autoCapitalize="none"
              autoCorrect={false}
              editable={!loading}
              value={email}
              onChangeText={setEmail}
            />
            <EditorialInput
              label="密碼"
              placeholder="請輸入密碼"
              secureTextEntry
              editable={!loading}
              value={password}
              onChangeText={setPassword}
            />

            <EditorialButton
              label={loading ? '登入中…' : '登入 Haven'}
              loading={loading}
              onPress={handleLogin}
            />
          </EditorialCard>
        </FadeUpView>
      </KeyboardAvoidingView>
    </BrandScreen>
  );
}

const styles = StyleSheet.create({
  keyboardWrap: {
    gap: mobileTheme.spacing.lg,
  },
  brandIntro: {
    gap: mobileTheme.spacing.sm,
  },
  title: {
    ...mobileTheme.typography.display,
  },
  subtitle: {
    ...mobileTheme.typography.bodyMuted,
    maxWidth: 320,
  },
  card: {
    gap: mobileTheme.spacing.md,
  },
  iconBadge: {
    width: 48,
    height: 48,
    borderRadius: mobileTheme.radius.lg,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: mobileTheme.colors.primarySoft,
    marginBottom: mobileTheme.spacing.xs,
  },
});
