import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Voice Command Hook
 * 
 * Provides voice recognition capabilities for hands-free control
 * Especially useful during workout sessions
 */
export const useVoiceCommands = (onCommand) => {
    const [isListening, setIsListening] = useState(false);
    const [isSupported, setIsSupported] = useState(false);
    const [transcript, setTranscript] = useState('');
    const [error, setError] = useState(null);

    const recognitionRef = useRef(null);
    const timeoutRef = useRef(null);

    useEffect(() => {
        // Check if browser supports Web Speech API
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

        if (SpeechRecognition) {
            setIsSupported(true);

            const recognition = new SpeechRecognition();
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.lang = 'en-US';

            recognition.onstart = () => {
                setIsListening(true);
                setError(null);
                console.log('Voice recognition started');
            };

            recognition.onend = () => {
                setIsListening(false);
                console.log('Voice recognition ended');
            };

            recognition.onerror = (event) => {
                console.error('Speech recognition error:', event.error);
                setError(event.error);
                setIsListening(false);
            };

            recognition.onresult = (event) => {
                let finalTranscript = '';
                let interimTranscript = '';

                for (let i = event.resultIndex; i < event.results.length; i++) {
                    const transcript = event.results[i][0].transcript;
                    if (event.results[i].isFinal) {
                        finalTranscript += transcript;
                    } else {
                        interimTranscript += transcript;
                    }
                }

                const currentTranscript = finalTranscript || interimTranscript;
                setTranscript(currentTranscript);

                // Process final commands
                if (finalTranscript) {
                    processCommand(finalTranscript.toLowerCase().trim());

                    // Clear transcript after a delay
                    if (timeoutRef.current) clearTimeout(timeoutRef.current);
                    timeoutRef.current = setTimeout(() => {
                        setTranscript('');
                    }, 3000);
                }
            };

            recognitionRef.current = recognition;
        } else {
            setIsSupported(false);
            setError('Speech recognition not supported in this browser');
        }

        return () => {
            if (recognitionRef.current) {
                recognitionRef.current.stop();
            }
            if (timeoutRef.current) {
                clearTimeout(timeoutRef.current);
            }
        };
    }, []);

    const processCommand = useCallback((command) => {
        console.log('Processing command:', command);

        // Command patterns
        const commands = {
            // Session control
            start: /^(start|begin|go|resume)/,
            stop: /^(stop|end|finish|pause)/,

            // Set completion
            complete: /^(complete|done|finish set|next set)/,

            // Exercise switching
            pushups: /^(pushups|push ups|push-ups)/,
            squats: /^(squats|squat)/,
            plank: /^(plank|planks)/,
            crunches: /^(crunches|crunch)/,
            legRaises: /^(leg raises|leg raise)/,

            // Information
            status: /^(status|stats|how am i doing|progress)/,
            help: /^(help|commands|what can you do)/,

            // Navigation
            home: /^(home|dashboard|go home)/,
            leaderboard: /^(leaderboard|rankings|rank)/,
            profile: /^(profile|my profile)/,
        };

        // Check each command pattern
        for (const [action, pattern] of Object.entries(commands)) {
            if (pattern.test(command)) {
                if (onCommand) {
                    onCommand(action, command);
                }
                return;
            }
        }

        // If no command matched, still call the callback with the raw command
        if (onCommand) {
            onCommand('unknown', command);
        }
    }, [onCommand]);

    const startListening = useCallback(() => {
        if (recognitionRef.current && !isListening) {
            try {
                recognitionRef.current.start();
            } catch (error) {
                console.error('Error starting recognition:', error);
                setError('Failed to start voice recognition');
            }
        }
    }, [isListening]);

    const stopListening = useCallback(() => {
        if (recognitionRef.current && isListening) {
            recognitionRef.current.stop();
        }
    }, [isListening]);

    const toggleListening = useCallback(() => {
        if (isListening) {
            stopListening();
        } else {
            startListening();
        }
    }, [isListening, startListening, stopListening]);

    return {
        isListening,
        isSupported,
        transcript,
        error,
        startListening,
        stopListening,
        toggleListening,
    };
};

export default useVoiceCommands;
