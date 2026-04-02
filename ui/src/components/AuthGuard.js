import React, { useState, useEffect } from 'react';
import { Lock, AlertCircle, Eye, EyeOff } from 'lucide-react';
import { authAPI } from '../services/api';

/**
 * AuthGuard component that requires authentication before accessing the app
 * Uses /user/info endpoint for proper token validation
 */
const AuthGuard = ({ children, onAuthenticated }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showToken, setShowToken] = useState(false);
  const [token, setToken] = useState('');
  const [validatingToken, setValidatingToken] = useState(false);

  /**
   * Check if user is already authenticated using proper token validation
   */
  useEffect(() => {
    const checkExistingAuth = async () => {
      const existingToken = localStorage.getItem('authToken');

      if (existingToken && existingToken.trim()) {
        console.log('Found existing token, validating...');

        try {
          const userInfo = await authAPI.validateToken(existingToken);
          console.log('Token validation successful:', userInfo);

          setIsAuthenticated(true);
          onAuthenticated && onAuthenticated();
        } catch (validationError) {
          console.error('Token validation failed:', validationError);
          localStorage.removeItem('authToken');
          setError('Your session has expired. Please enter a valid token.');
        }
      }

      setLoading(false);
    };

    checkExistingAuth();
  }, [onAuthenticated]);

  /**
   * Handle token submission with proper validation
   */
  const handleTokenSubmit = async (e) => {
    e.preventDefault();

    if (!token.trim()) {
      setError('Please enter a valid token');
      return;
    }

    try {
      setError(null);
      setValidatingToken(true);

      const userInfo = await authAPI.setAndValidateToken(token.trim());
      console.log('Token validation successful, user info:', userInfo);

      setIsAuthenticated(true);
      onAuthenticated && onAuthenticated();
      setToken('');

    } catch (err) {
      console.error('Token validation error:', err);

      let errorMessage = err.message || 'Token validation failed';

      if (errorMessage.includes('Invalid token')) {
        setError('Invalid token. Please check your token and try again.');
      } else if (errorMessage.includes('Cannot connect to API')) {
        setError('Cannot connect to API server. Please check your connection.');
      } else if (errorMessage.includes('Insufficient permissions')) {
        setError('Token does not have sufficient permissions.');
      } else {
        setError('Authentication failed: ' + errorMessage);
      }
    } finally {
      setValidatingToken(false);
    }
  };

  /**
   * Handle token visibility toggle
   */
  const handleToggleTokenVisibility = () => {
    setShowToken(!showToken);
  };

  /**
   * Show loading state
   */
  if (loading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        backgroundColor: '#f8fafc',
        flexDirection: 'column',
        gap: '1rem'
      }}>
        <div className="loading-spinner" style={{
          width: '40px',
          height: '40px',
          borderWidth: '4px'
        }}></div>
        <p style={{ color: '#64748b', fontSize: '1.1rem' }}>
          Validating authentication...
        </p>
      </div>
    );
  }

  /**
   * Show authentication required screen
   */
  if (!isAuthenticated) {
    return (
      <div style={{
        minHeight: '100vh',
        backgroundColor: '#f8fafc',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        padding: '2rem'
      }}>
        <div style={{
          backgroundColor: 'white',
          borderRadius: '12px',
          padding: '2rem',
          width: '100%',
          maxWidth: '420px',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
          border: '1px solid #e2e8f0'
        }}>
          {/* Header */}
          <div style={{
            textAlign: 'center',
            marginBottom: '1.5rem'
          }}>
            {/* Logo */}
            <div style={{
              marginBottom: '1rem',
              minHeight: '60px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <img
                src="https://nationaldataplatform.org/National_Data_Platform_horiz_stacked.svg"
                alt="National Data Platform Logo"
                style={{
                  maxWidth: '220px',
                  maxHeight: '80px',
                  height: 'auto',
                  width: 'auto'
                }}
                onLoad={() => {
                  console.log('NDP logo loaded successfully');
                }}
                onError={(e) => {
                  console.error('Failed to load NDP logo from nationaldataplatform.org');
                  e.target.style.display = 'none';

                  const fallback = document.createElement('div');
                  fallback.innerHTML = '<div style="font-size: 1.8rem; font-weight: bold; color: #2563eb; margin: 20px 0;">National Data Platform</div>';
                  e.target.parentNode.appendChild(fallback);
                }}
              />
            </div>

            <h1 style={{
              fontSize: '1.6rem',
              fontWeight: '700',
              color: '#1e293b',
              marginBottom: '0.25rem'
            }}>
              NDP EndPoint
            </h1>

            <p style={{
              color: '#64748b',
              fontSize: '1rem',
              lineHeight: '1.4',
              margin: 0
            }}>
              Admin console
            </p>
          </div>

          {/* Error Message */}
          {error && (
            <div style={{
              backgroundColor: '#fef2f2',
              border: '1px solid #fecaca',
              borderRadius: '6px',
              padding: '0.75rem',
              marginBottom: '1rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}>
              <AlertCircle size={20} style={{ color: '#dc2626' }} />
              <span style={{ color: '#dc2626', fontSize: '0.875rem' }}>
                {error}
              </span>
            </div>
          )}

          {/* Token Form */}
          <form onSubmit={handleTokenSubmit}>
            <div style={{ marginBottom: '1rem' }}>
              <label style={{
                display: 'block',
                fontWeight: '600',
                color: '#374151',
                marginBottom: '0.5rem',
                fontSize: '0.9rem'
              }}>
                Access Token
              </label>

              <div style={{ position: 'relative' }}>
                <textarea
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  placeholder="testing_password"
                  required
                  disabled={validatingToken}
                  style={{
                    width: '100%',
                    minHeight: '80px',
                    padding: '0.75rem',
                    paddingRight: '2.5rem',
                    border: '2px solid #e2e8f0',
                    borderRadius: '6px',
                    fontSize: '0.875rem',
                    fontFamily: showToken ? 'monospace' : 'inherit',
                    lineHeight: '1.4',
                    resize: 'vertical',
                    transition: 'border-color 0.3s ease',
                    backgroundColor: validatingToken ? '#f3f4f6' : 'white',
                    opacity: validatingToken ? 0.6 : 1,
                    WebkitTextSecurity: showToken ? 'none' : 'disc',
                    textSecurity: showToken ? 'none' : 'disc',
                    ...(showToken ? {} : {
                      fontFamily: 'text-security-disc, -webkit-small-control, monospace',
                      letterSpacing: '0.125em'
                    })
                  }}
                  onFocus={(e) => {
                    if (!validatingToken) {
                      e.target.style.borderColor = '#2563eb';
                      e.target.style.boxShadow = '0 0 0 3px rgba(37, 99, 235, 0.1)';
                    }
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = '#e2e8f0';
                    e.target.style.boxShadow = 'none';
                  }}
                />

                <button
                  type="button"
                  onClick={handleToggleTokenVisibility}
                  disabled={validatingToken}
                  style={{
                    position: 'absolute',
                    top: '0.75rem',
                    right: '0.75rem',
                    background: 'none',
                    border: 'none',
                    color: validatingToken ? '#9ca3af' : '#64748b',
                    cursor: validatingToken ? 'not-allowed' : 'pointer',
                    padding: '0.25rem',
                    borderRadius: '4px',
                    transition: 'all 0.2s ease',
                    opacity: validatingToken ? 0.5 : 1
                  }}
                  title={showToken ? 'Hide token' : 'Show token'}
                  onMouseOver={(e) => {
                    if (!validatingToken) {
                      e.target.style.backgroundColor = '#f1f5f9';
                      e.target.style.color = '#374151';
                    }
                  }}
                  onMouseOut={(e) => {
                    if (!validatingToken) {
                      e.target.style.backgroundColor = 'transparent';
                      e.target.style.color = '#64748b';
                    }
                  }}
                >
                  {showToken ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>

              {/* Token visibility indicator */}
              <div style={{
                fontSize: '0.75rem',
                color: '#64748b',
                marginTop: '0.25rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.25rem'
              }}>
                {showToken ? (
                  <>
                    <Eye size={12} />
                    <span>Token is visible</span>
                  </>
                ) : (
                  <>
                    <EyeOff size={12} />
                    <span>Token is hidden</span>
                  </>
                )}
              </div>
            </div>

            <button
              type="submit"
              disabled={validatingToken}
              style={{
                width: '100%',
                padding: '0.75rem 1rem',
                backgroundColor: validatingToken ? '#9ca3af' : '#2563eb',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                fontSize: '0.9rem',
                fontWeight: '600',
                cursor: validatingToken ? 'not-allowed' : 'pointer',
                transition: 'all 0.3s ease',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.5rem',
                opacity: validatingToken ? 0.6 : 1
              }}
              onMouseOver={(e) => {
                if (!validatingToken) {
                  e.target.style.backgroundColor = '#1d4ed8';
                  e.target.style.transform = 'translateY(-1px)';
                }
              }}
              onMouseOut={(e) => {
                if (!validatingToken) {
                  e.target.style.backgroundColor = '#2563eb';
                  e.target.style.transform = 'translateY(0)';
                }
              }}
            >
              {validatingToken ? (
                <>
                  <div className="loading-spinner" style={{ width: '16px', height: '16px' }} />
                  Validating...
                </>
              ) : (
                <>
                  <Lock size={18} />
                  Authenticate
                </>
              )}
            </button>
          </form>

          {/* Help Text */}
          <div style={{
            marginTop: '1.5rem',
            padding: '1rem',
            backgroundColor: '#f8fafc',
            borderRadius: '6px',
            border: '1px solid #e2e8f0'
          }}>
            <h4 style={{
              color: '#374151',
              marginBottom: '0.5rem',
              fontSize: '0.85rem',
              fontWeight: '600'
            }}>
              Need a token?
            </h4>
            <p style={{
              color: '#64748b',
              fontSize: '0.8rem',
              lineHeight: '1.5',
              margin: 0
            }}>
              Go to <strong>nationaldataplatform.org</strong> and register an account.
              In your user panel you will find your access token.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // User is authenticated, render the app
  return children;
};

export default AuthGuard;
