import React, { useState } from 'react';
import { Sparkles, Target, TrendingUp, Heart, Calendar, Dumbbell, Clock, Zap, ChevronRight, Info } from 'lucide-react';

// Dummy user profile for personalization
const USER_PROFILE = {
    name: 'Alex Morgan',
    age: 28,
    fitnessLevel: 'Intermediate',
    goal: 'Muscle Building',
    healthConditions: ['None'],
    preferences: ['Upper Body', 'HIIT'],
    workoutFrequency: 6, // days per week
    avgWorkoutDuration: 45, // minutes
};

// Dummy personalized suggestions
const DAILY_SUGGESTIONS = [
    {
        id: 1,
        type: 'workout',
        title: 'Recommended Workout Plan',
        description: 'Based on your recent performance and muscle building goal',
        icon: Dumbbell,
        color: 'blue',
        details: [
            '4 sets × 15 Pushups (Focus on form)',
            '3 sets × 20 Squats (Increase depth)',
            '3 sets × 30s Plank (Core stability)',
            '3 sets × 12 Leg Raises',
        ],
        reason: 'Your upper body strength has improved by 15%. Time to challenge yourself with higher reps!',
        priority: 'high',
    },
    {
        id: 2,
        type: 'recovery',
        title: 'Recovery Day Recommended',
        description: 'You\'ve worked out 6 consecutive days',
        icon: Heart,
        color: 'red',
        details: [
            'Light stretching (15 minutes)',
            'Foam rolling for muscle recovery',
            'Stay hydrated (2.5L water)',
            'Get 8+ hours of sleep',
        ],
        reason: 'Your body needs time to repair and build muscle. Rest is just as important as training!',
        priority: 'high',
    },
    {
        id: 3,
        type: 'nutrition',
        title: 'Nutrition Optimization',
        description: 'Fuel your muscle building goals',
        icon: Target,
        color: 'green',
        details: [
            'Daily Calories: 2,200-2,400 kcal',
            'Protein: 150-170g (lean meats, eggs)',
            'Carbs: 250-280g (whole grains, fruits)',
            'Fats: 60-70g (nuts, avocado, olive oil)',
        ],
        reason: 'Based on your 406 cal/day burn rate and muscle building goal, this macro split will optimize your results.',
        priority: 'medium',
    },
    {
        id: 4,
        type: 'timing',
        title: 'Optimal Workout Time',
        description: 'Maximize your performance',
        icon: Clock,
        color: 'purple',
        details: [
            'Best Time: 6:00 PM - 7:30 PM',
            'Your peak performance window',
            'Avoid: Early morning (lower energy)',
            'Pre-workout meal: 2 hours before',
        ],
        reason: 'Your data shows 23% better performance during evening sessions. Your body is naturally stronger at this time.',
        priority: 'low',
    },
    {
        id: 5,
        type: 'challenge',
        title: 'Weekly Challenge',
        description: 'Push your limits this week',
        icon: Zap,
        color: 'yellow',
        details: [
            'Goal: 3,000 calories burned this week',
            'Current: 2,840 calories',
            'Remaining: 160 calories (1 HIIT session)',
            'Reward: +500 leaderboard points',
        ],
        reason: 'You\'re so close! One more intense session and you\'ll unlock bonus points and maintain your #1 rank.',
        priority: 'medium',
    },
    {
        id: 6,
        type: 'variety',
        title: 'Add Exercise Variety',
        description: 'Prevent plateau and boredom',
        icon: TrendingUp,
        color: 'indigo',
        details: [
            'Try: Pull-ups (back strength)',
            'Try: Burpees (full body cardio)',
            'Try: Mountain climbers (core + cardio)',
            'Reduce: Pushup frequency (avoid overuse)',
        ],
        reason: 'You\'ve done pushups in 80% of your workouts. Adding variety will target different muscle groups and prevent overuse injuries.',
        priority: 'medium',
    },
];

