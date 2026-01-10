import React, { createContext, useState, useContext, useEffect } from 'react';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check for saved session in localStorage
    const savedUser = localStorage.getItem('auraFitUser');
    if (savedUser) {
      setUser(JSON.parse(savedUser));
    }
    setLoading(false);
  }, []);

  const login = async (email, password) => {
    // ============================================
    // 🔧 BACKEND INTEGRATION POINT - LOGIN
    // ============================================
    // TODO: Replace this dummy logic with actual API call
    // Example:
    // try {
    //   const response = await fetch('/api/auth/login', {
    //     method: 'POST',
    //     headers: { 'Content-Type': 'application/json' },
    //     body: JSON.stringify({ email, password })
    //   });
    //   const data = await response.json();
    //   if (response.ok) {
    //     setUser(data.user);
    //     localStorage.setItem('auraFitUser', JSON.stringify(data.user));
    //     localStorage.setItem('authToken', data.token); // Store JWT token
    //     return { success: true };
    //   } else {
    //     return { success: false, error: data.message };
    //   }
    // } catch (error) {
    //   return { success: false, error: 'Network error' };
    // }
    // ============================================

    // DUMMY LOGIN - Accepts any email/password
    if (email && password) {
      const userData = {
        name: email.split('@')[0].charAt(0).toUpperCase() + email.split('@')[0].slice(1),
        email,
        role: 'user',
        age: 28,
        gender: 'male',
        height: 175,
        weight: 70,
        medicalConditions: { heartIssues: false, diabetes: false, jointPain: false }
      };
      setUser(userData);
      localStorage.setItem('auraFitUser', JSON.stringify(userData));
      return { success: true };
    }
    return { success: false, error: 'Please enter email and password' };
  };

  const logout = () => {
    // ============================================
    // 🔧 BACKEND INTEGRATION POINT - LOGOUT
    // ============================================
    // TODO: Add API call to invalidate session/token
    // Example:
    // await fetch('/api/auth/logout', {
    //   method: 'POST',
    //   headers: { 'Authorization': `Bearer ${localStorage.getItem('authToken')}` }
    // });
    // localStorage.removeItem('authToken');
    // ============================================

    setUser(null);
    localStorage.removeItem('auraFitUser');
  };

  const register = async (userData) => {
    // ============================================
    // 🔧 BACKEND INTEGRATION POINT - REGISTRATION
    // ============================================
    // TODO: Replace this dummy logic with actual API call
    // Example:
    // try {
    //   const response = await fetch('/api/auth/register', {
    //     method: 'POST',
    //     headers: { 'Content-Type': 'application/json' },
    //     body: JSON.stringify(userData)
    //   });
    //   const data = await response.json();
    //   if (response.ok) {
    //     setUser(data.user);
    //     localStorage.setItem('auraFitUser', JSON.stringify(data.user));
    //     localStorage.setItem('authToken', data.token);
    //     return { success: true };
    //   } else {
    //     return { success: false, error: data.message };
    //   }
    // } catch (error) {
    //   return { success: false, error: 'Network error' };
    // }
    // ============================================

    // DUMMY REGISTRATION - Auto-creates account with provided data
    const newUser = {
      ...userData,
      role: 'user',
      email: userData.email || `${userData.name.toLowerCase().replace(/\s+/g, '')}@aurafit.com`
    };
    setUser(newUser);
    localStorage.setItem('auraFitUser', JSON.stringify(newUser));
    return { success: true };
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, register, loading }}>
      {!loading && children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
