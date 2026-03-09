// frontend/src/hooks/useSocket.ts

import { useEffect, useRef } from 'react';
import { logClientError } from '@/lib/safe-error-log';
import { capturePosthogEvent } from '@/lib/posthog';
import { emitRealtimeFallback } from '@/lib/realtime-policy';
import {
  classifyDisconnectReason,
  computeReconnectDelayMs,
  resolveReconnectCap,
} from '@/hooks/socket-reconnect-policy';
import {
  INITIAL_SOCKET_STATE,
  transitionSocketConnectionState,
} from '@/hooks/socket-connection-state';

const isDev = typeof process !== 'undefined' && process.env.NODE_ENV === 'development';
const devLog = (...args: unknown[]) => {
  if (isDev) {
    console.log(...args);
  }
};
const devWarn = (...args: unknown[]) => {
  if (isDev) {
    console.warn(...args);
  }
};
const devInfo = (...args: unknown[]) => {
  if (isDev) {
    console.info(...args);
  }
};

const HEARTBEAT_INTERVAL_MS = 25_000;
const DEFAULT_MAX_RECONNECT_ATTEMPTS = 8;

const trimTrailingSlash = (value: string): string => value.replace(/\/+$/, '');

const resolveWsEndpointForLog = (wsBaseUrl: string): string => {
  try {
    const parsed = new URL(wsBaseUrl);
    return `${parsed.protocol}//${parsed.host}/ws/:user_id`;
  } catch {
    return '/ws/:user_id';
  }
};

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

const resolveReconnectLimit = (): number => {
  const raw = (process.env.NEXT_PUBLIC_WS_MAX_RECONNECT_ATTEMPTS || '').trim();
  const parsed = Number(raw);
  if (!Number.isFinite(parsed)) {
    return DEFAULT_MAX_RECONNECT_ATTEMPTS;
  }
  return Math.max(1, Math.min(20, Math.floor(parsed)));
};

