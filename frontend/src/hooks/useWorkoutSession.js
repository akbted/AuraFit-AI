import { useState, useRef, useCallback, useEffect } from 'react';

const API_BASE = 'http://localhost:8000';
const WS_BASE = 'ws://localhost:8000';

const FRAME_INTERVAL_MS = 150;
const JPEG_QUALITY = 0.5;
const TARGET_WIDTH = 480;
const TARGET_HEIGHT = 360;

export const useWorkoutSession = (exercise, inputVideoRef) => {
  const [sessionId, setSessionId] = useState(() => `session_${Date.now()}`);
  const [reps, setReps] = useState(0);
  const [sets, setSets] = useState(0);
  const [state, setState] = useState('UNKNOWN');
  const [feedback, setFeedback] = useState(['Position yourself in the frame.']);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSessionActive, setIsSessionActive] = useState(false);
  
  // Timed exercise state (for plank)
  const [exerciseType, setExerciseType] = useState('reps');
  const [currentTime, setCurrentTime] = useState(0);
  const [bestTime, setBestTime] = useState(0);
  const [totalTime, setTotalTime] = useState(0);
  
  const wsRef = useRef(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(document.createElement('canvas'));
  const streamRef = useRef(null);
  const frameIntervalRef = useRef(null);
  const isStreamingRef = useRef(false);

  // Reset session when exercise changes
  useEffect(() => {
    setSessionId(`session_${Date.now()}`);
    setReps(0);
    setSets(0);
    setState('UNKNOWN');
    setFeedback(['Position yourself in the frame.']);
    setConnected(false);
    setIsSessionActive(false);
    setCurrentTime(0);
    setBestTime(0);
    setTotalTime(0);
    
    // Determine exercise type
    setExerciseType(exercise === 'plank' ? 'timed' : 'reps');
  }, [exercise]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      isStreamingRef.current = false;
      if (frameIntervalRef.current) {
        clearInterval(frameIntervalRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  const connectWebSocket = useCallback(() => {
    return new Promise((resolve, reject) => {
      wsRef.current = new WebSocket(`${WS_BASE}/ws/exercise/${sessionId}`);
      
      wsRef.current.onopen = () => {
        console.log('WebSocket connected');
        setConnected(true);
        setError(null);
        resolve();
      };
      
      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'processed_frame') {
            setState(data.state);
            setSets(data.sets);
            
            if (data.feedback && data.feedback.length > 0) {
              setFeedback(data.feedback);
            }
            
            // Handle based on exercise type
            if (data.exercise_type === 'timed') {
              setCurrentTime(data.current_time || 0);
              setBestTime(data.best_time || 0);
              setTotalTime(data.total_time || 0);
            } else {
              setReps(data.reps || 0);
            }
            
            if (videoRef.current && data.frame) {
              if (data.frame.startsWith('data:')) {
                videoRef.current.src = data.frame;
              } else if (data.frame.startsWith('image/')) {
                videoRef.current.src = `data:${data.frame}`;
              } else {
                videoRef.current.src = `data:image/jpeg;base64,${data.frame}`;
              }
            }
          } else if (data.type === 'set_completed') {
            setSets(data.sets);
          } else if (data.error) {
            setError(data.error);
          }
        } catch (e) {
          console.error("Error parsing WS message", e);
        }
      };
      
      wsRef.current.onerror = (err) => {
        console.error('WebSocket error:', err);
        setError('Connection lost. Ensure backend is running.');
        setConnected(false);
        reject(err);
      };
      
      wsRef.current.onclose = () => {
        console.log('WebSocket closed');
        setConnected(false);
      };
    });
  }, [sessionId]);

  const captureAndSendFrame = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return;
    }

    const inputVideo = inputVideoRef?.current;
    if (!inputVideo || inputVideo.readyState < 2) {
      return;
    }

    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    canvas.width = TARGET_WIDTH;
    canvas.height = TARGET_HEIGHT;
    ctx.drawImage(inputVideo, 0, 0, TARGET_WIDTH, TARGET_HEIGHT);
    
    const frameData = canvas.toDataURL('image/jpeg', JPEG_QUALITY);
    
    wsRef.current.send(JSON.stringify({
      type: 'frame',
      frame: frameData
    }));
  }, [inputVideoRef]);

  const startCamera = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { 
          width: { ideal: 640 }, 
          height: { ideal: 480 },
          facingMode: 'user',
          frameRate: { ideal: 15, max: 30 }
        }
      });
      streamRef.current = stream;
      
      const inputVideo = inputVideoRef?.current;
      if (inputVideo) {
        inputVideo.srcObject = stream;
        await inputVideo.play();
      } else {
        throw new Error("Video element not available");
      }
      
      return stream;
    } catch (err) {
      console.error("Camera Init Error:", err);
      throw new Error('Camera access denied. Please allow camera access.');
    }
  }, [inputVideoRef]);

  const stopCamera = useCallback(() => {
    isStreamingRef.current = false;
    if (frameIntervalRef.current) {
      clearInterval(frameIntervalRef.current);
      frameIntervalRef.current = null;
    }
    
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    
    const inputVideo = inputVideoRef?.current;
    if (inputVideo) {
      inputVideo.srcObject = null;
    }
    
    if (videoRef.current) {
      videoRef.current.src = '';
    }
  }, [inputVideoRef]);

  const startSession = useCallback(async () => {
    if (isSessionActive) return;
    
    try {
      setIsLoading(true);
      setError(null);
      
      await startCamera();
      
      const response = await fetch(
        `${API_BASE}/api/session/start?exercise=${exercise}&session_id=${sessionId}`,
        { method: 'POST' }
      );
      
      if (!response.ok) {
        throw new Error('Failed to start session. Is the backend running?');
      }
      
      const data = await response.json();
      console.log('Session started:', data);
      setExerciseType(data.exercise_type || 'reps');
      
      await connectWebSocket();
      
      isStreamingRef.current = true;
      frameIntervalRef.current = setInterval(() => {
        if (isStreamingRef.current) {
          captureAndSendFrame();
        }
      }, FRAME_INTERVAL_MS);
      
      setIsSessionActive(true);
      setIsLoading(false);
      
    } catch (err) {
      console.error("Start session error:", err);
      setError(err.message);
      setIsLoading(false);
      stopCamera();
    }
  }, [exercise, sessionId, isSessionActive, startCamera, stopCamera, connectWebSocket, captureAndSendFrame]);

  const endSession = useCallback(async () => {
    if (!isSessionActive) return;
    
    try {
      setIsLoading(true);
      stopCamera();
      
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      
      await fetch(`${API_BASE}/api/session/stop?session_id=${sessionId}`, {
        method: 'POST',
        keepalive: true
      });
      
      setIsSessionActive(false);
      setConnected(false);
      setState('UNKNOWN');
      setFeedback(['Position yourself in the frame.']);
      setIsLoading(false);
      
    } catch (err) {
      console.error("End session error:", err);
      setError(err.message);
      setIsLoading(false);
    }
  }, [sessionId, isSessionActive, stopCamera]);

  const completeSet = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'complete_set' }));
    }
  }, []);

  const resetSession = useCallback(() => {
    setReps(0);
    setSets(0);
    setState('UNKNOWN');
    setFeedback(['Position yourself in the frame.']);
    setCurrentTime(0);
  }, []);

  return {
    // Common
    sets,
    state,
    feedback,
    connected,
    error,
    isLoading,
    isSessionActive,
    exerciseType,
    videoRef,
    canvasRef,
    completeSet,
    startSession,
    endSession,
    resetSession,
    // Rep-based
    reps,
    // Timed
    currentTime,
    bestTime,
    totalTime,
  };
};
