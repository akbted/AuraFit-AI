import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Sparkles, X, MessageCircle, Minimize2 } from 'lucide-react';

// Dummy AI responses based on keywords
const generateResponse = (userMessage) => {
    const message = userMessage.toLowerCase();

    if (message.includes('progress') || message.includes('how am i doing')) {
        return "Great question! Based on your data:\n\n📊 **Overall Progress**: You're doing fantastic! You've completed 124 workouts this month with a 12-day streak.\n\n🔥 **Calories Burned**: 12,540 total - that's 8.2% higher than last month!\n\n💪 **Strength Gains**: Your pushup count has increased by 15% over the past 2 weeks.\n\n⚡ **Recommendation**: Try increasing your workout intensity by 10% to break through your current plateau.";
    }

    if (message.includes('suggest') || message.includes('recommend') || message.includes('workout')) {
        return "Based on your profile (Age: 28, Goal: Muscle Building, Fitness Level: Intermediate), here are my recommendations:\n\n🎯 **Today's Workout**:\n• 4 sets of 15 pushups\n• 3 sets of 20 squats\n• 3 sets of 30-second planks\n\n💡 **Why?** Your recent data shows strong upper body performance. Let's balance it with more core work.\n\n⏰ **Best Time**: Your performance peaks around 6-7 PM based on your history.";
    }

    if (message.includes('streak') || message.includes('consistency')) {
        return "Your consistency is impressive! 🔥\n\n**Current Streak**: 12 days\n**Longest Streak**: 18 days (achieved last month)\n\n📈 **Trend**: You're most consistent on weekdays. Weekend workouts could use a boost!\n\n💪 **Challenge**: Can you reach a 15-day streak? You're only 3 days away!";
    }

    if (message.includes('calories') || message.includes('burn')) {
        return "Let's look at your calorie burning stats! 🔥\n\n**This Week**: 2,840 calories burned\n**Daily Average**: 406 calories\n**Best Day**: Wednesday (980 calories)\n\n📊 **Insight**: Your HIIT workouts burn 40% more calories than regular sessions. Consider adding 2 more HIIT sessions per week to maximize results!";
    }

    if (message.includes('hello') || message.includes('hi') || message.includes('hey')) {
        return "Hello! 👋 Ready to crush your fitness goals today? I'm here to help with:\n\n• Workout analysis and insights\n• Personalized recommendations\n• Progress tracking\n• Nutrition tips\n• Competition updates\n\nWhat would you like to explore?";
    }

    // Default response
    return "That's an interesting question! I can help with:\n\n• Your workout progress\n• Personalized workout suggestions\n• Calorie burn analysis\n• Streak and consistency\n• Leaderboard rankings\n• Tips to improve performance\n\nWhat would you like to know?";
};

