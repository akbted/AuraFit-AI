import React, { useState, useRef, useCallback } from 'react';
import { RefreshCw, CheckCircle2, AlertCircle, Play, Square, Timer } from 'lucide-react';
import { useWorkoutSession } from '../hooks/useWorkoutSession';

const EXERCISES = [
  { id: 'pushups', name: 'Pushups', type: 'reps' },
  { id: 'squats', name: 'Squats', type: 'reps' },
  { id: 'crunches', name: 'Crunches', type: 'reps' },
  { id: 'leg_raises', name: 'Leg Raises', type: 'reps' },
  { id: 'plank', name: 'Plank', type: 'timed' },
];

/**
 * WorkoutSession Component
 * 
 * Real-time AI workout tracking with backend integration.
 */
const WorkoutSession = () => {
  const [activeExercise, setActiveExercise] = useState('pushups');
  const [key, setKey] = useState(0); // Force remount on exercise change
  const inputVideoRef = useRef(null);

  // Handle exercise switch - force hook to reinitialize
  const handleSwitchExercise = useCallback((newExercise) => {
    if (newExercise !== activeExercise) {
      setActiveExercise(newExercise);
      setKey(prev => prev + 1); // Force remount
    }
  }, [activeExercise]);

  // Handle reset - force remount to reset counters
  const handleReset = useCallback(() => {
    setKey(prev => prev + 1);
  }, []);

  return (
    <WorkoutSessionContent 
      key={key} 
      activeExercise={activeExercise} 
      onSwitchExercise={handleSwitchExercise}
      onReset={handleReset}
      inputVideoRef={inputVideoRef}
    />
  );
};

