import { useEffect, useRef } from 'react';
import {
  ActivityIndicator,
  Animated,
  Easing,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
  type PressableProps,
  type StyleProp,
  type TextInputProps,
  type TextStyle,
  type ViewStyle,
} from 'react-native';
import { mobileTheme, editorialShadow, hexToRgba } from '../theme/editorial';

type ButtonVariant = 'primary' | 'secondary' | 'ghost';

interface EditorialButtonProps extends Omit<PressableProps, 'style'> {
  label: string;
  loading?: boolean;
  variant?: ButtonVariant;
  style?: StyleProp<ViewStyle>;
  textStyle?: StyleProp<TextStyle>;
}

export function FadeUpView({
  children,
  delay = 0,
  style,
}: {
  children: React.ReactNode;
  delay?: number;
  style?: StyleProp<ViewStyle>;
}) {
  const opacity = useRef(new Animated.Value(0)).current;
  const translateY = useRef(new Animated.Value(16)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(opacity, {
        toValue: 1,
        duration: mobileTheme.motion.slow,
        delay,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: true,
      }),
      Animated.timing(translateY, {
        toValue: 0,
        duration: mobileTheme.motion.slow,
        delay,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: true,
      }),
    ]).start();
  }, [delay, opacity, translateY]);

  return (
    <Animated.View style={[style, { opacity, transform: [{ translateY }] }]}>
      {children}
    </Animated.View>
  );
}

export function EditorialCard({
  children,
  style,
}: {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
}) {
  return <View style={[styles.card, style]}>{children}</View>;
}

export function EditorialButton({
  label,
  loading = false,
  disabled,
  variant = 'primary',
  style,
  textStyle,
  ...rest
}: EditorialButtonProps) {
  const isDisabled = Boolean(disabled || loading);
  return (
    <Pressable
      accessibilityRole="button"
      disabled={isDisabled}
      style={({ pressed }) => [
        styles.button,
        buttonVariants[variant],
        isDisabled && styles.buttonDisabled,
        pressed && !isDisabled && styles.buttonPressed,
        style,
      ]}
      {...rest}
    >
      {loading ? (
        <ActivityIndicator color={variant === 'primary' ? mobileTheme.colors.inkInverse : mobileTheme.colors.foreground} />
      ) : (
        <Text style={[styles.buttonLabel, buttonTextVariants[variant], textStyle]}>{label}</Text>
      )}
    </Pressable>
  );
}

interface EditorialInputProps extends TextInputProps {
  label: string;
  hint?: string | null;
  error?: string | null;
}

export function EditorialInput({
  label,
  hint,
  error,
  style,
  ...rest
}: EditorialInputProps) {
  return (
    <View style={styles.fieldWrap}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <TextInput
        placeholderTextColor={hexToRgba(mobileTheme.colors.foregroundMuted, 0.75)}
        style={[styles.input, error ? styles.inputError : null, style]}
        {...rest}
      />
      {error ? <Text style={styles.errorText}>{error}</Text> : hint ? <Text style={styles.hintText}>{hint}</Text> : null}
    </View>
  );
}

export function InlineError({ message }: { message: string }) {
  return (
    <View style={styles.errorBanner}>
      <Text style={styles.errorBannerText}>{message}</Text>
    </View>
  );
}

export function StatusPill({
  label,
  tone = 'warm',
}: {
  label: string;
  tone?: 'warm' | 'sage' | 'muted';
}) {
  return (
    <View style={[styles.pill, pillVariants[tone]]}>
      <Text style={[styles.pillLabel, pillTextVariants[tone]]}>{label}</Text>
    </View>
  );
}

export function SectionHeading({
  eyebrow,
  title,
  meta,
}: {
  eyebrow?: string;
  title: string;
  meta?: string;
}) {
  return (
    <View style={styles.sectionHeader}>
      <View style={styles.sectionHeaderText}>
        {eyebrow ? <Text style={styles.sectionEyebrow}>{eyebrow}</Text> : null}
        <Text style={styles.sectionTitle}>{title}</Text>
      </View>
      {meta ? <StatusPill label={meta} tone="muted" /> : null}
    </View>
  );
}

const buttonVariants = StyleSheet.create({
  primary: {
    backgroundColor: mobileTheme.colors.primaryStrong,
    borderColor: mobileTheme.colors.primaryStrong,
  },
  secondary: {
    backgroundColor: mobileTheme.colors.surfaceElevated,
    borderColor: mobileTheme.colors.borderStrong,
  },
  ghost: {
    backgroundColor: 'transparent',
    borderColor: 'transparent',
    paddingHorizontal: mobileTheme.spacing.md,
  },
});

const buttonTextVariants = StyleSheet.create({
  primary: {
    color: mobileTheme.colors.inkInverse,
  },
  secondary: {
    color: mobileTheme.colors.foreground,
  },
  ghost: {
    color: mobileTheme.colors.foregroundMuted,
  },
});

const pillVariants = StyleSheet.create({
  warm: {
    backgroundColor: mobileTheme.colors.primarySoft,
    borderColor: hexToRgba(mobileTheme.colors.primaryStrong, 0.22),
  },
  sage: {
    backgroundColor: mobileTheme.colors.accentSoft,
    borderColor: hexToRgba(mobileTheme.colors.accent, 0.25),
  },
  muted: {
    backgroundColor: hexToRgba(mobileTheme.colors.foreground, 0.04),
    borderColor: hexToRgba(mobileTheme.colors.foregroundMuted, 0.12),
  },
});

const pillTextVariants = StyleSheet.create({
  warm: {
    color: mobileTheme.colors.primaryStrong,
  },
  sage: {
    color: mobileTheme.colors.accent,
  },
  muted: {
    color: mobileTheme.colors.foregroundMuted,
  },
});

const styles = StyleSheet.create({
  card: {
    backgroundColor: hexToRgba(mobileTheme.colors.surface, 0.92),
    borderRadius: mobileTheme.radius.lg,
    borderWidth: 1,
    borderColor: hexToRgba(mobileTheme.colors.borderStrong, 0.72),
    padding: mobileTheme.spacing.lg,
    gap: mobileTheme.spacing.sm,
    ...editorialShadow('soft'),
  },
  button: {
    minHeight: 52,
    borderRadius: mobileTheme.radius.pill,
    paddingHorizontal: mobileTheme.spacing.lg,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
    ...editorialShadow('soft'),
  },
  buttonPressed: {
    transform: [{ scale: 0.985 }],
    opacity: 0.96,
  },
  buttonDisabled: {
    opacity: 0.65,
  },
  buttonLabel: {
    ...mobileTheme.typography.body,
    fontWeight: '700',
    letterSpacing: 0.2,
  },
  fieldWrap: {
    gap: mobileTheme.spacing.xs,
  },
  fieldLabel: {
    ...mobileTheme.typography.eyebrow,
    color: mobileTheme.colors.foregroundSoft,
  },
  input: {
    minHeight: 54,
    borderRadius: mobileTheme.radius.md,
    borderWidth: 1,
    borderColor: mobileTheme.colors.border,
    backgroundColor: hexToRgba(mobileTheme.colors.surfaceElevated, 0.96),
    paddingHorizontal: mobileTheme.spacing.md,
    paddingVertical: mobileTheme.spacing.sm,
    color: mobileTheme.colors.foreground,
    fontSize: mobileTheme.typography.body.fontSize,
    lineHeight: mobileTheme.typography.body.lineHeight,
  },
  inputError: {
    borderColor: hexToRgba(mobileTheme.colors.danger, 0.55),
    backgroundColor: mobileTheme.colors.dangerSoft,
  },
  hintText: {
    ...mobileTheme.typography.caption,
  },
  errorText: {
    ...mobileTheme.typography.caption,
    color: mobileTheme.colors.danger,
  },
  errorBanner: {
    backgroundColor: mobileTheme.colors.dangerSoft,
    borderRadius: mobileTheme.radius.md,
    borderWidth: 1,
    borderColor: hexToRgba(mobileTheme.colors.danger, 0.2),
    paddingHorizontal: mobileTheme.spacing.md,
    paddingVertical: mobileTheme.spacing.sm,
  },
  errorBannerText: {
    ...mobileTheme.typography.caption,
    color: mobileTheme.colors.danger,
  },
  pill: {
    borderRadius: mobileTheme.radius.pill,
    borderWidth: 1,
    paddingHorizontal: mobileTheme.spacing.sm,
    paddingVertical: 6,
    alignSelf: 'flex-start',
  },
  pillLabel: {
    ...mobileTheme.typography.eyebrow,
    letterSpacing: 0.9,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: mobileTheme.spacing.md,
  },
  sectionHeaderText: {
    flexShrink: 1,
    gap: 4,
  },
  sectionEyebrow: {
    ...mobileTheme.typography.eyebrow,
  },
  sectionTitle: {
    ...mobileTheme.typography.title,
    fontSize: 20,
    lineHeight: 26,
  },
});