const ChatbotWidget = () => {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState([
        {
            id: 1,
            type: 'bot',
            content: "Hi! 👋 I'm your AuraFit AI assistant. How can I help you today?",
            timestamp: new Date(),
        },
    ]);
    const [inputValue, setInputValue] = useState('');
    const [isTyping, setIsTyping] = useState(false);
    const messagesEndRef = useRef(null);
    const inputRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        if (isOpen) {
            scrollToBottom();
            inputRef.current?.focus();
        }
    }, [messages, isOpen]);

    const handleSendMessage = async (messageText = inputValue) => {
        if (!messageText.trim()) return;

        const userMessage = {
            id: Date.now(),
            type: 'user',
            content: messageText,
            timestamp: new Date(),
        };

        setMessages((prev) => [...prev, userMessage]);
        setInputValue('');
        setIsTyping(true);

        // Simulate AI thinking time
        setTimeout(() => {
            const botResponse = {
                id: Date.now() + 1,
                type: 'bot',
                content: generateResponse(messageText),
                timestamp: new Date(),
            };
            setMessages((prev) => [...prev, botResponse]);
            setIsTyping(false);
        }, 1000 + Math.random() * 1000);
    };

    const formatTime = (date) => {
        return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    };

    return (
        <>
            {/* Floating Chat Button */}
            {!isOpen && (
                <button
                    onClick={() => setIsOpen(true)}
                    className="fixed bottom-6 right-6 w-16 h-16 bg-gradient-to-br from-purple-600 to-indigo-600 text-white rounded-full shadow-2xl hover:shadow-purple-500/50 transition-all hover:scale-110 active:scale-95 flex items-center justify-center z-50 group"
                >
                    <MessageCircle className="w-7 h-7" />
                    <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full border-2 border-white animate-pulse"></span>

                    {/* Tooltip */}
                    <div className="absolute bottom-full right-0 mb-2 px-3 py-2 bg-slate-900 text-white text-sm rounded-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
                        Chat with AI Assistant
                    </div>
                </button>
            )}

            {/* Chat Window */}
            {isOpen && (
                <div className="fixed bottom-6 right-6 w-96 h-[600px] bg-white rounded-2xl shadow-2xl flex flex-col z-50 border border-slate-200 overflow-hidden">
                    {/* Header */}
                    <div className="bg-gradient-to-br from-purple-600 to-indigo-600 p-4 text-white flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 bg-white/20 backdrop-blur-sm rounded-full flex items-center justify-center">
                                <Bot className="w-6 h-6" />
                            </div>
                            <div>
                                <h3 className="font-bold flex items-center gap-1">
                                    AI Assistant
                                    <Sparkles className="w-4 h-4 text-yellow-300" />
                                </h3>
                                <p className="text-xs text-purple-100">Always here to help</p>
                            </div>
                        </div>
                        <div className="flex items-center gap-2">
                            <button
                                onClick={() => setIsOpen(false)}
                                className="p-2 hover:bg-white/10 rounded-lg transition-colors"
                            >
                                <Minimize2 className="w-5 h-5" />
                            </button>
                            <button
                                onClick={() => setIsOpen(false)}
                                className="p-2 hover:bg-white/10 rounded-lg transition-colors"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                    </div>

                    {/* Messages */}
                    <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50">
                        {messages.map((message) => (
                            <div
                                key={message.id}
                                className={`flex gap-2 ${message.type === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
                            >
                                {/* Avatar */}
                                <div
                                    className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${message.type === 'bot'
                                            ? 'bg-gradient-to-br from-purple-500 to-indigo-500 text-white'
                                            : 'bg-gradient-to-br from-blue-500 to-blue-600 text-white'
                                        }`}
                                >
                                    {message.type === 'bot' ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
                                </div>

                                {/* Message Bubble */}
                                <div className={`flex-1 flex flex-col ${message.type === 'user' ? 'items-end' : 'items-start'}`}>
                                    <div
                                        className={`rounded-2xl px-4 py-2 max-w-[85%] ${message.type === 'bot'
                                                ? 'bg-white text-slate-800 shadow-sm'
                                                : 'bg-gradient-to-br from-blue-600 to-blue-700 text-white'
                                            }`}
                                    >
                                        <p className="text-sm whitespace-pre-line leading-relaxed">{message.content}</p>
                                    </div>
                                    <span className="text-xs text-slate-400 mt-1 px-2">
                                        {formatTime(message.timestamp)}
                                    </span>
                                </div>
                            </div>
                        ))}

                        {/* Typing Indicator */}
                        {isTyping && (
                            <div className="flex gap-2">
                                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-indigo-500 text-white flex items-center justify-center">
                                    <Bot className="w-4 h-4" />
                                </div>
                                <div className="bg-white rounded-2xl px-4 py-2 shadow-sm">
                                    <div className="flex gap-1">
                                        <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                                        <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                                        <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                                    </div>
                                </div>
                            </div>
                        )}

                        <div ref={messagesEndRef} />
                    </div>

                    {/* Input Area */}
                    <div className="p-4 bg-white border-t border-slate-200">
                        <div className="flex gap-2">
                            <input
                                ref={inputRef}
                                type="text"
                                value={inputValue}
                                onChange={(e) => setInputValue(e.target.value)}
                                onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                                placeholder="Ask me anything..."
                                className="flex-1 px-4 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent text-sm text-slate-800 placeholder:text-slate-400"
                            />
                            <button
                                onClick={() => handleSendMessage()}
                                disabled={!inputValue.trim()}
                                className="px-4 py-2 bg-gradient-to-br from-purple-600 to-indigo-600 text-white rounded-xl font-semibold hover:from-purple-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-2 shadow-lg shadow-purple-900/30"
                            >
                                <Send className="w-4 h-4" />
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
};

export default ChatbotWidget;
