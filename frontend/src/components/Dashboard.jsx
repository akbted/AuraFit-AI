import React, { useState, useEffect } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Activity, Flame, Clock, Trophy, MoreHorizontal, TrendingUp, AlertCircle, ArrowRight } from 'lucide-react';

const Dashboard = ({ onNavigate }) => {
  const [hasCompletedAssessment, setHasCompletedAssessment] = useState(false);

  useEffect(() => {
    try {
      const assessment = localStorage.getItem('fitnessAssessment_v2');
      if (assessment) {
        const parsed = JSON.parse(assessment);
        // Only consider complete if we have actual results
        if (parsed && parsed.results && Object.keys(parsed.results).length > 0) {
          setHasCompletedAssessment(true);
          return;
        }
      }
    } catch (e) {
      console.error('Error parsing assessment data', e);
    }
    setHasCompletedAssessment(false); // Default to false if missing or invalid
  }, []);

  // Mock Data for the Activity Chart
  const activityData = [
    { name: 'Mon', calories: 240, active: 40 },
    { name: 'Tue', calories: 139, active: 30 },
    { name: 'Wed', calories: 980, active: 110 },
    { name: 'Thu', calories: 390, active: 55 },
    { name: 'Fri', calories: 480, active: 70 },
    { name: 'Sat', calories: 380, active: 60 },
    { name: 'Sun', calories: 430, active: 65 },
  ];

  // Stats Card Component for Reusability
  const StatsCard = ({ title, value, subValue, icon: Icon, color, trend }) => (
    <div className="bg-white p-6 rounded-xl border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex justify-between items-start mb-4">
        <div className={`p-3 rounded-lg ${color} bg-opacity-10`}>
          <Icon className={`w-6 h-6 ${color.replace('bg-', 'text-')}`} />
        </div>
        <button className="text-slate-400 hover:text-slate-600">
          <MoreHorizontal className="w-5 h-5" />
        </button>
      </div>
      <div>
        <h3 className="text-3xl font-bold text-slate-800 mb-1">{value}</h3>
        <p className="text-slate-500 text-sm font-medium">{title}</p>
        {trend && (
          <div className="flex items-center gap-1 mt-3 text-sm font-medium text-emerald-600">
            <TrendingUp className="w-4 h-4" />
            <span>{trend}</span>
            <span className="text-slate-400 font-normal">vs last month</span>
          </div>
        )}
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Welcome Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Welcome Back, Alex! 👋</h1>
          <p className="text-slate-500">Here's what's happening with your fitness today.</p>
        </div>
        <div className="flex gap-3">
          <select className="bg-white border border-slate-200 text-slate-700 py-2 px-4 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-100">
            <option>Last 7 Days</option>
            <option>Last 30 Days</option>
          </select>
          <button
            onClick={() => onNavigate && onNavigate('workout')}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            Start Workout
          </button>
        </div>
      </div>

      {/* Assessment Reminder Ticket */}
      {!hasCompletedAssessment && (
        <div className="bg-gradient-to-r from-violet-600 to-indigo-600 rounded-2xl p-6 text-white shadow-lg relative overflow-hidden group">
          <div className="absolute right-0 top-0 w-64 h-64 bg-white opacity-5 rounded-full transform translate-x-1/2 -translate-y-1/2" />
          <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-white/20 rounded-xl backdrop-blur-sm">
                <AlertCircle className="w-6 h-6 text-white" />
              </div>
              <div>
                <h3 className="text-lg font-bold mb-1">Assessment Not Completed</h3>
                <p className="text-blue-100 text-sm max-w-xl">
                  Please take your fitness assessment to get accurate, personalized workout suggestions and track your progress effectively.
                </p>
              </div>
            </div>
            <button
              onClick={() => onNavigate && onNavigate('assessment')}
              className="whitespace-nowrap bg-white text-indigo-600 px-6 py-3 rounded-xl font-bold text-sm shadow-md hover:bg-blue-50 transition-colors flex items-center gap-2"
            >
              Take Assessment <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatsCard
          title="Total Workouts"
          value="124"
          icon={Activity}
          color="bg-blue-500"
          trend="+12%"
        />
        <StatsCard
          title="Calories Burned"
          value="12,540"
          icon={Flame}
          color="bg-orange-500"
          trend="+8.2%"
        />
        <StatsCard
          title="Hours Trained"
          value="48.5"
          icon={Clock}
          color="bg-purple-500"
          trend="+4%"
        />
        <StatsCard
          title="Current Streak"
          value="12 Days"
          icon={Trophy}
          color="bg-yellow-500"
          trend=""
        />
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Chart */}
        <div className="lg:col-span-2 bg-white p-6 rounded-xl border border-slate-100 shadow-sm">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-lg font-bold text-slate-800">Activity Overview</h2>
            <div className="flex gap-2">
              <span className="px-3 py-1 bg-blue-50 text-blue-600 text-xs font-semibold rounded-full">Calories</span>
              <span className="px-3 py-1 bg-slate-50 text-slate-500 text-xs font-semibold rounded-full">Time</span>
            </div>
          </div>

          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={activityData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorCalories" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis
                  dataKey="name"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: '#64748b', fontSize: 12 }}
                  dy={10}
                />
                <YAxis
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: '#64748b', fontSize: 12 }}
                />
                <Tooltip
                  contentStyle={{ backgroundColor: '#fff', borderRadius: '8px', border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                />
                <Area
                  type="monotone"
                  dataKey="calories"
                  stroke="#3b82f6"
                  strokeWidth={3}
                  fillOpacity={1}
                  fill="url(#colorCalories)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Side/Upcoming Schedule Panel */}
        <div className="bg-white p-6 rounded-xl border border-slate-100 shadow-sm">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-lg font-bold text-slate-800">Recent Sessions</h2>
            <button className="text-blue-600 text-sm font-medium hover:underline">View All</button>
          </div>

          <div className="space-y-4">
            {[1, 2, 3, 4].map((item) => (
              <div key={item} className="flex items-center gap-4 p-3 rounded-lg hover:bg-slate-50 transition-colors cursor-pointer border border-transparent hover:border-slate-100">
                <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-bold text-sm">
                  {20 + item}
                </div>
                <div className="flex-1">
                  <h4 className="font-semibold text-slate-800 text-sm">HIIT Workout</h4>
                  <p className="text-xs text-slate-500">10:00 AM • 45 mins</p>
                </div>
                <div className="text-right">
                  <span className="inline-block px-2 py-1 bg-green-100 text-green-700 text-xs font-medium rounded">Done</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
