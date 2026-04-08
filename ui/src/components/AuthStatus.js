import React, { useState, useEffect } from 'react';
import { Lock, Unlock, LogOut, User } from 'lucide-react';
import { authAPI } from '../services/api';

/**
 * Auth Status component to show current authentication state
 * and provide login/logout functionality
 */
const AuthStatus = ({ onLoginClick }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [tokenPreview, setTokenPreview] = useState('');

  /**
   * Check authentication status on component mount
   */
  useEffect(() => {
    checkAuthStatus();
  }, []);

  /**
   * Check if user is authenticated
   */
  const checkAuthStatus = () => {
    const token = localStorage.getItem('authToken');
    const authenticated = !!token;
    
    setIsAuthenticated(authenticated);
    
    if (token) {
      // Show first and last 6 characters of token
      const preview = token.length > 12 
        ? `${token.substring(0, 6)}...${token.substring(token.length - 6)}`
        : token;
      setTokenPreview(preview);
    } else {
      setTokenPreview('');
    }
  };

  /**
   * Handle logout
   */
  const handleLogout = () => {
    if (window.confirm('Are you sure you want to logout?')) {
      authAPI.logout();
      setIsAuthenticated(false);
      setTokenPreview('');

      // Redirect to /ui/ so AuthGuard shows the login screen
      window.location.href = `${window.__EP_CONFIG__?.rootPath ?? ''}/ui/`;
    }
  };

  /**
   * Handle login click
   */
  const handleLoginClick = () => {
    onLoginClick && onLoginClick();
  };

  // Listen for token changes (when login modal saves a token)
  useEffect(() => {
    const handleStorageChange = () => {
      checkAuthStatus();
    };

    window.addEventListener('storage', handleStorageChange);
    
    // Also check periodically in case token was set by the same tab
    const interval = setInterval(checkAuthStatus, 1000);

    return () => {
      window.removeEventListener('storage', handleStorageChange);
      clearInterval(interval);
    };
  }, []);

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '0.75rem',
      padding: '0.5rem 1rem',
      backgroundColor: isAuthenticated 
        ? 'rgba(34, 197, 94, 0.15)' 
        : 'rgba(239, 68, 68, 0.15)',
      borderRadius: '8px',
      border: `1px solid ${isAuthenticated 
        ? 'rgba(34, 197, 94, 0.3)' 
        : 'rgba(239, 68, 68, 0.3)'}`,
      minWidth: 'fit-content',
      whiteSpace: 'nowrap'
    }}>
      {/* Status Icon */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        color: isAuthenticated ? '#059669' : '#dc2626'
      }}>
        {isAuthenticated ? <Unlock size={16} /> : <Lock size={16} />}
      </div>

      {/* Status Info - Compact version */}
      <div style={{ 
        flex: 1, 
        minWidth: 0
      }}>
        <div style={{
          fontSize: '0.875rem',
          fontWeight: '600',
          color: isAuthenticated ? '#059669' : '#dc2626'
        }}>
          {isAuthenticated ? 'Auth' : 'Login'}
        </div>
      </div>

      {/* Action Buttons */}
      <div style={{ display: 'flex', gap: '0.5rem' }}>
        {isAuthenticated ? (
          <button
            onClick={handleLogout}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.25rem',
              padding: '0.375rem 0.75rem',
              fontSize: '0.8rem',
              backgroundColor: '#dc2626',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              transition: 'background-color 0.2s'
            }}
            onMouseOver={(e) => e.target.style.backgroundColor = '#b91c1c'}
            onMouseOut={(e) => e.target.style.backgroundColor = '#dc2626'}
          >
            <LogOut size={12} />
            <span style={{ display: window.innerWidth < 640 ? 'none' : 'inline' }}>
              Logout
            </span>
          </button>
        ) : (
          <button
            onClick={handleLoginClick}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.25rem',
              padding: '0.375rem 0.75rem',
              fontSize: '0.8rem',
              backgroundColor: '#1e40af',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              transition: 'background-color 0.2s'
            }}
            onMouseOver={(e) => e.target.style.backgroundColor = '#1d4ed8'}
            onMouseOut={(e) => e.target.style.backgroundColor = '#1e40af'}
          >
            <User size={12} />
            <span style={{ display: window.innerWidth < 640 ? 'none' : 'inline' }}>
              Login
            </span>
          </button>
        )}
      </div>
    </div>
  );
};

export default AuthStatus;