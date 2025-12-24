import React from 'react';
import { Dumbbell, ArrowRight, Play, ShieldCheck, Activity } from 'lucide-react';

const Landing = ({ onNavigate }) => {
  return (
    <div className="min-h-screen bg-slate-50 font-sans text-slate-800">
      {/* Navbar */}
      <nav className="p-6 sticky top-0 bg-white/80 backdrop-blur-md z-50 border-b border-slate-200">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <Dumbbell className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600">
              AuraFit
            </span>
          </div>
          <div className="flex items-center gap-4">
             {/* 
             <button 
               onClick={() => onNavigate('login')}
               className="text-slate-600 font-semibold hover:text-blue-600 transition-colors"
             >
               Sign In
             </button>
             <button 
               onClick={() => onNavigate('register')}
               className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-full font-bold transition-all shadow-lg shadow-blue-600/20 active:scale-95"
             >
               Get Started
             </button>
             */}
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <header className="px-6 py-20 lg:py-32">
         <div className="max-w-5xl mx-auto text-center">
           <div className="inline-flex items-center gap-2 px-4 py-2 bg-blue-50 text-blue-700 rounded-full font-semibold text-sm mb-8 animate-fade-in-up">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
              </span>
              Next Gen Fitness Tracking
           </div>
           
           <h1 className="text-5xl lg:text-7xl font-black text-slate-900 mb-8 leading-tight tracking-tight">
             Unlock Your Potential with <br className="hidden md:block" />
             <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600">
               AuraFit AI
             </span>
           </h1>
           
           <p className="text-xl text-slate-600 mb-12 max-w-2xl mx-auto leading-relaxed">
             Experience the future of home workouts. Real-time form correction, competitive modes, and personalized insights powered by advanced computer vision.
           </p>

           <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
             {/*
             <button 
               onClick={() => onNavigate('register')}
               className="w-full sm:w-auto px-8 py-4 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold text-lg shadow-xl shadow-blue-600/30 transition-all hover:scale-105 active:scale-95 flex items-center justify-center gap-2"
             >
               Create Free Account <ArrowRight className="w-5 h-5" />
             </button>
             */}
             <button 
               onClick={() => onNavigate('demo')}
               className="w-full sm:w-auto px-8 py-4 bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 rounded-xl font-bold text-lg shadow-sm transition-all hover:scale-105 active:scale-95 flex items-center justify-center gap-2"
             >
               <Play className="w-5 h-5 fill-current" /> Try Demo Mode
             </button>
           </div>
         </div>
      </header>

      {/* Feature Grid */}
      <section className="px-6 py-20 bg-white">
        <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-8">
           <div className="p-8 rounded-2xl bg-slate-50 border border-slate-100 hover:border-blue-100 hover:shadow-xl hover:shadow-blue-900/5 transition-all group">
             <div className="w-14 h-14 bg-blue-100 rounded-xl flex items-center justify-center mb-6 text-blue-600 group-hover:scale-110 transition-transform">
               <Activity className="w-7 h-7" />
             </div>
             <h3 className="text-2xl font-bold text-slate-800 mb-3">AI Form Analysis</h3>
             <p className="text-slate-600 leading-relaxed">Get real-time feedback on your posture and technique during workouts using just your webcam.</p>
           </div>

           <div className="p-8 rounded-2xl bg-slate-50 border border-slate-100 hover:border-purple-100 hover:shadow-xl hover:shadow-purple-900/5 transition-all group">
             <div className="w-14 h-14 bg-purple-100 rounded-xl flex items-center justify-center mb-6 text-purple-600 group-hover:scale-110 transition-transform">
               <ShieldCheck className="w-7 h-7" />
             </div>
             <h3 className="text-2xl font-bold text-slate-800 mb-3">Privacy First</h3>
             <p className="text-slate-600 leading-relaxed">Your video feed is processed 100% locally on your device. No functionality requires video upload.</p>
           </div>

           <div className="p-8 rounded-2xl bg-slate-50 border border-slate-100 hover:border-pink-100 hover:shadow-xl hover:shadow-pink-900/5 transition-all group">
             <div className="w-14 h-14 bg-pink-100 rounded-xl flex items-center justify-center mb-6 text-pink-600 group-hover:scale-110 transition-transform">
               <Dumbbell className="w-7 h-7" />
             </div>
             <h3 className="text-2xl font-bold text-slate-800 mb-3">Compete & Win</h3>
             <p className="text-slate-600 leading-relaxed">Challenge friends or AI opponents in real-time workout battles to push your limits.</p>
           </div>
        </div>
      </section>

      <footer className="py-10 text-center text-slate-400 text-sm">
        © 2024 AuraFit AI. All rights reserved.
      </footer>
    </div>
  );
};

export default Landing;
