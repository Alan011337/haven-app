// frontend/src/hooks/use-auth.ts

import { useContext } from 'react';
// 引入剛剛上面的 Context
import { AuthContext, AuthContextType } from '@/contexts/AuthContext';

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);

  // 防呆機制：如果你忘記在 layout.tsx 包 <AuthProvider>，這裡會報錯提醒你
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }

  return context;
};