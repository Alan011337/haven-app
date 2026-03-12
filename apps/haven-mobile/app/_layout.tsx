import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { Platform } from 'react-native';
import { mobileTheme } from '../theme/editorial';

export default function RootLayout() {
  return (
    <>
      <StatusBar style="dark" />
      <Stack
        screenOptions={{
          headerShown: true,
          headerShadowVisible: false,
          headerTintColor: mobileTheme.colors.foreground,
          headerStyle: {
            backgroundColor: mobileTheme.colors.backgroundMuted,
          },
          headerTitleStyle: {
            color: mobileTheme.colors.foreground,
            fontFamily: Platform.select({ ios: 'Georgia', android: 'serif', default: 'serif' }),
            fontSize: 18,
            fontWeight: '700',
          },
          contentStyle: {
            backgroundColor: mobileTheme.colors.background,
          },
        }}
      >
        <Stack.Screen
          name="index"
          options={{
            title: 'Haven',
            headerLargeTitle: Platform.OS === 'ios',
          }}
        />
        <Stack.Screen name="login" options={{ title: '登入', headerShown: false }} />
        <Stack.Screen name="daily" options={{ title: '每日共感' }} />
        <Stack.Screen name="deck" options={{ title: '牌組圖書館' }} />
      </Stack>
    </>
  );
}
