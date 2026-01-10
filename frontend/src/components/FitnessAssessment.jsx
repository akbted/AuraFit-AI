import React, { useState, useRef, useEffect } from 'react';
import { Dumbbell, Timer, CheckCircle2, ArrowRight, Play, Square, Trophy, Target, Camera, RefreshCw } from 'lucide-react';

const EXERCISES = [
    {
        id: 'pushups',
        name: 'Push-ups',
        description: 'Do as many push-ups as you can with proper form',
        icon: Dumbbell,
        color: 'blue',
        type: 'reps',
        instruction: 'Keep your body straight, lower until chest nearly touches ground, then push back up.',
    },
    {
        id: 'squats',
        name: 'Squats',
        description: 'Do as many squats as you can with proper form',
        icon: Dumbbell,
        color: 'green',
        type: 'reps',
        instruction: 'Stand with feet shoulder-width apart, lower until thighs are parallel to ground.',
    },
    {
        id: 'situps',
        name: 'Sit-ups',
        description: 'Do as many sit-ups as you can in 60 seconds',
        icon: Dumbbell,
        color: 'purple',
        type: 'reps',
        instruction: 'Lie on your back, knees bent, hands behind head. Lift upper body to knees.',
    },
    {
        id: 'plank',
        name: 'Plank Hold',
        description: 'Hold a plank position for as long as you can',
        icon: Timer,
        color: 'orange',
        type: 'time',
        instruction: 'Hold a straight body position on forearms and toes. Keep core engaged.',
    },
];

