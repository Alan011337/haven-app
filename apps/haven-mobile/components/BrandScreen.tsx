import { useEffect, useRef } from 'react';
import {
  Animated,
  Easing,
  ScrollView,
  StyleSheet,
  Text,
  View,
  type StyleProp,
  type ViewStyle,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { mobileTheme, hexToRgba } from '../theme/editorial';

interface BrandScreenProps {
  children: React.ReactNode;
  eyebrow?: string;
  title?: string;
  subtitle?: string;
  scroll?: boolean;
  centered?: boolean;
  contentContainerStyle?: StyleProp<ViewStyle>;
}

export function BrandScreen({
  children,
  eyebrow,
  title,
  subtitle,
  scroll = true,
  centered = false,
  contentContainerStyle,
}: BrandScreenProps) {
  const glowScale = useRef(new Animated.Value(0.96)).current;

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(glowScale, {
          toValue: 1.04,
          duration: 4200,
          easing: Easing.inOut(Easing.sin),
          useNativeDriver: true,
        }),
        Animated.timing(glowScale, {
          toValue: 0.96,
          duration: 4200,
          easing: Easing.inOut(Easing.sin),
          useNativeDriver: true,
        }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [glowScale]);

  const header = title ? (
    <View style={styles.header}>
      {eyebrow ? <Text style={styles.eyebrow}>{eyebrow}</Text> : null}
      <Text style={styles.title}>{title}</Text>
      {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
    </View>
  ) : null;

  const body = (
    <>
      {header}
      {children}
    </>
  );

  return (
    <SafeAreaView style={styles.safeArea} edges={['top', 'left', 'right', 'bottom']}>
      <View style={styles.backdrop}>
        <View style={[styles.orb, styles.orbWarm]} />
        <View style={[styles.orb, styles.orbSage]} />
        <Animated.View style={[styles.orb, styles.orbGlow, { transform: [{ scale: glowScale }] }]} />
      </View>

      {scroll ? (
        <ScrollView
          style={styles.scroll}
          contentContainerStyle={[
            styles.scrollContent,
            centered && styles.centeredContent,
            contentContainerStyle,
          ]}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          {body}
        </ScrollView>
      ) : (
        <View style={[styles.staticContent, centered && styles.centeredContent, contentContainerStyle]}>
          {body}
        </View>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: mobileTheme.colors.background,
  },
  backdrop: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: mobileTheme.colors.background,
  },
  orb: {
    position: 'absolute',
    borderRadius: 999,
  },
  orbWarm: {
    width: 260,
    height: 260,
    top: -24,
    right: -36,
    backgroundColor: hexToRgba(mobileTheme.colors.primary, 0.12),
  },
  orbSage: {
    width: 220,
    height: 220,
    bottom: 120,
    left: -42,
    backgroundColor: hexToRgba(mobileTheme.colors.accent, 0.11),
  },
  orbGlow: {
    width: 180,
    height: 180,
    top: '38%',
    right: 24,
    backgroundColor: hexToRgba(mobileTheme.colors.heroGlow, 0.12),
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: mobileTheme.spacing.lg,
    paddingTop: mobileTheme.spacing.lg,
    paddingBottom: mobileTheme.spacing.xxl,
    gap: mobileTheme.spacing.lg,
  },
  staticContent: {
    flex: 1,
    paddingHorizontal: mobileTheme.spacing.lg,
    paddingTop: mobileTheme.spacing.lg,
    paddingBottom: mobileTheme.spacing.xxl,
    gap: mobileTheme.spacing.lg,
  },
  centeredContent: {
    justifyContent: 'center',
  },
  header: {
    marginBottom: mobileTheme.spacing.md,
    gap: mobileTheme.spacing.xs,
  },
  eyebrow: {
    ...mobileTheme.typography.eyebrow,
  },
  title: {
    ...mobileTheme.typography.display,
  },
  subtitle: {
    ...mobileTheme.typography.bodyMuted,
    maxWidth: 320,
  },
});
