import React, { useState } from 'react';
import { Lock, User, Eye, EyeOff, AlertCircle, X } from 'lucide-react';
import { authAPI } from '../services/api';

/**
 * Login Modal component for authentication
 * Handles both username/password login and manual token entry
 */
const LoginModal = ({ isOpen, onClose, onSuccess }) => {
  const [loginMode, setLoginMode] = useState('credentials'); // 'credentials' or 'token'
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showPassword, setShowPassword] = useState(false);

  // Form states
  const [credentials, setCredentials] = useState({
    username: '',
    password: ''
  });
  
  const [manualToken, setManualToken] = useState('');

  /**
   * Handle input changes for credentials
   */
  const handleCredentialsChange = (e) => {
    const { name, value } = e.target;
    setCredentials(prev => ({
      ...prev,
      [name]: value
    }));
  };

  /**
   * Handle login with username/password
   */
  const handleCredentialsLogin = async (e) => {
    e.preventDefault();
    
    try {
      setError(null);
      setLoading(true);

      await authAPI.login(credentials.username, credentials.password);
      
      onSuccess && onSuccess();
      onClose();
      
      // Reset form
      setCredentials({ username: '', password: '' });
      
    } catch (err) {
      console.error('Login error:', err);
      setError('Login failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  /**
   * Handle manual token entry
   */
  const handleTokenLogin = (e) => {
    e.preventDefault();
    
    if (!manualToken.trim()) {
      setError('Please enter a valid token');
      return;
    }

    try {
      // Save token to localStorage and update API client
      localStorage.setItem('authToken', manualToken.trim());
      
      // The API client will pick up the token from localStorage
      // via the request interceptor
      
      onSuccess && onSuccess();
      onClose();
      
      // Reset form
      setManualToken('');
      setError(null);
      
    } catch (err) {
      console.error('Token error:', err);
      setError('Invalid token format');
    }
  };

  /**
   * Close modal and reset state
   */
  const handleClose = () => {
    setError(null);
    setCredentials({ username: '', password: '' });
    setManualToken('');
    setLoginMode('credentials');
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: '1rem'
    }}>
      <div style={{
        backgroundColor: 'white',
        borderRadius: '12px',
        padding: '2rem',
        width: '100%',
        maxWidth: '450px',
        maxHeight: '90vh',
        overflow: 'auto',
        boxShadow: '0 10px 25px rgba(0, 0, 0, 0.1)'
      }}>
        {/* Header */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '1.5rem'
        }}>
          <h2 style={{
            margin: 0,
            color: '#1e293b',
            fontSize: '1.5rem',
            fontWeight: '600'
          }}>
            <Lock size={24} style={{ marginRight: '0.5rem' }} />
            Authentication
          </h2>
          <button
            onClick={handleClose}
            style={{
              background: 'none',
              border: 'none',
              color: '#64748b',
              cursor: 'pointer',
              padding: '0.5rem'
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Error Message */}
        {error && (
          <div className="alert alert-error" style={{ marginBottom: '1rem' }}>
            <AlertCircle size={16} />
            {error}
          </div>
        )}

        {/* Mode Toggle */}
        <div style={{ marginBottom: '1.5rem' }}>
          <div style={{
            display: 'flex',
            backgroundColor: '#f1f5f9',
            borderRadius: '8px',
            padding: '0.25rem'
          }}>
            <button
              onClick={() => setLoginMode('credentials')}
              style={{
                flex: 1,
                padding: '0.5rem 1rem',
                border: 'none',
                borderRadius: '6px',
                backgroundColor: loginMode === 'credentials' ? 'white' : 'transparent',
                color: loginMode === 'credentials' ? '#1e293b' : '#64748b',
                fontSize: '0.875rem',
                fontWeight: '500',
                cursor: 'pointer',
                boxShadow: loginMode === 'credentials' ? '0 1px 3px rgba(0, 0, 0, 0.1)' : 'none'
              }}
            >
              Username/Password
            </button>
            <button
              onClick={() => setLoginMode('token')}
              style={{
                flex: 1,
                padding: '0.5rem 1rem',
                border: 'none',
                borderRadius: '6px',
                backgroundColor: loginMode === 'token' ? 'white' : 'transparent',
                color: loginMode === 'token' ? '#1e293b' : '#64748b',
                fontSize: '0.875rem',
                fontWeight: '500',
                cursor: 'pointer',
                boxShadow: loginMode === 'token' ? '0 1px 3px rgba(0, 0, 0, 0.1)' : 'none'
              }}
            >
              Manual Token
            </button>
          </div>
        </div>

        {/* Credentials Form */}
        {loginMode === 'credentials' && (
          <form onSubmit={handleCredentialsLogin}>
            <div className="form-group">
              <label className="form-label">
                <User size={16} style={{ marginRight: '0.5rem' }} />
                Username
              </label>
              <input
                type="text"
                name="username"
                value={credentials.username}
                onChange={handleCredentialsChange}
                className="form-input"
                placeholder="Enter your username"
                required
                autoComplete="username"
              />
            </div>

            <div className="form-group">
              <label className="form-label">
                <Lock size={16} style={{ marginRight: '0.5rem' }} />
                Password
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  type={showPassword ? 'text' : 'password'}
                  name="password"
                  value={credentials.password}
                  onChange={handleCredentialsChange}
                  className="form-input"
                  placeholder="Enter your password"
                  required
                  autoComplete="current-password"
                  style={{ paddingRight: '3rem' }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={{
                    position: 'absolute',
                    right: '0.75rem',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: 'none',
                    border: 'none',
                    color: '#64748b',
                    cursor: 'pointer',
                    padding: 0
                  }}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
              style={{ width: '100%', marginTop: '1rem' }}
            >
              {loading ? (
                <>
                  <div className="loading-spinner" />
                  Logging in...
                </>
              ) : (
                'Login'
              )}
            </button>
          </form>
        )}

        {/* Token Form */}
        {loginMode === 'token' && (
          <form onSubmit={handleTokenLogin}>
            <div className="form-group">
              <label className="form-label">
                <Lock size={16} style={{ marginRight: '0.5rem' }} />
                Bearer Token
              </label>
              <textarea
                value={manualToken}
                onChange={(e) => setManualToken(e.target.value)}
                className="form-input form-textarea"
                placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
                style={{
                  fontFamily: 'monospace',
                  fontSize: '0.875rem',
                  minHeight: '100px',
                  resize: 'vertical'
                }}
                required
              />
              <small style={{ color: '#64748b', display: 'block', marginTop: '0.5rem' }}>
                Paste your Bearer token here (without "Bearer " prefix)
              </small>
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              style={{ width: '100%', marginTop: '1rem' }}
            >
              Save Token
            </button>
          </form>
        )}

        {/* Help Text */}
        <div style={{
          marginTop: '1.5rem',
          padding: '1rem',
          backgroundColor: '#f8fafc',
          borderRadius: '8px',
          fontSize: '0.875rem',
          color: '#64748b'
        }}>
          <p style={{ margin: 0, marginBottom: '0.5rem' }}>
            <strong>Need help?</strong>
          </p>
          <p style={{ margin: 0 }}>
            Use username/password to get a token automatically, or paste an existing 
            Bearer token if you already have one from your API.
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginModal;