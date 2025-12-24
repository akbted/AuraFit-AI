import React, { useState, useEffect } from 'react';
import { User, Heart, Activity, AlertCircle, CheckCircle2, ArrowLeft } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

/**
 * ProfileForm Component
 * 
 * Functions as both a Profile Editor and Registration Form.
 */
const ProfileForm = ({ isRegistration = false, onNavigate }) => {
  const { user, register } = useAuth();
  
  const [formData, setFormData] = useState({
    name: user?.name || '', 
    age: user?.age || '', 
    gender: user?.gender || '', 
    height: user?.height || '', 
    weight: user?.weight || '',
    medicalConditions: user?.medicalConditions || { heartIssues: false, diabetes: false, jointPain: false }
  });

  const [bmi, setBmi] = useState(null);
  const [bmiCategory, setBmiCategory] = useState('');

  useEffect(() => {
    const { height, weight } = formData;
    if (height && weight && parseFloat(height) > 0 && parseFloat(weight) > 0) {
      const h = parseFloat(height) / 100;
      const w = parseFloat(weight);
      const val = w / (h * h);
      setBmi(val.toFixed(1));
      if (val < 18.5) setBmiCategory('Underweight');
      else if (val < 25) setBmiCategory('Normal');
      else if (val < 30) setBmiCategory('Overweight');
      else setBmiCategory('Obese');
    } else {
      setBmi(null);
      setBmiCategory('');
    }
  }, [formData.height, formData.weight]);

  const handleInputChange = (e) => setFormData({ ...formData, [e.target.name]: e.target.value });
  
  const handleCheckboxChange = (key) => {
    setFormData(prev => ({
      ...prev,
      medicalConditions: { ...prev.medicalConditions, [key]: !prev.medicalConditions[key] }
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (isRegistration) {
      // Register via context
      register(formData);
      // Main App component should handle the redirect based on auth state change
    } else {
      console.log('Profile Updated:', formData);
      // In a real app, updateProfile(formData)
    }
  };

  const getBmiColor = () => {
    switch (bmiCategory) {
      case 'Normal': return 'text-green-600 bg-green-50 border-green-200';
      case 'Overweight': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'Obese': return 'text-red-600 bg-red-50 border-red-200';
      default: return 'text-blue-600 bg-blue-50 border-blue-200';
    }
  };

  return (
    <div className={isRegistration ? "min-h-screen bg-white flex flex-col items-center justify-center p-4" : "max-w-3xl mx-auto py-8"}>
      
      {isRegistration && (
        <button 
          onClick={() => onNavigate('landing')}
          className="absolute top-6 left-6 text-slate-500 hover:text-blue-600 flex items-center gap-2 font-medium"
        >
          <ArrowLeft className="w-5 h-5" /> Back
        </button>
      )}

      <div className={isRegistration ? "w-full max-w-2xl" : ""}>
        <div className="text-center mb-10">
          {isRegistration && (
             <h3 className="text-blue-600 font-bold mb-2 uppercase tracking-wider text-sm">AuraFit Registration</h3>
          )}
          <h1 className="text-3xl font-bold text-slate-800 mb-2">
            {isRegistration ? "Create Your Account" : "Your Profile"}
          </h1>
          <p className="text-slate-500">
            {isRegistration ? "Tell us about yourself to get a personalized plan." : "Manage your personal information."}
          </p>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="p-8">
            <form onSubmit={handleSubmit} className="space-y-8">
              
              {/* Personal Info */}
              <section>
                <h2 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
                  <User className="w-5 h-5 text-blue-600" /> Personal Details
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-slate-700 mb-1">Full Name</label>
                    <input type="text" name="name" value={formData.name} onChange={handleInputChange} 
                      className="w-full px-4 py-2 rounded-lg border border-slate-200 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none transition-all"
                      placeholder="e.g. Alex Morgan" required />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Age</label>
                    <input type="number" name="age" value={formData.age} onChange={handleInputChange} 
                      className="w-full px-4 py-2 rounded-lg border border-slate-200 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none transition-all" required />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Gender</label>
                    <select name="gender" value={formData.gender} onChange={handleInputChange} 
                      className="w-full px-4 py-2 rounded-lg border border-slate-200 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none transition-all" required>
                      <option value="">Select</option>
                      <option value="male">Male</option>
                      <option value="female">Female</option>
                      <option value="other">Other</option>
                    </select>
                  </div>
                </div>
              </section>

              {/* Body Metrics */}
              <section>
                <h2 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
                  <Activity className="w-5 h-5 text-blue-600" /> Body Metrics
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
                  <div className="space-y-6">
                     <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">Height (cm)</label>
                      <input type="number" name="height" value={formData.height} onChange={handleInputChange} 
                        className="w-full px-4 py-2 rounded-lg border border-slate-200 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none transition-all" required />
                     </div>
                     <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">Weight (kg)</label>
                      <input type="number" name="weight" value={formData.weight} onChange={handleInputChange} 
                        className="w-full px-4 py-2 rounded-lg border border-slate-200 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none transition-all" required />
                     </div>
                  </div>

                  {/* BMI Card */}
                  {bmi && (
                    <div className={`p-6 rounded-xl border ${getBmiColor()} flex flex-col items-center justify-center text-center h-full`}>
                      <p className="text-sm font-medium opacity-80 uppercase tracking-wide">Your BMI</p>
                      <p className="text-4xl font-bold my-2">{bmi}</p>
                      <span className="px-3 py-1 rounded-full text-xs font-bold bg-white/50 backdrop-blur-sm">{bmiCategory}</span>
                    </div>
                  )}
                </div>
              </section>

              {/* Medical */}
              <section>
                <h2 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
                  <Heart className="w-5 h-5 text-blue-600" /> Health Conditions
                </h2>
                <div className="space-y-3">
                  { Object.entries({ heartIssues: 'Heart Condition', diabetes: 'Diabetes', jointPain: 'Joint Pain' }).map(([key, label]) => (
                    <label key={key} className="flex items-center p-4 border border-slate-200 rounded-xl hover:bg-slate-50 cursor-pointer transition-colors">
                      <input type="checkbox" checked={formData.medicalConditions[key]} onChange={() => handleCheckboxChange(key)} 
                         className="w-5 h-5 rounded text-blue-600 focus:ring-blue-500 border-gray-300" />
                      <span className="ml-3 font-medium text-slate-700">{label}</span>
                    </label>
                  ))}
                </div>
              </section>

              <div className="pt-4 border-t border-slate-100">
                 <button type="submit" className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-4 rounded-xl shadow-lg shadow-blue-600/20 transition-all hover:scale-[1.02] active:scale-[0.98]">
                   {isRegistration ? "Create Account & Start" : "Save Changes"}
                 </button>
                 
                 {isRegistration && (
                   <p className="text-center mt-4 text-sm text-slate-500">
                     Already have an account? <button type="button" onClick={() => onNavigate('login')} className="text-blue-600 font-bold hover:underline">Sign In</button>
                   </p>
                 )}
              </div>

            </form>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProfileForm;
