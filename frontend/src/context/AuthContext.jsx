import React, { createContext, useState, useContext, useEffect } from 'react';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check for saved session
    const savedUser = localStorage.getItem('auraFitUser');
    if (savedUser) {
      setUser(JSON.parse(savedUser));
    }
    setLoading(false);
  }, []);

  const login = (email, password) => {
    // Dummy authentication
    if (email === 'admin@gmail.com' && password === 'admin') {
      const userData = { name: 'Admin User', email, role: 'user' };
      setUser(userData);
      localStorage.setItem('auraFitUser', JSON.stringify(userData));
      return { success: true };
    }
    return { success: false, error: 'Invalid email or password' };
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('auraFitUser');
  };

  const register = (userData) => {
    // Mock registration - automatically log in
    const newUser = { ...userData, role: 'user' };
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
