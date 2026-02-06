/**
 * Custom hook for WebSocket connection to parking feed.
 */
import { useState, useEffect, useRef, useCallback } from 'react';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

export function useParkingWebSocket() {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const [zoneUpdates, setZoneUpdates] = useState({});
  const [events, setEvents] = useState([]);
  const wsRef = useRef(null);
  const reconnectTimer = useRef(null);

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(`${WS_URL}/ws/parking`);

      ws.onopen = () => {
        setIsConnected(true);
        console.log('WebSocket connected');
      };

      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        setLastMessage(message);

        switch (message.type) {
          case 'zone_update':
            setZoneUpdates((prev) => ({
              ...prev,
              [message.data.zone_code]: message.data,
            }));
            break;
          case 'event':
            setEvents((prev) => [message.data, ...prev].slice(0, 50));
            break;
          case 'alert':
            console.warn('Parking alert:', message.data);
            break;
          default:
            break;
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        console.log('WebSocket disconnected, reconnecting...');
        reconnectTimer.current = setTimeout(connect, 3000);
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        ws.close();
      };

      wsRef.current = ws;
    } catch (err) {
      console.error('WebSocket connection failed:', err);
      reconnectTimer.current = setTimeout(connect, 5000);
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const subscribe = useCallback((zoneIds) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'subscribe', zones: zoneIds }));
    }
  }, []);

  return { isConnected, lastMessage, zoneUpdates, events, subscribe };
}
