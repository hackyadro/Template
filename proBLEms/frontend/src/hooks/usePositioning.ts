import { useState, useEffect, useCallback, useRef } from 'react';
import { RESTClient } from '@/api/rest-client';
import { WebSocketClient } from '@/api/websocket-client';
import type { Beacon, Position, SessionConfig, WebSocketMessage } from '@/types';
import { toast } from 'sonner';

export const usePositioning = () => {
  const [beacons, setBeacons] = useState<Beacon[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [currentPosition, setCurrentPosition] = useState<Position | undefined>();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionStatus, setSessionStatus] = useState<string>('No session');
  const [isLoading, setIsLoading] = useState(false);

  const restClientRef = useRef(new RESTClient());
  const wsClientRef = useRef(new WebSocketClient());

  // Load beacons on mount
  useEffect(() => {
    loadBeacons();
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      wsClientRef.current.disconnect();
    };
  }, []);

  const loadBeacons = async () => {
    try {
      setIsLoading(true);
      const beaconsData = await restClientRef.current.getBeacons();
      setBeacons(beaconsData);
      toast.success(`Loaded ${beaconsData.length} beacons`);
    } catch (error) {
      console.error('Failed to load beacons:', error);
      toast.error('Failed to load beacons');
    } finally {
      setIsLoading(false);
    }
  };

  const handleWebSocketMessage = useCallback((data: WebSocketMessage) => {
    console.log('WebSocket message:', data);

    switch (data.type) {
      case 'position_update':
        if (data.position) {
          setPositions(prev => [...prev, data.position!]);
          setCurrentPosition(data.position);
        }
        break;

      case 'session_status':
        if (data.status) {
          setSessionStatus(data.status);
          toast.info(`Session status: ${data.status}`);
        }
        break;

      case 'error':
        console.error('WebSocket error:', data.message);
        toast.error(data.message || 'An error occurred');
        setSessionStatus('error');
        break;
    }
  }, []);

  const startSession = async (frequency: number, beaconMapId: string) => {
    try {
      setIsLoading(true);
      const config: SessionConfig = { frequency, beaconMapId };
      const newSessionId = await restClientRef.current.startSession(config);
      
      setSessionId(newSessionId);
      setPositions([]);
      setCurrentPosition(undefined);
      setSessionStatus('started');

      // Connect WebSocket
      await wsClientRef.current.connect();
      wsClientRef.current.subscribe(newSessionId);
      wsClientRef.current.onMessage(handleWebSocketMessage);

      toast.success('Session started successfully');
    } catch (error) {
      console.error('Failed to start session:', error);
      toast.error('Failed to start session');
      setSessionStatus('error');
    } finally {
      setIsLoading(false);
    }
  };

  const stopSession = async () => {
    if (!sessionId) return;

    try {
      setIsLoading(true);
      await restClientRef.current.stopSession(sessionId);
      
      wsClientRef.current.unsubscribe(sessionId);
      wsClientRef.current.disconnect();

      setSessionStatus('stopped');
      toast.success('Session stopped');
    } catch (error) {
      console.error('Failed to stop session:', error);
      toast.error('Failed to stop session');
    } finally {
      setIsLoading(false);
    }
  };

  const savePath = async (fileName: string) => {
    if (!sessionId) {
      toast.error('No active session');
      return;
    }

    try {
      setIsLoading(true);
      await restClientRef.current.savePath(sessionId, fileName);
      toast.success(`Path saved as: ${fileName}`);
    } catch (error) {
      console.error('Failed to save path:', error);
      toast.error('Failed to save path');
    } finally {
      setIsLoading(false);
    }
  };

  return {
    beacons,
    positions,
    currentPosition,
    sessionStatus,
    isSessionActive: sessionStatus === 'started',
    isLoading,
    startSession,
    stopSession,
    savePath,
    loadBeacons
  };
};
