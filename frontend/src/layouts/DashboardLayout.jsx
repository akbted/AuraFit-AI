import { Home, Dumbbell, Users, User, LogOut, Menu, X, Bell, Search, Trophy, Sparkles } from 'lucide-react';
import { useState } from 'react';

const DashboardLayout = ({ children, currentView, onViewChange, onLogout }) => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  // Navigation Items
  const navItems = [
    { id: 'home', label: 'Dashboard', icon: Home },
    { id: 'workout', label: 'Workout Session', icon: Dumbbell },
    { id: 'compete', label: 'Competition Mode', icon: Users },
    { id: 'leaderboard', label: 'Leaderboard', icon: Trophy },
    { id: 'suggestions', label: 'AI Suggestions', icon: Sparkles },
    { id: 'profile', label: 'My Profile', icon: User },
  ];

  return (
    <div className="min-h-screen bg-slate-50 flex font-sans text-slate-800">

      {/* Mobile Sidebar Overlay */}
      {isSidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={`
        fixed top-0 left-0 z-50 h-screen w-64 bg-white border-r border-slate-200 transition-transform duration-300 ease-in-out
        lg:translate-x-0 lg:static flex flex-col
        ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        {/* Logo Area */}
        <div className="h-16 flex items-center px-6 border-b border-slate-100">
          {/* Simple Logo Placeholder */}
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center mr-3">
            <Dumbbell className="w-5 h-5 text-white" />
          </div>
          <span className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600">
            AuraFit
          </span>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 px-4 py-6 space-y-1">
          {navItems.map((item) => {
            const isActive = currentView === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  onViewChange(item.id);
                  setIsSidebarOpen(false);
                }}
                className={`
                  w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200
                  ${isActive
                    ? 'bg-blue-50 text-blue-600 shadow-sm'
                    : 'text-slate-500 hover:bg-slate-50 hover:text-slate-900'}
                `}
              >
                <item.icon className={`w-5 h-5 ${isActive ? 'text-blue-600' : 'text-slate-400'}`} />
                {item.label}
              </button>
            );
          })}
        </nav>

        {/* User Profile Snippet (Bottom Sidebar) */}
        <div className="p-4 border-t border-slate-100">
          <div className="flex items-center gap-3 p-3 rounded-xl hover:bg-slate-50 cursor-pointer transition-colors group">
            <img
              src="https://api.dicebear.com/7.x/avataaars/svg?seed=Felix"
              alt="User"
              className="w-10 h-10 rounded-full bg-slate-100 border border-slate-200"
            />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-slate-900 truncate">Alex Morgan</p>
              <p className="text-xs text-slate-500 truncate">Pro Member</p>
            </div>
            <button onClick={onLogout} className="p-1 rounded-full hover:bg-red-50 transition-colors" title="Sign Out">
              <LogOut className="w-4 h-4 text-slate-400 group-hover:text-red-500 transition-colors" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">

        {/* Top Header */}
        <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-4 lg:px-8 sticky top-0 z-30">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setIsSidebarOpen(true)}
              className="p-2 -ml-2 text-slate-500 hover:bg-slate-100 rounded-lg lg:hidden"
            >
              <Menu className="w-6 h-6" />
            </button>

            {/* Search Bar (Visual Only) */}
            <div className="hidden md:flex items-center gap-2 bg-slate-50 px-4 py-2 rounded-lg border border-slate-200 focus-within:border-blue-300 focus-within:ring-2 focus-within:ring-blue-100 transition-all">
              <Search className="w-4 h-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search..."
                className="bg-transparent border-none text-sm outline-none text-slate-700 placeholder:text-slate-400 w-48"
              />
            </div>
          </div>

          <div className="flex items-center gap-4">
            <button className="relative p-2 text-slate-400 hover:bg-slate-50 rounded-full transition-colors">
              <Bell className="w-5 h-5" />
              <span className="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full border-2 border-white"></span>
            </button>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 p-4 lg:p-8 overflow-y-auto">
          <div className="max-w-7xl mx-auto">
            {children}
          </div>
        </main>

      </div>
    </div>
  );
};

export default DashboardLayout;
