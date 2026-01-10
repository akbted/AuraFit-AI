import React, { useState } from 'react';
import { Trophy, Medal, Crown, TrendingUp, Users, Flame, Target, Zap } from 'lucide-react';

// Dummy leaderboard data
const GLOBAL_LEADERBOARD = [
  { id: 1, name: 'Alex Morgan', avatar: 'Felix', score: 12540, workouts: 124, streak: 12, rank: 1, change: 0 },
  { id: 2, name: 'Sarah Chen', avatar: 'Aneka', score: 11890, workouts: 118, streak: 15, rank: 2, change: 1 },
  { id: 3, name: 'Mike Johnson', avatar: 'Bob', score: 11200, workouts: 112, streak: 8, rank: 3, change: -1 },
  { id: 4, name: 'Emma Davis', avatar: 'Emery', score: 10850, workouts: 108, streak: 10, rank: 4, change: 2 },
  { id: 5, name: 'James Wilson', avatar: 'George', score: 10500, workouts: 105, streak: 7, rank: 5, change: 0 },
  { id: 6, name: 'Olivia Brown', avatar: 'Sophie', score: 10200, workouts: 102, streak: 9, rank: 6, change: -2 },
  { id: 7, name: 'Liam Martinez', avatar: 'Max', score: 9800, workouts: 98, streak: 6, rank: 7, change: 1 },
  { id: 8, name: 'Sophia Garcia', avatar: 'Lucy', score: 9500, workouts: 95, streak: 11, rank: 8, change: 0 },
  { id: 9, name: 'Noah Anderson', avatar: 'Charlie', score: 9200, workouts: 92, streak: 5, rank: 9, change: -1 },
  { id: 10, name: 'Ava Taylor', avatar: 'Mia', score: 8900, workouts: 89, streak: 4, rank: 10, change: 0 },
];

const FRIENDS_LEADERBOARD = [
  { id: 1, name: 'Alex Morgan', avatar: 'Felix', score: 12540, workouts: 124, streak: 12, rank: 1, change: 0 },
  { id: 2, name: 'Sarah Chen', avatar: 'Aneka', score: 11890, workouts: 118, streak: 15, rank: 2, change: 1 },
  { id: 4, name: 'Emma Davis', avatar: 'Emery', score: 10850, workouts: 108, streak: 10, rank: 3, change: 0 },
  { id: 7, name: 'Liam Martinez', avatar: 'Max', score: 9800, workouts: 98, streak: 6, rank: 4, change: 1 },
  { id: 9, name: 'Noah Anderson', avatar: 'Charlie', score: 9200, workouts: 92, streak: 5, rank: 5, change: -1 },
];

