// frontend/src/hooks/useSocket.ts

import { useEffect, useRef } from 'react';

const HEARTBEAT_INTERVAL_MS = 25_000;
const BASE_RETRY_DELAY_MS = 1_000;
const MAX_RETRY_DELAY_MS = 15_000;

const trimTrailingSlash = (value: string): string => value.replace(/\/+$/, '');

const resolveWebSocketBaseUrl = (): string => {
  const rawWsUrl = process.env.NEXT_PUBLIC_WS_URL?.trim();
  if (rawWsUrl) {
    return trimTrailingSlash(rawWsUrl);
  }

  const rawApiUrl = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (rawApiUrl && typeof window !== 'undefined') {
    try {
      const apiUrl = new URL(rawApiUrl, window.location.origin);
      const wsProtocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:';
      return `${wsProtocol}//${apiUrl.host}`;
    } catch {
      // Ignore malformed NEXT_PUBLIC_API_URL and fallback below.
    }
  }

  if (typeof window !== 'undefined') {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${wsProtocol}//${window.location.host}`;
  }

  return 'ws://localhost:8000';
};

/**
 * 穩定版 WebSocket Hook
 * 特點：使用 useRef 隔離 callback 的變化，避免因為畫面渲染導致 WebSocket 不斷重連
 */
const useSocket = (
  userId: string | undefined | null, 
  onMessage: (data: Record<string, unknown>) => void,
  onPartnerAction?: (data: Record<string, unknown>) => void
) => {
  // 1. 使用 Ref 保存 Socket 實體，確保跨渲染週期存活
  const socketRef = useRef<WebSocket | null>(null);

  // 2. 使用 Ref 保存最新的 callback 函式
  // 這樣做的目的是：即使外部的 onMessage 函式改變了，我們也不需要斷開 WebSocket 重連
  const onMessageRef = useRef(onMessage);
  const onPartnerActionRef = useRef(onPartnerAction);

  // 隨時更新最新的 callback 到 Ref 中
  useEffect(() => {
    onMessageRef.current = onMessage;
    onPartnerActionRef.current = onPartnerAction;
  }, [onMessage, onPartnerAction]);

  // 3. 建立連線的主邏輯 (只依賴 userId)
  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    // 防呆：沒有 ID 就不要連
    if (!userId) {
      console.log("⏳ [WebSocket] 等待使用者登入...");
      return;
    }
    const token = localStorage.getItem('token');
    if (!token) {
      console.warn('⏳ [WebSocket] 找不到 token，暫不建立連線。');
      return;
    }

    const wsBaseUrl = resolveWebSocketBaseUrl();
    let disposed = false;
    let retryCount = 0;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let heartbeatTimer: ReturnType<typeof setInterval> | null = null;

    const clearHeartbeat = () => {
      if (heartbeatTimer) {
        clearInterval(heartbeatTimer);
        heartbeatTimer = null;
      }
    };

    const clearReconnect = () => {
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
    };

    const scheduleReconnect = () => {
      clearReconnect();
      if (disposed) {
        return;
      }
      const delay = Math.min(BASE_RETRY_DELAY_MS * 2 ** retryCount, MAX_RETRY_DELAY_MS);
      retryCount += 1;
      reconnectTimer = setTimeout(() => {
        connect();
      }, delay);
      console.info(`🔁 [WebSocket] ${delay}ms 後重連...`);
    };

    const connect = () => {
      if (disposed) {
        return;
      }

      const latestToken = localStorage.getItem('token');
      if (!latestToken) {
        console.warn('⏳ [WebSocket] token 遺失，停止重連。');
        return;
      }

      const targetUrl = `${wsBaseUrl}/ws/${userId}?token=${encodeURIComponent(latestToken)}`;
      console.log(`🔌 [WebSocket] 正在連線至: ${targetUrl}`);

      const socket = new WebSocket(targetUrl);
      socketRef.current = socket;

      socket.onopen = () => {
        retryCount = 0;
        clearReconnect();
        clearHeartbeat();

        heartbeatTimer = setInterval(() => {
          if (socket.readyState === WebSocket.OPEN) {
            socket.send('ping');
          }
        }, HEARTBEAT_INTERVAL_MS);
        console.log('✅ [WebSocket] 連線成功！');
      };

      socket.onmessage = (event) => {
        if (event.data === 'pong') {
          return;
        }

        try {
          const data = JSON.parse(event.data);
          const eventType = typeof data.event === 'string' ? data.event : '';
          if (
            eventType === 'PARTNER_ACTION' ||
            eventType === 'NEW_CARD_PICKED' ||
            eventType === 'PARTNER_TYPING'
          ) {
            onPartnerActionRef.current?.(data);
          } else {
            onMessageRef.current?.(data);
          }
        } catch (error) {
          console.error('⚠️ [WebSocket] 解析訊息失敗:', error);
        }
      };

      socket.onerror = () => {
        console.error('❌ [WebSocket] 發生錯誤。');
      };

      socket.onclose = (event) => {
        clearHeartbeat();
        console.log(`👋 [WebSocket] 連線已關閉 (Code: ${event.code})`);
        if (disposed) {
          return;
        }

        // 1008 通常是驗證失敗，不做無限重連。
        if (event.code === 1008) {
          console.warn('⛔ [WebSocket] 驗證失敗，停止重連。');
          return;
        }
        scheduleReconnect();
      };
    };

    connect();

    // 清理機制：當 userId 改變或元件卸載時，才真正關閉連線
    return () => {
      disposed = true;
      clearHeartbeat();
      clearReconnect();
      const socket = socketRef.current;
      if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
        console.log('🛑 [WebSocket] 切斷舊連線');
        socket.close();
      }
    };
  }, [userId]); // 🔥 這裡的依賴陣列只有 userId！這是穩定的關鍵！

  return socketRef;
};

export default useSocket;
