/**
 * Cross-platform Haven editorial design tokens.
 * Web remains the visual source of truth; native consumes these distilled values.
 */

export const havenEditorialTokens = {
  color: {
    background: '#F8F3ED',
    backgroundMuted: '#F2EAE1',
    surface: '#FFFBF6',
    surfaceSecondary: '#F7EFE6',
    surfaceElevated: '#FFF8F1',
    foreground: '#352C26',
    foregroundMuted: '#7B6D62',
    foregroundSoft: '#9E9185',
    primary: '#C7A173',
    primaryStrong: '#B78B59',
    primarySoft: '#EFE2D0',
    accent: '#8E9C8D',
    accentSoft: '#E5ECE3',
    border: '#E7DBCF',
    borderStrong: '#D8C7B7',
    danger: '#B86460',
    dangerSoft: '#F7E5E2',
    heroBase: '#4E4036',
    heroGlow: '#E2C198',
    inkInverse: '#FFF8F1',
    overlay: 'rgba(53, 44, 38, 0.04)',
  },
  spacing: {
    xxs: 4,
    xs: 8,
    sm: 12,
    md: 16,
    lg: 24,
    xl: 32,
    xxl: 48,
  },
  radius: {
    sm: 12,
    md: 18,
    lg: 24,
    xl: 32,
    pill: 999,
  },
  motion: {
    fast: 180,
    normal: 240,
    slow: 340,
    ritual: 520,
  },
  typography: {
    display: 34,
    title: 24,
    body: 16,
    caption: 13,
    eyebrow: 11,
  },
} as const;

export type HavenEditorialTokens = typeof havenEditorialTokens;