const Suggestions = () => {
    const [selectedSuggestion, setSelectedSuggestion] = useState(null);

    const getColorClasses = (color) => {
        const colors = {
            blue: {
                bg: 'bg-blue-100',
                text: 'text-blue-600',
                border: 'border-blue-200',
                icon: 'bg-blue-500',
                badge: 'bg-blue-500',
            },
            red: {
                bg: 'bg-red-100',
                text: 'text-red-600',
                border: 'border-red-200',
                icon: 'bg-red-500',
                badge: 'bg-red-500',
            },
            green: {
                bg: 'bg-green-100',
                text: 'text-green-600',
                border: 'border-green-200',
                icon: 'bg-green-500',
                badge: 'bg-green-500',
            },
            purple: {
                bg: 'bg-purple-100',
                text: 'text-purple-600',
                border: 'border-purple-200',
                icon: 'bg-purple-500',
                badge: 'bg-purple-500',
            },
            yellow: {
                bg: 'bg-yellow-100',
                text: 'text-yellow-600',
                border: 'border-yellow-200',
                icon: 'bg-yellow-500',
                badge: 'bg-yellow-500',
            },
            indigo: {
                bg: 'bg-indigo-100',
                text: 'text-indigo-600',
                border: 'border-indigo-200',
                icon: 'bg-indigo-500',
                badge: 'bg-indigo-500',
            },
        };
        return colors[color] || colors.blue;
    };

    const getPriorityBadge = (priority) => {
        if (priority === 'high') {
            return <span className="px-2 py-1 bg-red-100 text-red-700 text-xs font-bold rounded-full">HIGH PRIORITY</span>;
        }
        if (priority === 'medium') {
            return <span className="px-2 py-1 bg-yellow-100 text-yellow-700 text-xs font-bold rounded-full">RECOMMENDED</span>;
        }
        return <span className="px-2 py-1 bg-slate-100 text-slate-600 text-xs font-bold rounded-full">OPTIONAL</span>;
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="bg-gradient-to-br from-indigo-600 to-purple-600 rounded-2xl p-6 text-white shadow-xl">
                <div className="flex items-start justify-between">
                    <div className="flex-1">
                        <h1 className="text-2xl font-bold flex items-center gap-2 mb-2">
                            <Sparkles className="w-7 h-7 text-yellow-300" />
                            Personalized Suggestions
                        </h1>
                        <p className="text-indigo-100 text-sm mb-4">
                            AI-powered recommendations tailored to your fitness journey
                        </p>

                        {/* User Profile Summary */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
                            <div className="bg-white/10 backdrop-blur-sm rounded-lg p-3 border border-white/20">
                                <p className="text-xs text-indigo-200 mb-1">Age</p>
                                <p className="font-bold">{USER_PROFILE.age} years</p>
                            </div>
                            <div className="bg-white/10 backdrop-blur-sm rounded-lg p-3 border border-white/20">
                                <p className="text-xs text-indigo-200 mb-1">Level</p>
                                <p className="font-bold">{USER_PROFILE.fitnessLevel}</p>
                            </div>
                            <div className="bg-white/10 backdrop-blur-sm rounded-lg p-3 border border-white/20">
                                <p className="text-xs text-indigo-200 mb-1">Goal</p>
                                <p className="font-bold">{USER_PROFILE.goal}</p>
                            </div>
                            <div className="bg-white/10 backdrop-blur-sm rounded-lg p-3 border border-white/20">
                                <p className="text-xs text-indigo-200 mb-1">Frequency</p>
                                <p className="font-bold">{USER_PROFILE.workoutFrequency}x/week</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Suggestions Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {DAILY_SUGGESTIONS.map((suggestion) => {
                    const colors = getColorClasses(suggestion.color);
                    const IconComponent = suggestion.icon;

                    return (
                        <div
                            key={suggestion.id}
                            className="bg-white rounded-2xl border-2 border-slate-200 shadow-sm hover:shadow-lg hover:border-slate-300 transition-all cursor-pointer group"
                            onClick={() => setSelectedSuggestion(suggestion.id === selectedSuggestion ? null : suggestion.id)}
                        >
                            <div className="p-6">
                                {/* Header */}
                                <div className="flex items-start justify-between mb-4">
                                    <div className="flex items-start gap-4 flex-1">
                                        <div className={`w-12 h-12 ${colors.icon} rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg`}>
                                            <IconComponent className="w-6 h-6 text-white" />
                                        </div>
                                        <div className="flex-1">
                                            <h3 className="font-bold text-lg text-slate-800 mb-1">{suggestion.title}</h3>
                                            <p className="text-sm text-slate-500">{suggestion.description}</p>
                                        </div>
                                    </div>
                                    <ChevronRight
                                        className={`w-5 h-5 text-slate-400 transition-transform flex-shrink-0 ${selectedSuggestion === suggestion.id ? 'rotate-90' : ''
                                            }`}
                                    />
                                </div>

                                {/* Priority Badge */}
                                <div className="mb-4">
                                    {getPriorityBadge(suggestion.priority)}
                                </div>

                                {/* Expandable Details */}
                                {selectedSuggestion === suggestion.id && (
                                    <div className="mt-4 pt-4 border-t border-slate-200 space-y-4 animate-in slide-in-from-top duration-300">
                                        {/* Details List */}
                                        <div className={`${colors.bg} ${colors.border} border rounded-xl p-4`}>
                                            <h4 className={`font-bold text-sm ${colors.text} mb-3 flex items-center gap-2`}>
                                                <Target className="w-4 h-4" />
                                                Action Items
                                            </h4>
                                            <ul className="space-y-2">
                                                {suggestion.details.map((detail, index) => (
                                                    <li key={index} className="flex items-start gap-2 text-sm text-slate-700">
                                                        <span className={`${colors.text} font-bold`}>•</span>
                                                        <span>{detail}</span>
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>

                                        {/* Reason */}
                                        <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
                                            <h4 className="font-bold text-sm text-slate-700 mb-2 flex items-center gap-2">
                                                <Info className="w-4 h-4" />
                                                Why This Matters
                                            </h4>
                                            <p className="text-sm text-slate-600 leading-relaxed">{suggestion.reason}</p>
                                        </div>

                                        {/* Action Button */}
                                        <button className={`w-full py-3 ${colors.icon} text-white rounded-xl font-semibold hover:opacity-90 transition-all shadow-md`}>
                                            Apply This Suggestion
                                        </button>
                                    </div>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Weekly Goals Summary */}
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
                <h2 className="text-lg font-bold text-slate-800 mb-4 flex items-center gap-2">
                    <Calendar className="w-5 h-5 text-blue-600" />
                    This Week's Focus
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl p-4 border border-blue-200">
                        <p className="text-sm text-blue-700 font-medium mb-1">Primary Goal</p>
                        <p className="text-xl font-bold text-blue-900">Increase Strength</p>
                        <p className="text-xs text-blue-600 mt-2">Focus on progressive overload</p>
                    </div>
                    <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-xl p-4 border border-green-200">
                        <p className="text-sm text-green-700 font-medium mb-1">Recovery Target</p>
                        <p className="text-xl font-bold text-green-900">1 Rest Day</p>
                        <p className="text-xs text-green-600 mt-2">Scheduled for Sunday</p>
                    </div>
                    <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-xl p-4 border border-purple-200">
                        <p className="text-sm text-purple-700 font-medium mb-1">Nutrition Focus</p>
                        <p className="text-xl font-bold text-purple-900">High Protein</p>
                        <p className="text-xs text-purple-600 mt-2">150-170g daily intake</p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Suggestions;
