import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';

export default function RootLayout() {
  return (
    <>
      <StatusBar style="auto" />
      <Stack screenOptions={{ headerShown: true }}>
        <Stack.Screen name="index" options={{ title: 'Haven' }} />
        <Stack.Screen name="login" options={{ title: '登入' }} />
        <Stack.Screen name="daily" options={{ title: '今日抽卡' }} />
        <Stack.Screen name="deck" options={{ title: '牌組' }} />
      </Stack>
    </>
  );
}