const Leaderboard = () => {
  const [activeTab, setActiveTab] = useState('global'); // 'global' or 'friends'
  const currentUserId = 1; // Alex Morgan

  const leaderboardData = activeTab === 'global' ? GLOBAL_LEADERBOARD : FRIENDS_LEADERBOARD;

  const getRankIcon = (rank) => {
    if (rank === 1) return <Crown className="w-6 h-6 text-yellow-500 fill-current" />;
    if (rank === 2) return <Medal className="w-6 h-6 text-slate-400 fill-current" />;
    if (rank === 3) return <Medal className="w-6 h-6 text-amber-600 fill-current" />;
    return <span className="text-lg font-bold text-slate-400">#{rank}</span>;
  };

  const getRankBadgeColor = (rank) => {
    if (rank === 1) return 'bg-gradient-to-br from-yellow-400 to-yellow-600';
    if (rank === 2) return 'bg-gradient-to-br from-slate-300 to-slate-500';
    if (rank === 3) return 'bg-gradient-to-br from-amber-400 to-amber-600';
    return 'bg-slate-100';
  };

  const getChangeIndicator = (change) => {
    if (change > 0) return <div className="flex items-center text-green-600 text-xs font-medium"><TrendingUp className="w-3 h-3 mr-1" />+{change}</div>;
    if (change < 0) return <div className="flex items-center text-red-600 text-xs font-medium"><TrendingUp className="w-3 h-3 mr-1 rotate-180" />{change}</div>;
    return <div className="text-slate-400 text-xs">—</div>;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <Trophy className="w-7 h-7 text-yellow-500" />
            Leaderboard
          </h1>
          <p className="text-slate-500 mt-1">Compete with the community and climb the ranks!</p>
        </div>
        
        {/* Tab Switcher */}
        <div className="flex gap-2 bg-slate-100 p-1 rounded-xl">
          <button
            onClick={() => setActiveTab('global')}
            className={`px-6 py-2 rounded-lg font-medium text-sm transition-all ${
              activeTab === 'global'
                ? 'bg-white text-blue-600 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Users className="w-4 h-4 inline mr-2" />
            Global
          </button>
          <button
            onClick={() => setActiveTab('friends')}
            className={`px-6 py-2 rounded-lg font-medium text-sm transition-all ${
              activeTab === 'friends'
                ? 'bg-white text-blue-600 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Users className="w-4 h-4 inline mr-2" />
            Friends
          </button>
        </div>
      </div>

      {/* Top 3 Podium */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {leaderboardData.slice(0, 3).map((user, index) => {
          const isCurrentUser = user.id === currentUserId;
          return (
            <div
              key={user.id}
              className={`bg-white rounded-2xl p-6 border-2 shadow-lg hover:shadow-xl transition-all ${
                isCurrentUser ? 'border-blue-500 ring-4 ring-blue-100' : 'border-slate-200'
              } ${index === 0 ? 'md:order-2 md:scale-105' : index === 1 ? 'md:order-1' : 'md:order-3'}`}
            >
              <div className="flex flex-col items-center text-center">
                {/* Rank Badge */}
                <div className={`w-16 h-16 rounded-full ${getRankBadgeColor(user.rank)} flex items-center justify-center mb-4 shadow-lg`}>
                  {getRankIcon(user.rank)}
                </div>
                
                {/* Avatar */}
                <img
                  src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${user.avatar}`}
                  alt={user.name}
                  className="w-20 h-20 rounded-full border-4 border-white shadow-md mb-3"
                />
                
                {/* Name */}
                <h3 className="font-bold text-lg text-slate-800 mb-1">
                  {user.name}
                  {isCurrentUser && <span className="ml-2 text-blue-600 text-sm">(You)</span>}
                </h3>
                
                {/* Score */}
                <div className="flex items-center gap-1 text-2xl font-black text-slate-900 mb-3">
                  <Flame className="w-6 h-6 text-orange-500" />
                  {user.score.toLocaleString()}
                </div>
                
                {/* Stats */}
                <div className="grid grid-cols-2 gap-3 w-full mt-4">
                  <div className="bg-slate-50 rounded-lg p-2">
                    <p className="text-xs text-slate-500 font-medium">Workouts</p>
                    <p className="text-lg font-bold text-slate-800">{user.workouts}</p>
                  </div>
                  <div className="bg-slate-50 rounded-lg p-2">
                    <p className="text-xs text-slate-500 font-medium">Streak</p>
                    <p className="text-lg font-bold text-slate-800">{user.streak}🔥</p>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Full Leaderboard Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-6 border-b border-slate-200">
          <h2 className="text-lg font-bold text-slate-800">Full Rankings</h2>
          <p className="text-sm text-slate-500 mt-1">Complete leaderboard standings</p>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Rank</th>
                <th className="px-6 py-3 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">User</th>
                <th className="px-6 py-3 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Score</th>
                <th className="px-6 py-3 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Workouts</th>
                <th className="px-6 py-3 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Streak</th>
                <th className="px-6 py-3 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Change</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {leaderboardData.map((user) => {
                const isCurrentUser = user.id === currentUserId;
                return (
                  <tr
                    key={user.id}
                    className={`hover:bg-slate-50 transition-colors ${
                      isCurrentUser ? 'bg-blue-50 hover:bg-blue-100' : ''
                    }`}
                  >
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        {getRankIcon(user.rank)}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-3">
                        <img
                          src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${user.avatar}`}
                          alt={user.name}
                          className="w-10 h-10 rounded-full border-2 border-slate-200"
                        />
                        <div>
                          <p className="font-semibold text-slate-800">
                            {user.name}
                            {isCurrentUser && <span className="ml-2 text-xs text-blue-600 font-bold">(YOU)</span>}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-1 font-bold text-slate-900">
                        <Flame className="w-4 h-4 text-orange-500" />
                        {user.score.toLocaleString()}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-1 text-slate-700">
                        <Target className="w-4 h-4 text-blue-500" />
                        {user.workouts}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-1 font-semibold text-slate-800">
                        <Zap className="w-4 h-4 text-yellow-500 fill-current" />
                        {user.streak} days
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getChangeIndicator(user.change)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Your Stats Summary */}
      <div className="bg-gradient-to-br from-blue-600 to-indigo-600 rounded-2xl p-6 text-white shadow-xl">
        <h3 className="text-lg font-bold mb-4">Your Performance</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4 border border-white/20">
            <p className="text-sm text-blue-100 mb-1">Current Rank</p>
            <p className="text-3xl font-black">#1</p>
          </div>
          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4 border border-white/20">
            <p className="text-sm text-blue-100 mb-1">Total Score</p>
            <p className="text-3xl font-black">12,540</p>
          </div>
          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4 border border-white/20">
            <p className="text-sm text-blue-100 mb-1">Next Rank</p>
            <p className="text-3xl font-black">—</p>
          </div>
          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4 border border-white/20">
            <p className="text-sm text-blue-100 mb-1">Points Ahead</p>
            <p className="text-3xl font-black">+650</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Leaderboard;
