import React, { useState, useEffect } from 'react';
import { Lock, Eye, EyeOff } from 'lucide-react';
import { authAPI } from '../services/api';

const VERSION = '0.9.0';

/**
 * Simplified AuthGuard - just handles token authentication
 * No version checking needed since frontend and backend are in the same repo
 */
const AuthGuard = ({ children, onAuthenticated }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showToken, setShowToken] = useState(false);
  const [token, setToken] = useState('');
  const [validatingToken, setValidatingToken] = useState(false);

  // Check for existing token on mount
  useEffect(() => {
    const checkExistingAuth = async () => {
      const existingToken = localStorage.getItem('authToken');
      
      if (existingToken && existingToken.trim()) {
        try {
          await authAPI.validateToken(existingToken);
          setIsAuthenticated(true);
          onAuthenticated && onAuthenticated();
        } catch (err) {
          localStorage.removeItem('authToken');
        }
      }
      
      setLoading(false);
    };

    checkExistingAuth();
  }, [onAuthenticated]);

  const handleTokenSubmit = async (e) => {
    e.preventDefault();
    
    if (!token.trim()) {
      setError('Please enter a valid token');
      return;
    }

    try {
      setError(null);
      setValidatingToken(true);

      await authAPI.setAndValidateToken(token.trim());
      
      setIsAuthenticated(true);
      onAuthenticated && onAuthenticated();
      setToken('');
      
    } catch (err) {
      let errorMessage = err.message || 'Token validation failed';
      
      if (errorMessage.includes('Invalid token')) {
        setError('Invalid token. Please check your token and try again.');
      } else if (errorMessage.includes('Cannot connect to API')) {
        setError('Cannot connect to API server. Please check your connection.');
      } else {
        setError('Authentication failed: ' + errorMessage);
      }
    } finally {
      setValidatingToken(false);
    }
  };

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        backgroundColor: '#f8fafc'
      }}>
        <div className="loading-spinner" style={{ width: '40px', height: '40px', borderWidth: '4px' }}></div>
      </div>
    );
  }

  if (isAuthenticated) {
    return children;
  }

  // Login form
  return (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      minHeight: '100vh',
      backgroundColor: '#f8fafc',
      padding: '2rem'
    }}>
      <div style={{
        width: '100%',
        maxWidth: '420px',
        backgroundColor: 'white',
        borderRadius: '12px',
        padding: '2rem',
        boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
        border: '1px solid #e2e8f0'
      }}>
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
          <div style={{ marginBottom: '1rem', minHeight: '60px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <img 
              alt="National Data Platform Logo" 
              src="https://nationaldataplatform.org/National_Data_Platform_horiz_stacked.svg"
              style={{ maxWidth: '220px', maxHeight: '80px', height: 'auto', width: 'auto' }}
            />
          </div>
          <h1 style={{ fontSize: '1.6rem', fontWeight: '700', color: '#1e293b', marginBottom: '0.25rem' }}>
            NDP EndPoint
          </h1>
          <p style={{ color: '#94a3b8', fontSize: '0.75rem', marginTop: '0.5rem' }}>
            v{VERSION}
          </p>
        </div>

        {/* Token Form */}
        <form onSubmit={handleTokenSubmit}>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', fontWeight: '600', color: '#374151', marginBottom: '0.5rem', fontSize: '0.9rem' }}>
              Access Token
            </label>
            <div style={{ position: 'relative' }}>
              <textarea
                placeholder="Enter your access token"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                required
                style={{
                  width: '100%',
                  minHeight: '80px',
                  padding: '0.75rem 2.5rem 0.75rem 0.75rem',
                  border: '2px solid #e2e8f0',
                  borderRadius: '6px',
                  fontSize: '0.875rem',
                  fontFamily: showToken ? 'monospace' : 'text-security-disc, monospace',
                  WebkitTextSecurity: showToken ? 'none' : 'disc',
                  resize: 'vertical',
                  boxSizing: 'border-box'
                }}
              />
              <button
                type="button"
                onClick={() => setShowToken(!showToken)}
                title={showToken ? 'Hide token' : 'Show token'}
                style={{
                  position: 'absolute',
                  top: '0.75rem',
                  right: '0.75rem',
                  background: 'none',
                  border: 'none',
                  color: '#9ca3af',
                  cursor: 'pointer',
                  padding: '0.25rem',
                  borderRadius: '4px'
                }}
              >
                {showToken ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          {error && (
            <div style={{
              backgroundColor: '#fef2f2',
              border: '1px solid #fecaca',
              borderRadius: '6px',
              padding: '0.75rem',
              marginBottom: '1rem',
              color: '#dc2626',
              fontSize: '0.875rem'
            }}>
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={validatingToken || !token.trim()}
            style={{
              width: '100%',
              padding: '0.75rem 1rem',
              backgroundColor: validatingToken || !token.trim() ? '#9ca3af' : '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              fontSize: '0.9rem',
              fontWeight: '600',
              cursor: validatingToken || !token.trim() ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem'
            }}
          >
            {validatingToken ? (
              <>
                <div className="loading-spinner" style={{ width: '18px', height: '18px', borderWidth: '2px' }}></div>
                Validating...
              </>
            ) : (
              <>
                <Lock size={18} />
                Connect
              </>
            )}
          </button>
        </form>

        {/* Help text */}
        <div style={{
          marginTop: '1.5rem',
          padding: '1rem',
          backgroundColor: '#f8fafc',
          borderRadius: '6px',
          border: '1px solid #e2e8f0'
        }}>
          <h4 style={{ color: '#374151', marginBottom: '0.5rem', fontSize: '0.85rem', fontWeight: '600' }}>
            Need a token?
          </h4>
          <p style={{ color: '#64748b', fontSize: '0.8rem', lineHeight: '1.5', margin: 0 }}>
            Go to <strong>nationaldataplatform.org</strong> and register an account. 
            In your user panel you will find your access token.
          </p>
        </div>
      </div>
    </div>
  );
};

export default AuthGuard;
