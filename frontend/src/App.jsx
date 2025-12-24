import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import DashboardLayout from './layouts/DashboardLayout';
import Dashboard from './components/Dashboard';
import Landing from './components/Landing';
import Login from './components/Login';
import ProfileForm from './components/ProfileForm';
import WorkoutSession from './components/WorkoutSession';
import CompeteMode from './components/CompeteMode';

// Main App Controller
const AppContent = () => {
  const { user, logout, loading } = useAuth();
  const [currentView, setCurrentView] = useState('landing');
  const [isDemoMode, setIsDemoMode] = useState(false);

  useEffect(() => {
    if (user && !isDemoMode) {
      setCurrentView('home');
    } else if (!user && !isDemoMode && !['login', 'register', 'landing'].includes(currentView)) {
      setCurrentView('landing');
    }
  }, [user, isDemoMode]);

  const handleNavigate = (view) => {
    if (view === 'demo') {
      setIsDemoMode(true);
      setCurrentView('workout');
    } else {
      setIsDemoMode(false);
      setCurrentView(view);
    }
  };

  const handleLogout = () => {
    logout();
    setIsDemoMode(false);
    setCurrentView('landing');
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-slate-500">
        Loading AuraFit...
      </div>
    );
  }

  // Public Views
  if (!user && !isDemoMode) {
    if (currentView === 'login') return <Login onNavigate={handleNavigate} />;
    if (currentView === 'register') return <ProfileForm isRegistration={true} onNavigate={handleNavigate} />;
    return <Landing onNavigate={handleNavigate} />;
  }

  // Demo View
  if (isDemoMode) {
    return (
      <div className="min-h-screen bg-slate-100">
        <header className="bg-white p-4 border-b border-slate-200 flex justify-between items-center">
          <span className="font-bold text-blue-600 ml-4">AuraFit Demo</span>
          <button 
            onClick={() => handleNavigate('landing')} 
            className="text-sm font-medium text-slate-600 hover:text-red-500 mr-4"
          >
            Exit Demo
          </button>
        </header>
        <div className="max-w-7xl mx-auto p-6">
          <WorkoutSession />
        </div>
      </div>
    );
  }

  // Authenticated Dashboard Layout
  return (
    <DashboardLayout currentView={currentView} onViewChange={setCurrentView} onLogout={handleLogout}>
      {currentView === 'home' && <Dashboard onNavigate={handleNavigate} />}
      {currentView === 'profile' && <ProfileForm />}
      {currentView === 'workout' && (
        <WorkoutSession 
          exercise="pushups" 
          onNavigate={handleNavigate}
          onExit={() => setCurrentView('home')}
        />
      )}
      {currentView === 'compete' && <CompeteMode />}
    </DashboardLayout>
  );
};

const App = () => {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
};

export default App;