const wsRealtimeEnabled = (): boolean => {
  const raw = (process.env.NEXT_PUBLIC_WEBSOCKET_ENABLED || '').trim().toLowerCase();
  if (!raw) return true;
  return !['0', 'false', 'off', 'no'].includes(raw);
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
  const lastReceivedWsSeqRef = useRef(0);
  const connectionStateRef = useRef(INITIAL_SOCKET_STATE);

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

    if (!wsRealtimeEnabled()) {
      connectionStateRef.current = transitionSocketConnectionState(
        connectionStateRef.current,
        'fallback_enabled',
      );
      emitRealtimeFallback(true, 'feature_disabled');
      return;
    }

    // 防呆：沒有 ID 就不要連
    if (!userId) {
      devLog("⏳ [WebSocket] 等待使用者登入...");
      return;
    }
    // ✅ httpOnly Cookie 自動被瀏覽器發送，無需 localStorage
    // 後端會優先從 Cookie 中讀取令牌

    const wsBaseUrl = resolveWebSocketBaseUrl();
    const maxReconnectAttempts = resolveReconnectLimit();
    let disposed = false;
    let retryCount = 0;
    let lastCloseCode = 1000;
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
      const reconnectCap = resolveReconnectCap(maxReconnectAttempts, lastCloseCode);
      const transientServerPressure = reconnectCap < maxReconnectAttempts;
      if (retryCount >= reconnectCap) {
        connectionStateRef.current = transitionSocketConnectionState(
          connectionStateRef.current,
          'fallback_enabled',
        );
        const fallbackReason = transientServerPressure
          ? 'max_reconnect_exceeded_server_pressure'
          : 'max_reconnect_exceeded';
        emitRealtimeFallback(true, fallbackReason, {
          reconnect_attempts: retryCount,
        });
        return;
      }
      const delay = computeReconnectDelayMs({
        retryCount,
        closeCode: lastCloseCode,
      });
      connectionStateRef.current = transitionSocketConnectionState(
        connectionStateRef.current,
        'reconnect_scheduled',
      );
      retryCount += 1;
      capturePosthogEvent('ws_reconnect_attempted', {
        attempt: retryCount,
        delay_ms: delay,
        close_code: lastCloseCode,
        strategy: transientServerPressure ? 'server_pressure' : 'default',
      });
      reconnectTimer = setTimeout(() => {
        connect();
      }, delay);
      devInfo(`🔁 [WebSocket] ${delay}ms 後重連...`);
    };

    const connect = () => {
      if (disposed) {
        return;
      }
      connectionStateRef.current = transitionSocketConnectionState(
        connectionStateRef.current,
        'connect_start',
      );

      // ✅ 令牌由 httpOnly Cookie 提供，後端自動讀取
      // 前端無需在 localStorage 中查詢

      // WebSocket 連接會自動帶上瀏覽器的 Cookie（包括 access_token）
      const targetUrl = `${wsBaseUrl}/ws/${userId}`;
      devLog(`[WebSocket] 正在連線至: ${resolveWsEndpointForLog(wsBaseUrl)}`);

      const socket = new WebSocket(targetUrl);
      socketRef.current = socket;

      socket.onopen = () => {
        // ✅ 令牌由 httpOnly Cookie 提供，後端自動從 Cookie 讀取
        // 不再需要在第一條消息中發送令牌

        retryCount = 0;
        lastReceivedWsSeqRef.current = 0;
        clearReconnect();
        clearHeartbeat();
        connectionStateRef.current = transitionSocketConnectionState(
          connectionStateRef.current,
          'connect_open',
        );
        emitRealtimeFallback(false, 'socket_recovered');
        capturePosthogEvent('ws_connected', { transport: 'websocket' });

        heartbeatTimer = setInterval(() => {
          if (socket.readyState === WebSocket.OPEN) {
            socket.send('ping');
          }
        }, HEARTBEAT_INTERVAL_MS);
        devLog('✅ [WebSocket] 連線成功！');
      };

      socket.onmessage = (event) => {
        if (event.data === 'pong') {
          return;
        }

        try {
          const data = JSON.parse(event.data);
          const wsSeq =
            typeof data?._ws_seq === 'number' && Number.isFinite(data._ws_seq)
              ? Math.floor(data._ws_seq)
              : null;
          if (wsSeq !== null) {
            if (wsSeq <= lastReceivedWsSeqRef.current) {
              return;
            }
            lastReceivedWsSeqRef.current = wsSeq;
          }
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
          logClientError('ws-parse-message-failed', error);
        }
      };

      socket.onerror = (event) => {
        const target = event?.target as WebSocket | undefined;
        if (target?.readyState !== WebSocket.CLOSED) {
          logClientError('ws-error', event);
        }
      };

      socket.onclose = (event) => {
        clearHeartbeat();
        lastCloseCode = event.code;
        devLog(`👋 [WebSocket] 連線已關閉 (Code: ${event.code})`);
        capturePosthogEvent('ws_disconnected', {
          close_code: event.code,
          reason_bucket: classifyDisconnectReason(event.code),
        });
        if (disposed) {
          return;
        }

        // 1008 通常是驗證失敗，不做無限重連。
        if (event.code === 1008) {
          devWarn('⛔ [WebSocket] 驗證失敗，停止重連。');
          connectionStateRef.current = transitionSocketConnectionState(
            connectionStateRef.current,
            'fallback_enabled',
          );
          emitRealtimeFallback(true, 'auth_or_policy');
          return;
        }
        scheduleReconnect();
      };
    };

    connect();

    // 清理機制：當 userId 改變或元件卸載時，才真正關閉連線
    return () => {
      disposed = true;
      connectionStateRef.current = transitionSocketConnectionState(
        connectionStateRef.current,
        'disposed',
      );
      clearHeartbeat();
      clearReconnect();
      const socket = socketRef.current;
      if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
        devLog('🛑 [WebSocket] 切斷舊連線');
        socket.close();
      }
    };
  }, [userId]); // 🔥 這裡的依賴陣列只有 userId！這是穩定的關鍵！

  return socketRef;
};

export default useSocket;