const WorkoutSessionContent = ({ activeExercise, onSwitchExercise, onReset, inputVideoRef }) => {
  const {
    reps,
    sets,
    state,
    feedback,
    connected,
    error,
    isLoading,
    isSessionActive,
    exerciseType,
    currentTime,
    bestTime,
    videoRef,
    canvasRef,
    completeSet,
    startSession,
    endSession
  } = useWorkoutSession(activeExercise, inputVideoRef);

  const handleSwitchWithEnd = async (newExercise) => {
    if (isSessionActive) {
      await endSession();
    }
    onSwitchExercise(newExercise);
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const currentExerciseInfo = EXERCISES.find(e => e.id === activeExercise) || EXERCISES[0];

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col lg:flex-row gap-6">
      
      {/* Hidden raw input video (captured by hook) 
          NOTE: We use opacity-0 and z-index instead of display:none because hidden elements
          often don't update their video texture in browsers, breaking canvas capture.
      */}
      <video 
        ref={inputVideoRef}
        className="opacity-0 absolute pointer-events-none -z-50" 
        autoPlay 
        playsInline 
        muted 
      />
      
      {/* Main Camera Area */}
      <div className="flex-1 bg-black rounded-3xl overflow-hidden relative shadow-2xl border border-slate-800">
        
        {/* Connection Status Indicator */}
        <div className="absolute top-6 left-6 z-20 flex gap-2">
            <div className={`px-4 py-2 rounded-full backdrop-blur-md flex items-center gap-2 text-sm font-medium ${
                connected 
                    ? 'bg-green-500/20 text-green-400 border border-green-500/30' 
                    : 'bg-red-500/20 text-red-400 border border-red-500/30 animate-pulse'
            }`}>
               <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`} />
               {connected ? 'AI Online' : (error ? 'Connection Error' : 'Connecting...')}
            </div>
            
            <div className="px-4 py-2 bg-blue-600/20 text-blue-300 border border-blue-500/30 rounded-full backdrop-blur-md text-sm font-medium uppercase tracking-wider">
                {currentExerciseInfo.name}
            </div>
            
            {exerciseType === 'timed' && (
              <div className="px-4 py-2 bg-purple-600/20 text-purple-300 border border-purple-500/30 rounded-full backdrop-blur-md text-sm font-medium flex items-center gap-1">
                <Timer className="w-4 h-4" /> Timed
              </div>
            )}
        </div>

        {/* Video Feed */}
        <div className="absolute inset-0 flex items-center justify-center bg-slate-900">
          {isLoading && !videoRef.current?.src ? (
             <div className="text-center text-slate-500 flex flex-col items-center">
                <div className="w-12 h-12 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin mb-4" />
                <p>Initializing Vision System...</p>
             </div>
          ) : isSessionActive ? (
             <img 
               ref={videoRef} 
               className="w-full h-full object-contain"
               alt="AI Vision Feed"
             />
          ) : (
             <div className="text-center text-slate-500">
                <p>Press "Start Session" to begin</p>
             </div>
          )}
          {/* Hidden Canvas for Frame Processing */}
          <canvas ref={canvasRef} className="hidden" />
        </div>

        {/* AI Feedback Overlay */}
        {feedback.length > 0 && (
          <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 w-full max-w-lg">
             <div className="mx-6 bg-black/60 backdrop-blur-xl border border-white/10 rounded-2xl p-4 text-center">
                 {feedback.map((msg, i) => (
                    <p key={i} className="text-white text-lg font-medium drop-shadow-md flex items-center justify-center gap-2">
                       <AlertCircle className="w-5 h-5 text-blue-400" /> {msg}
                    </p>
                 ))}
             </div>
          </div>
        )}
      </div>

      {/* Right Sidebar - Stats & Controls */}
      <div className="lg:w-96 flex flex-col gap-6">
        
        {/* Main Counter/Timer Card */}
        <div className="bg-white rounded-3xl p-8 border border-slate-200 shadow-xl flex-1 flex flex-col justify-center items-center text-center relative overflow-hidden group">
            <div className={`absolute inset-0 opacity-5 transition-colors duration-300 ${
              exerciseType === 'timed' 
                ? (state === 'PLANK' ? 'bg-green-600' : 'bg-slate-100')
                : (state === 'DOWN' ? 'bg-blue-600' : (state === 'UP' ? 'bg-green-600' : 'bg-slate-100'))
            }`} />
            
            {exerciseType === 'timed' ? (
              <>
                <h3 className="text-slate-500 text-sm font-bold uppercase tracking-widest mb-2">Hold Time</h3>
                <div className="text-[80px] leading-none font-black text-slate-900 font-tabular-nums tracking-tighter">
                    {formatTime(currentTime)}
                </div>
                <p className="text-slate-400 text-sm mt-4">Best: {formatTime(bestTime)}</p>
              </>
            ) : (
              <>
                <h3 className="text-slate-500 text-sm font-bold uppercase tracking-widest mb-2">Current Reps</h3>
                <div className="text-[120px] leading-none font-black text-slate-900 font-tabular-nums tracking-tighter shadow-slate-200 drop-shadow-sm">
                    {reps}
                </div>
              </>
            )}
            
            <div className={`mt-6 px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-wide border transition-all ${
                state === 'DOWN' ? 'bg-blue-100 text-blue-700 border-blue-200' :
                state === 'UP' ? 'bg-green-100 text-green-700 border-green-200' :
                state === 'PLANK' ? 'bg-green-100 text-green-700 border-green-200' :
                state === 'REST' ? 'bg-orange-100 text-orange-700 border-orange-200' :
                'bg-slate-100 text-slate-500 border-slate-200'
            }`}>
               State: {state}
            </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-4">
             <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow">
                 <p className="text-slate-400 text-xs font-bold uppercase">Sets Completed</p>
                 <p className="text-3xl font-bold text-slate-800 mt-1">{sets}</p>
             </div>
             <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow">
                 <p className="text-slate-400 text-xs font-bold uppercase">
                   {exerciseType === 'timed' ? 'Exercise' : 'Accuracy'}
                 </p>
                 <p className="text-3xl font-bold text-slate-800 mt-1">
                   {exerciseType === 'timed' ? '🧘' : '98%'}
                 </p>
             </div>
        </div>

        {/* Controls */}
        <div className="bg-slate-900 text-white p-6 rounded-3xl shadow-xl">
             <div className="flex items-center justify-between mb-6">
                 <div>
                    <h3 className="font-bold text-lg">Control Panel</h3>
                    <p className="text-slate-400 text-sm">Manage your session</p>
                 </div>
                 <button 
                    onClick={onReset}
                    className="w-10 h-10 rounded-full bg-slate-800 hover:bg-slate-700 flex items-center justify-center transition-colors group"
                    title="Reset Session"
                 >
                    <RefreshCw className="w-5 h-5 text-slate-400 group-hover:text-white transition-colors" />
                 </button>
             </div>

             <button 
                onClick={completeSet}
                disabled={!connected}
                className={`w-full py-4 rounded-xl font-bold text-lg flex items-center justify-center gap-2 mb-3 transition-all ${
                    connected 
                    ? 'bg-blue-600 hover:bg-blue-500 shadow-lg shadow-blue-900/50 active:scale-95' 
                    : 'bg-slate-700 text-slate-500 cursor-not-allowed'
                }`}
             >
                 <CheckCircle2 className="w-6 h-6" /> Complete Set
             </button>

             {/* Exercise Selector */}
             <div className="mb-3">
               <select
                 value={activeExercise}
                 onChange={(e) => handleSwitchWithEnd(e.target.value)}
                 className="w-full py-3 px-4 bg-slate-800 hover:bg-slate-700 rounded-xl font-medium text-sm text-slate-300 border border-slate-700 focus:outline-none focus:border-blue-500"
               >
                 {EXERCISES.map(ex => (
                   <option key={ex.id} value={ex.id}>
                     {ex.name} {ex.type === 'timed' ? '(Timed)' : ''}
                   </option>
                 ))}
               </select>
             </div>

             <div className="grid grid-cols-1 gap-3">
                 {isSessionActive ? (
                   <button 
                     onClick={endSession}
                     disabled={isLoading}
                     className="py-3 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 rounded-xl font-medium text-sm transition-colors flex items-center justify-center gap-2"
                   >
                     <Square className="w-4 h-4" />
                     {isLoading ? 'Stopping...' : 'End Session'}
                   </button>
                 ) : (
                   <button 
                     onClick={startSession}
                     disabled={isLoading}
                     className="py-3 bg-green-500/10 hover:bg-green-500/20 text-green-400 border border-green-500/20 rounded-xl font-medium text-sm transition-colors flex items-center justify-center gap-2"
                   >
                     <Play className="w-4 h-4" />
                     {isLoading ? 'Starting...' : 'Start Session'}
                   </button>
                 )}
             </div>
        </div>

      </div>
    </div>
  );
};

export default WorkoutSession;
