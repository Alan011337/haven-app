export type SocketConnectionState =
  | 'idle'
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'fallback';

export type SocketConnectionEvent =
  | 'connect_start'
  | 'connect_open'
  | 'reconnect_scheduled'
  | 'fallback_enabled'
  | 'disposed';

export const INITIAL_SOCKET_STATE: SocketConnectionState = 'idle';

export function transitionSocketConnectionState(
  current: SocketConnectionState,
  event: SocketConnectionEvent
): SocketConnectionState {
  switch (event) {
    case 'connect_start':
      return 'connecting';
    case 'connect_open':
      return 'connected';
    case 'reconnect_scheduled':
      if (current === 'fallback') {
        return 'fallback';
      }
      return 'reconnecting';
    case 'fallback_enabled':
      return 'fallback';
    case 'disposed':
      return 'idle';
    default:
      return current;
  }
}
