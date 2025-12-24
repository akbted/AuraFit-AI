import React, { useState, useEffect, useRef } from 'react';
import { Trophy, Zap, Target, Video, Crown, RotateCcw } from 'lucide-react';

/**
 * CompeteMode Component
 * 
 * Refactored for 'Tailwick' Light Theme.
 * Features:
 * - Clean split-screen design
 * - Modern score cards
 * - Winner overlay
 */
const CompeteMode = ({ p1_score = 0, p2_score = 0, targetScore = 20 }) => {
  const videoRef = useRef(null);
  
  const [player1Score, setPlayer1Score] = useState(p1_score);
  const [player2Score, setPlayer2Score] = useState(p2_score);
  const [winner, setWinner] = useState(null);
  
  const [cameraError, setCameraError] = useState(null);

  useEffect(() => {
    const initCamera = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ 
          video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' },
          audio: false 
        });
        if (videoRef.current) videoRef.current.srcObject = stream;
      } catch (err) {
        setCameraError('Unable to access camera.');
      }
    };
    initCamera();
    return () => {
      if (videoRef.current && videoRef.current.srcObject) {
        videoRef.current.srcObject.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  useEffect(() => {
    setPlayer1Score(p1_score);
    setPlayer2Score(p2_score);
  }, [p1_score, p2_score]);

  useEffect(() => {
    if (player1Score >= targetScore && player1Score > player2Score) setWinner('player1');
    else if (player2Score >= targetScore && player2Score > player1Score) setWinner('player2');
  }, [player1Score, player2Score, targetScore]);

  const resetCompetition = () => {
    setPlayer1Score(0);
    setPlayer2Score(0);
    setWinner(null);
  };

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col gap-6">
      {/* Header Stats */}
      <div className="grid grid-cols-3 gap-6">
        <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-3">
             <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-bold">P1</div>
             <div>
               <p className="text-sm text-slate-500 font-medium">Player 1</p>
               <h3 className="text-2xl font-bold text-slate-800">{player1Score}</h3>
             </div>
          </div>
          {player1Score > player2Score && <Zap className="w-6 h-6 text-yellow-500 fill-current" />}
        </div>

        <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-200 flex flex-col items-center justify-center text-center">
           <div className="flex items-center gap-2 text-slate-500 text-sm font-medium mb-1">
             <Target className="w-4 h-4" />
             Target Score
           </div>
           <p className="text-3xl font-black text-slate-800">{targetScore}</p>
        </div>

        <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-3">
             <div className="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center text-orange-600 font-bold">P2</div>
             <div>
               <p className="text-sm text-slate-500 font-medium">Player 2</p>
               <h3 className="text-2xl font-bold text-slate-800">{player2Score}</h3>
             </div>
          </div>
          {player2Score > player1Score && <Zap className="w-6 h-6 text-yellow-500 fill-current" />}
        </div>
      </div>

      {/* Main Arena */}
      <div className="flex-1 bg-black rounded-xl overflow-hidden shadow-lg relative border border-slate-800">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="w-full h-full object-cover transform -scale-x-100 opacity-90"
        />
        
        {/* VS Divider Line */}
        <div className="absolute inset-0 flex justify-center pointer-events-none">
          <div className="w-0.5 h-full bg-white/20 relative">
             <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-slate-900 border border-slate-700 text-white font-black rounded-full w-12 h-12 flex items-center justify-center text-sm z-10">VS</div>
          </div>
        </div>

        {/* Winner Overlay */}
        {winner && (
          <div className="absolute inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50">
            <div className="bg-white p-10 rounded-3xl text-center shadow-2xl max-w-lg w-full transform animate-in zoom-in duration-300">
              <Crown className="w-20 h-20 text-yellow-500 mx-auto mb-6 fill-current animate-bounce" />
              <h2 className="text-4xl font-black text-slate-800 mb-2">WINNER!</h2>
              <p className="text-2xl font-bold text-blue-600 mb-8">
                {winner === 'player1' ? 'Player 1' : 'Player 2'}
              </p>
              
              <div className="flex justify-center gap-4">
                <button 
                  onClick={resetCompetition}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-xl font-bold transition-all hover:scale-105"
                >
                  New Match
                </button>
              </div>
            </div>
          </div>
        )}
        
        {/* Reset Button (Floating) */}
        <div className="absolute bottom-6 left-1/2 -translate-x-1/2">
           <button 
             onClick={resetCompetition}
             className="bg-white/10 hover:bg-white/20 backdrop-blur-md text-white px-6 py-2 rounded-full text-sm font-medium border border-white/20 transition-all flex items-center gap-2"
           >
             <RotateCcw className="w-4 h-4" /> Reset Match
           </button>
        </div>

        {cameraError && (
          <div className="absolute inset-0 bg-slate-900 flex flex-col items-center justify-center text-white">
            <Video className="w-16 h-16 text-slate-600 mb-4" />
            <p className="text-slate-400">Camera Unavailable</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default CompeteMode;
