import { Platform, type TextStyle, type ViewStyle } from 'react-native';
import { havenEditorialTokens } from 'haven-shared';

export const mobileTheme = {
  colors: havenEditorialTokens.color,
  spacing: havenEditorialTokens.spacing,
  radius: havenEditorialTokens.radius,
  motion: havenEditorialTokens.motion,
  typography: {
    display: {
      fontFamily: Platform.select({ ios: 'Georgia', android: 'serif', default: 'serif' }),
      fontSize: havenEditorialTokens.typography.display,
      lineHeight: 40,
      fontWeight: '700' as TextStyle['fontWeight'],
      color: havenEditorialTokens.color.foreground,
    },
    title: {
      fontFamily: Platform.select({ ios: 'Georgia', android: 'serif', default: 'serif' }),
      fontSize: havenEditorialTokens.typography.title,
      lineHeight: 30,
      fontWeight: '700' as TextStyle['fontWeight'],
      color: havenEditorialTokens.color.foreground,
    },
    body: {
      fontFamily: Platform.select({ ios: 'System', android: 'sans-serif', default: 'System' }),
      fontSize: havenEditorialTokens.typography.body,
      lineHeight: 24,
      color: havenEditorialTokens.color.foreground,
    },
    bodyMuted: {
      fontFamily: Platform.select({ ios: 'System', android: 'sans-serif', default: 'System' }),
      fontSize: havenEditorialTokens.typography.body,
      lineHeight: 24,
      color: havenEditorialTokens.color.foregroundMuted,
    },
    caption: {
      fontFamily: Platform.select({ ios: 'System', android: 'sans-serif', default: 'System' }),
      fontSize: havenEditorialTokens.typography.caption,
      lineHeight: 18,
      color: havenEditorialTokens.color.foregroundMuted,
    },
    eyebrow: {
      fontFamily: Platform.select({ ios: 'System', android: 'sans-serif-medium', default: 'System' }),
      fontSize: havenEditorialTokens.typography.eyebrow,
      lineHeight: 16,
      letterSpacing: 1.4,
      textTransform: 'uppercase' as TextStyle['textTransform'],
      color: havenEditorialTokens.color.foregroundSoft,
    },
  },
} as const;

export function hexToRgba(hex: string, alpha: number): string {
  const normalized = hex.replace('#', '');
  const value = normalized.length === 3
    ? normalized.split('').map((part) => part + part).join('')
    : normalized;
  const int = Number.parseInt(value, 16);
  const r = (int >> 16) & 255;
  const g = (int >> 8) & 255;
  const b = int & 255;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export function editorialShadow(level: 'soft' | 'lift' = 'soft'): ViewStyle {
  if (Platform.OS === 'android') {
    return {
      elevation: level === 'soft' ? 3 : 7,
      shadowColor: mobileTheme.colors.foreground,
    };
  }

  if (level === 'lift') {
    return {
      shadowColor: '#5C4738',
      shadowOffset: { width: 0, height: 14 },
      shadowOpacity: 0.16,
      shadowRadius: 28,
    };
  }

  return {
    shadowColor: '#5C4738',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.1,
    shadowRadius: 18,
  };
}