const FitnessAssessment = ({ onComplete }) => {
    const [currentExerciseIndex, setCurrentExerciseIndex] = useState(0);
    const [isStarted, setIsStarted] = useState(false);
    const [isActive, setIsActive] = useState(false);
    const [results, setResults] = useState({});
    const [currentValue, setCurrentValue] = useState(0);
    const [timer, setTimer] = useState(0);
    const [timerInterval, setTimerInterval] = useState(null);
    const videoRef = useRef(null);
    const streamRef = useRef(null);
    const [cameraError, setCameraError] = useState(null);
    const [isAiActive, setIsAiActive] = useState(true);

    // AI Simulation Interval
    useEffect(() => {
        let aiInterval;
        if (isActive && isAiActive && currentExerciseIndex !== -1 && !cameraError) {
            // Simulate AI counting/tracking
            if (EXERCISES[currentExerciseIndex].type === 'reps') {
                aiInterval = setInterval(() => {
                    // 30% chance to count a rep every interval to simulate realistic pace
                    if (Math.random() > 0.7) {
                        setCurrentValue(prev => prev + 1);
                    }
                }, 1000);
            }
        }
        return () => clearInterval(aiInterval);
    }, [isActive, isAiActive, currentExerciseIndex, cameraError]);

    // Cleanup camera on unmount
    useEffect(() => {
        return () => {
            stopCamera();
        };
    }, []);

    const currentExercise = EXERCISES[currentExerciseIndex];
    const isLastExercise = currentExerciseIndex === EXERCISES.length - 1;
    const isAssessmentComplete = Object.keys(results).length === EXERCISES.length;

    const getColorClasses = (color) => {
        const colors = {
            blue: 'bg-blue-500',
            green: 'bg-green-500',
            purple: 'bg-purple-500',
            orange: 'bg-orange-500',
        };
        return colors[color] || colors.blue;
    };

    const startCamera = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'user' }
            });
            streamRef.current = stream;
            if (videoRef.current) {
                videoRef.current.srcObject = stream;
                videoRef.current.play();
            }
            setCameraError(null);
        } catch (err) {
            console.error("Camera Error:", err);
            setCameraError("Could not access camera. Please allow permissions.");
            setIsAiActive(false);
        }
    };

    const stopCamera = () => {
        if (streamRef.current) {
            streamRef.current.getTracks().forEach(track => track.stop());
            streamRef.current = null;
        }
    };

    const startExercise = () => {
        setIsActive(true);
        setCurrentValue(0);
        setTimer(0);
        startCamera();

        if (currentExercise.type === 'time') {
            const interval = setInterval(() => {
                setTimer((prev) => prev + 1);
            }, 1000);
            setTimerInterval(interval);
        }
    };

    const stopExercise = () => {
        setIsActive(false);
        stopCamera();
        if (timerInterval) {
            clearInterval(timerInterval);
            setTimerInterval(null);
        }
    };

    const saveResult = () => {
        const value = currentExercise.type === 'time' ? timer : currentValue;
        setResults((prev) => ({
            ...prev,
            [currentExercise.id]: value,
        }));

        stopExercise();

        if (isLastExercise) {
            // Assessment complete
            setIsStarted(false);
        } else {
            // Move to next exercise
            setCurrentExerciseIndex((prev) => prev + 1);
            setIsActive(false);
            setCurrentValue(0);
            setTimer(0);
        }
    };

    const handleComplete = () => {
        // ============================================
        // 🔧 BACKEND INTEGRATION POINT - SAVE ASSESSMENT
        // ============================================
        // TODO: Save assessment results to backend
        // Example:
        // await fetch('/api/user/fitness-assessment', {
        //   method: 'POST',
        //   headers: {
        //     'Content-Type': 'application/json',
        //     'Authorization': `Bearer ${localStorage.getItem('authToken')}`
        //   },
        //   body: JSON.stringify({ results, completedAt: new Date() })
        // });
        // ============================================

        // Save to localStorage for now
        const assessmentData = {
            results,
            completedAt: new Date().toISOString(),
            fitnessLevel: calculateFitnessLevel(results),
        };
        localStorage.setItem('fitnessAssessment_v2', JSON.stringify(assessmentData));

        // Call parent callback
        if (onComplete) {
            onComplete(assessmentData);
        }
    };

    const calculateFitnessLevel = (results) => {
        // Simple fitness level calculation based on results
        const pushups = results.pushups || 0;
        const squats = results.squats || 0;
        const situps = results.situps || 0;
        const plank = results.plank || 0;

        const score = pushups * 2 + squats * 1.5 + situps * 1.5 + plank * 0.5;

        if (score >= 150) return 'Advanced';
        if (score >= 80) return 'Intermediate';
        return 'Beginner';
    };

    const formatTime = (seconds) => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    };

    if (!isStarted) {
        return (
            <div className="flex flex-col items-center justify-center p-4 min-h-[calc(100vh-4rem)]">
                <div className="max-w-4xl w-full">
                    {/* Welcome Section */}
                    {Object.keys(results).length === 0 ? (
                        <div className="bg-white rounded-3xl shadow-2xl p-8 md:p-12 text-center">
                            <div className="w-20 h-20 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-full flex items-center justify-center mx-auto mb-6">
                                <Trophy className="w-10 h-10 text-white" />
                            </div>

                            <h1 className="text-4xl font-black text-slate-900 mb-4">
                                Welcome to AuraFit! 🎉
                            </h1>

                            <p className="text-xl text-slate-600 mb-8 max-w-2xl mx-auto">
                                Before we begin, let's assess your current fitness level. This will help us create a personalized workout plan just for you!
                            </p>

                            <div className="bg-blue-50 border border-blue-200 rounded-2xl p-6 mb-8">
                                <h3 className="font-bold text-blue-900 mb-4 flex items-center justify-center gap-2">
                                    <Target className="w-5 h-5" />
                                    What to Expect
                                </h3>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-left">
                                    <div className="flex items-start gap-3">
                                        <CheckCircle2 className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                                        <div>
                                            <p className="font-semibold text-slate-800">4 Quick Exercises</p>
                                            <p className="text-sm text-slate-600">Takes about 5-10 minutes</p>
                                        </div>
                                    </div>
                                    <div className="flex items-start gap-3">
                                        <CheckCircle2 className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                                        <div>
                                            <p className="font-semibold text-slate-800">No Equipment Needed</p>
                                            <p className="text-sm text-slate-600">Just your body weight</p>
                                        </div>
                                    </div>
                                    <div className="flex items-start gap-3">
                                        <CheckCircle2 className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                                        <div>
                                            <p className="font-semibold text-slate-800">Do Your Best</p>
                                            <p className="text-sm text-slate-600">No pressure, just baseline</p>
                                        </div>
                                    </div>
                                    <div className="flex items-start gap-3">
                                        <CheckCircle2 className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                                        <div>
                                            <p className="font-semibold text-slate-800">Personalized Plan</p>
                                            <p className="text-sm text-slate-600">Custom goals based on results</p>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                                {EXERCISES.map((exercise, index) => {
                                    const Icon = exercise.icon;
                                    return (
                                        <div key={exercise.id} className="bg-slate-50 rounded-xl p-4 border border-slate-200">
                                            <div className={`w-12 h-12 ${getColorClasses(exercise.color)} rounded-lg flex items-center justify-center mx-auto mb-2`}>
                                                <Icon className="w-6 h-6 text-white" />
                                            </div>
                                            <p className="font-semibold text-slate-800 text-sm">{exercise.name}</p>
                                            <p className="text-xs text-slate-500">{exercise.type === 'time' ? 'Timed' : 'Reps'}</p>
                                        </div>
                                    );
                                })}
                            </div>

                            <div className="flex flex-col items-center gap-4">
                                <button
                                    onClick={() => setIsStarted(true)}
                                    className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white px-8 py-4 rounded-xl font-bold text-lg shadow-xl shadow-blue-600/30 transition-all hover:scale-105 active:scale-95 flex items-center justify-center gap-2"
                                >
                                    Start Fitness Assessment <ArrowRight className="w-5 h-5" />
                                </button>
                            </div>
                        </div>
                    ) : (
                        // Results Summary
                        <div className="bg-white rounded-3xl shadow-2xl p-8 md:p-12 relative">
                            <div className="text-center mb-8">
                                <div className="w-20 h-20 bg-gradient-to-br from-green-500 to-emerald-500 rounded-full flex items-center justify-center mx-auto mb-6">
                                    <CheckCircle2 className="w-10 h-10 text-white" />
                                </div>
                                <h1 className="text-4xl font-black text-slate-900 mb-4">
                                    Assessment Complete! 🎉
                                </h1>
                                <p className="text-xl text-slate-600 mb-2">
                                    Great job! Here are your results:
                                </p>
                                <div className="inline-block px-4 py-2 bg-blue-100 text-blue-800 rounded-full font-bold text-lg">
                                    Fitness Level: {calculateFitnessLevel(results)}
                                </div>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                                {EXERCISES.map((exercise) => {
                                    const Icon = exercise.icon;
                                    const value = results[exercise.id] || 0;
                                    return (
                                        <div key={exercise.id} className="bg-slate-50 rounded-xl p-6 border border-slate-200">
                                            <div className="flex items-center gap-4 mb-3">
                                                <div className={`w-12 h-12 ${getColorClasses(exercise.color)} rounded-lg flex items-center justify-center`}>
                                                    <Icon className="w-6 h-6 text-white" />
                                                </div>
                                                <div className="flex-1">
                                                    <h3 className="font-bold text-slate-800">{exercise.name}</h3>
                                                    <p className="text-sm text-slate-500">{exercise.type === 'time' ? 'Time Held' : 'Reps Completed'}</p>
                                                </div>
                                            </div>
                                            <div className="text-3xl font-black text-slate-900">
                                                {exercise.type === 'time' ? formatTime(value) : value}
                                                <span className="text-lg text-slate-500 ml-2">{exercise.type === 'time' ? '' : 'reps'}</span>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>

                            <button
                                onClick={handleComplete}
                                className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white px-8 py-4 rounded-xl font-bold text-lg shadow-xl shadow-blue-600/30 transition-all hover:scale-105 active:scale-95 flex items-center justify-center gap-2"
                            >
                                Continue to Dashboard <ArrowRight className="w-5 h-5" />
                            </button>
                        </div >
                    )}
                </div >
            </div >
        );
    }

    // Exercise Screen - Camera View
    return (
        <div className="flex flex-col items-center justify-center p-4 min-h-[calc(100vh-4rem)]">
            <div className="max-w-4xl w-full">
                <div className="relative rounded-3xl overflow-hidden bg-slate-900 shadow-2xl min-h-[600px] flex flex-col">

                    {/* Camera Feed Background */}
                    <div className="absolute inset-0">
                        {isActive && !cameraError ? (
                            <video
                                ref={videoRef}
                                className="w-full h-full object-cover opacity-60"
                                muted
                                playsInline
                            />
                        ) : (
                            <div className="w-full h-full bg-slate-900/80 flex items-center justify-center">
                                {cameraError ? (
                                    <div className="text-red-400 flex flex-col items-center gap-2">
                                        <Camera className="w-12 h-12" />
                                        <p>{cameraError}</p>
                                    </div>
                                ) : (
                                    <div className="text-slate-600 flex flex-col items-center gap-2">
                                        <Camera className="w-16 h-16 opacity-20" />
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    {/* Progress Bar */}
                    <div className="relative z-20 bg-white/10 h-2 backdrop-blur-md">
                        <div
                            className="bg-gradient-to-r from-blue-500 to-indigo-500 h-full transition-all duration-300 shadow-[0_0_10px_rgba(59,130,246,0.5)]"
                            style={{ width: `${((currentExerciseIndex + 1) / EXERCISES.length) * 100}%` }}
                        />
                    </div>

                    {/* Content Overlay */}
                    <div className="relative z-10 flex-1 flex flex-col p-8 md:p-12 text-white">

                        {/* Header Info */}
                        <div className="flex justify-between items-start mb-8">
                            <div>
                                <p className="text-sm font-bold text-blue-300 uppercase tracking-wider mb-2">
                                    Exercise {currentExerciseIndex + 1} / {EXERCISES.length}
                                </p>
                                <h2 className="text-4xl font-black mb-2 flex items-center gap-3">
                                    {currentExercise.name}
                                    {isAiActive && isActive && (
                                        <span className="text-xs bg-green-500/20 text-green-400 border border-green-500/30 px-2 py-1 rounded-full flex items-center gap-1">
                                            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                                            AI Tracking
                                        </span>
                                    )}
                                </h2>
                            </div>

                            <div className={`w-16 h-16 ${getColorClasses(currentExercise.color)} bg-opacity-90 rounded-2xl flex items-center justify-center shadow-lg backdrop-blur-sm`}>
                                <currentExercise.icon className="w-8 h-8 text-white" />
                            </div>
                        </div>

                        {/* Center Display */}
                        <div className="flex-1 flex flex-col items-center justify-center">
                            <div className="bg-black/40 backdrop-blur-md border border-white/10 rounded-3xl p-8 mb-8 text-center min-w-[200px]">
                                <p className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-2">
                                    {currentExercise.type === 'time' ? 'Timer' : 'Reps Count'}
                                </p>
                                <div className="text-7xl font-black text-white slashed-zero tabular-nums tracking-tight">
                                    {currentExercise.type === 'time' ? formatTime(timer) : currentValue}
                                </div>
                                {currentExercise.type === 'reps' && isActive && (
                                    <p className="text-xs text-slate-400 mt-2">
                                        AI is counting...
                                    </p>
                                )}
                            </div>

                            {/* Manual Controls Fallback */}
                            {currentExercise.type === 'reps' && isActive && (
                                <div className="flex gap-4 mb-6 opacity-50 hover:opacity-100 transition-opacity">
                                    <button
                                        onClick={() => setCurrentValue((prev) => Math.max(0, prev - 1))}
                                        className="w-12 h-12 flex items-center justify-center bg-white/10 hover:bg-white/20 rounded-full text-white font-bold transition-colors"
                                    >
                                        -1
                                    </button>
                                    <button
                                        onClick={() => setCurrentValue((prev) => prev + 1)}
                                        className="w-12 h-12 flex items-center justify-center bg-white/10 hover:bg-white/20 rounded-full text-white font-bold transition-colors"
                                    >
                                        +1
                                    </button>
                                </div>
                            )}

                            {!isActive && (
                                <div className="bg-black/60 backdrop-blur-md p-6 rounded-2xl border border-white/10 max-w-md mx-auto text-center">
                                    <p className="font-semibold text-white mb-2">Instructions:</p>
                                    <p className="text-slate-300">{currentExercise.instruction}</p>
                                </div>
                            )}
                        </div>

                        {/* Controls Footer */}
                        <div className="mt-auto pt-8 flex gap-4">
                            {!isActive ? (
                                <button
                                    onClick={startExercise}
                                    className="flex-1 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 text-white px-6 py-4 rounded-2xl font-bold text-lg shadow-lg shadow-green-900/20 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-2"
                                >
                                    <Camera className="w-5 h-5" /> Start & Enable Camera
                                </button>
                            ) : (
                                <>
                                    <button
                                        onClick={stopExercise}
                                        className="flex-1 bg-white/10 hover:bg-white/20 text-white px-6 py-4 rounded-2xl font-bold text-lg backdrop-blur-md transition-all flex items-center justify-center gap-2"
                                    >
                                        <Square className="w-5 h-5" /> Pause
                                    </button>
                                    <button
                                        onClick={saveResult}
                                        className="flex-1 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white px-6 py-4 rounded-2xl font-bold text-lg shadow-lg shadow-blue-900/20 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-2"
                                    >
                                        <CheckCircle2 className="w-5 h-5" /> {isLastExercise ? 'Finish Assessment' : 'Next Exercise'}
                                    </button>
                                </>
                            )}
                        </div>

                    </div>
                </div>
            </div>
        </div>
    );
};

export default FitnessAssessment;
