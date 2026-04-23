import React, { useState, useEffect } from 'react';
import { Lock, AlertCircle, Eye, EyeOff, User, Send, CheckCircle } from 'lucide-react';
import { accessRequestsAPI, authAPI } from '../services/api';

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

  // Credentials mode state
  const [authMode, setAuthMode] = useState('token'); // 'token' | 'credentials'
  const [credentials, setCredentials] = useState({ username: '', password: '' });
  const [showPassword, setShowPassword] = useState(false);
  const [loggingIn, setLoggingIn] = useState(false);

  // Access-request flow state. The token is held in component state only —
  // it is never persisted because the user is not allowed into the app.
  const [deniedToken, setDeniedToken] = useState(null);
  const [requestFormOpen, setRequestFormOpen] = useState(false);
  const [requestJustification, setRequestJustification] = useState('');
  const [requestSubmitting, setRequestSubmitting] = useState(false);
  const [requestSubmitted, setRequestSubmitted] = useState(false);
  const [requestError, setRequestError] = useState(null);

  const clearRequestState = () => {
    setDeniedToken(null);
    setRequestFormOpen(false);
    setRequestJustification('');
    setRequestSubmitted(false);
    setRequestError(null);
  };

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
          if (validationError.response?.status === 403) {
            // Keep the token in memory so the user can submit an access
            // request without having to paste it again.
            setDeniedToken(existingToken);
            setError(
              validationError.response.data?.detail
              || 'You do not have permission to access this Endpoint.'
            );
          } else {
            setError('Your session has expired. Please enter a valid token.');
          }
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
      clearRequestState();
      setValidatingToken(true);

      const userInfo = await authAPI.setAndValidateToken(token.trim());
      console.log('Token validation successful, user info:', userInfo);

      setIsAuthenticated(true);
      onAuthenticated && onAuthenticated();
      setToken('');

    } catch (err) {
      console.error('Token validation error:', err);

      let errorMessage = err.message || 'Token validation failed';
      // If the IDP accepted the token but the Endpoint denied entry,
      // hold the raw token so the user can request access without
      // re-entering it.
      if (err.deniedToken) {
        setDeniedToken(err.deniedToken);
      }

      if (errorMessage.includes('Invalid token')) {
        setError('Invalid token. Please check your token and try again.');
      } else if (errorMessage.includes('Cannot connect to API')) {
        setError('Cannot connect to API server. Please check your connection.');
      } else if (errorMessage.toLowerCase().includes('access forbidden')
          || errorMessage.toLowerCase().includes('permission to access')) {
        setError(errorMessage);
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
   * Handle credentials input changes.
   */
  const handleCredentialsChange = (e) => {
    const { name, value } = e.target;
    setCredentials((prev) => ({ ...prev, [name]: value }));
  };

  /**
   * Handle login with username and password.
   */
  const handleCredentialsSubmit = async (e) => {
    e.preventDefault();

    if (!credentials.username.trim() || !credentials.password) {
      setError('Please enter both username and password');
      return;
    }

    try {
      setError(null);
      clearRequestState();
      setLoggingIn(true);

      await authAPI.login(credentials.username.trim(), credentials.password);

      setIsAuthenticated(true);
      onAuthenticated && onAuthenticated();
      setCredentials({ username: '', password: '' });
    } catch (err) {
      console.error('Credentials login error:', err);
      if (err.deniedToken) {
        setDeniedToken(err.deniedToken);
      }
      setError(err.message || 'Login failed');
    } finally {
      setLoggingIn(false);
    }
  };

  /**
   * Submit an access request on behalf of the denied user. The token held
   * in state is attached to this single call and never persisted.
   */
  const handleAccessRequestSubmit = async (e) => {
    e.preventDefault();
    if (!deniedToken) return;

    try {
      setRequestError(null);
      setRequestSubmitting(true);
      await accessRequestsAPI.createWithToken(
        deniedToken,
        requestJustification.trim() || null
      );
      setRequestSubmitted(true);
      setRequestFormOpen(false);
      setRequestJustification('');
    } catch (err) {
      console.error('Access request submission failed:', err);
      if (err.response?.status === 409) {
        setRequestError(
          'You already have a pending access request. An administrator ' +
            'will review it.'
        );
      } else if (err.response?.status === 503) {
        setRequestError(
          'Access requests are disabled on this deployment. ' +
            'Please contact the administrator directly.'
        );
      } else if (err.response?.status === 401 || err.response?.status === 403) {
        setRequestError(
          err.response.data?.detail ||
            'Your session is no longer valid. Please sign in again.'
        );
      } else {
        setRequestError(
          err.response?.data?.detail ||
            err.message ||
            'Could not submit the access request. Please try again.'
        );
      }
    } finally {
      setRequestSubmitting(false);
    }
  };

  /**
   * Switch between token and credentials authentication modes.
   */
  const switchAuthMode = (mode) => {
    setAuthMode(mode);
    setError(null);
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

          {/* Error Message (hidden once the request-submitted view takes over) */}
          {error && !requestSubmitted && (
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

          {/* Access-request CTA — shown when the user is authenticated to
              the IDP but denied entry to this Endpoint */}
          {deniedToken && !requestSubmitted && !requestFormOpen && (
            <div style={{ marginBottom: '1rem' }}>
              <button
                type="button"
                onClick={() => {
                  setRequestFormOpen(true);
                  setRequestError(null);
                }}
                style={{
                  width: '100%',
                  padding: '0.75rem 1rem',
                  backgroundColor: '#ffffff',
                  color: '#2563eb',
                  border: '1px solid #2563eb',
                  borderRadius: '6px',
                  fontSize: '0.9rem',
                  fontWeight: '600',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.5rem'
                }}
              >
                <Send size={16} />
                Request access to this Endpoint
              </button>
            </div>
          )}

          {/* Access-request form */}
          {deniedToken && requestFormOpen && !requestSubmitted && (
            <form
              onSubmit={handleAccessRequestSubmit}
              style={{
                marginBottom: '1rem',
                padding: '1rem',
                border: '1px solid #e2e8f0',
                borderRadius: '6px',
                backgroundColor: '#f8fafc'
              }}
            >
              <label style={{
                display: 'block',
                fontWeight: '600',
                color: '#374151',
                marginBottom: '0.5rem',
                fontSize: '0.9rem'
              }}>
                Justification (optional)
              </label>
              <textarea
                value={requestJustification}
                onChange={(e) => setRequestJustification(e.target.value)}
                placeholder="Briefly explain why you need access."
                maxLength={2000}
                disabled={requestSubmitting}
                style={{
                  width: '100%',
                  minHeight: '80px',
                  padding: '0.65rem',
                  border: '2px solid #e2e8f0',
                  borderRadius: '6px',
                  fontSize: '0.875rem',
                  lineHeight: 1.4,
                  resize: 'vertical',
                  boxSizing: 'border-box',
                  backgroundColor: requestSubmitting ? '#f3f4f6' : 'white'
                }}
              />

              {requestError && (
                <div style={{
                  marginTop: '0.5rem',
                  fontSize: '0.8rem',
                  color: '#dc2626'
                }}>
                  {requestError}
                </div>
              )}

              <div style={{
                display: 'flex',
                gap: '0.5rem',
                marginTop: '0.75rem'
              }}>
                <button
                  type="submit"
                  disabled={requestSubmitting}
                  style={{
                    flex: 1,
                    padding: '0.6rem 0.75rem',
                    backgroundColor: requestSubmitting ? '#9ca3af' : '#2563eb',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    fontSize: '0.85rem',
                    fontWeight: '600',
                    cursor: requestSubmitting ? 'not-allowed' : 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '0.4rem'
                  }}
                >
                  {requestSubmitting ? (
                    <>
                      <div className="loading-spinner" style={{ width: '14px', height: '14px' }} />
                      Sending...
                    </>
                  ) : (
                    <>
                      <Send size={14} />
                      Send request
                    </>
                  )}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setRequestFormOpen(false);
                    setRequestError(null);
                  }}
                  disabled={requestSubmitting}
                  style={{
                    flex: '0 0 auto',
                    padding: '0.6rem 0.9rem',
                    backgroundColor: 'white',
                    color: '#64748b',
                    border: '1px solid #cbd5e1',
                    borderRadius: '6px',
                    fontSize: '0.85rem',
                    fontWeight: '500',
                    cursor: requestSubmitting ? 'not-allowed' : 'pointer'
                  }}
                >
                  Cancel
                </button>
              </div>
            </form>
          )}

          {/* Confirmation after request submission */}
          {requestSubmitted && (
            <div style={{
              marginBottom: '1rem',
              padding: '1rem',
              backgroundColor: '#ecfdf5',
              border: '1px solid #a7f3d0',
              borderRadius: '6px',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '0.6rem'
            }}>
              <CheckCircle size={20} style={{ color: '#059669', flexShrink: 0 }} />
              <div style={{ fontSize: '0.875rem', color: '#065f46', lineHeight: 1.4 }}>
                <strong>Request submitted.</strong> An administrator will review
                your access request. You can close this page — you will be
                notified through your organization once the decision is made.
              </div>
            </div>
          )}

          {/* Token Form */}
          {!requestSubmitted && authMode === 'token' && (
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

            {/* Switch to credentials mode */}
            <div style={{
              textAlign: 'center',
              marginTop: '1rem',
              fontSize: '0.85rem',
              color: '#64748b'
            }}>
              <button
                type="button"
                onClick={() => switchAuthMode('credentials')}
                disabled={validatingToken}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#2563eb',
                  cursor: validatingToken ? 'not-allowed' : 'pointer',
                  padding: 0,
                  fontSize: '0.85rem',
                  textDecoration: 'underline',
                  opacity: validatingToken ? 0.5 : 1
                }}
              >
                or use your login / password
              </button>
            </div>
          </form>
          )}

          {/* Credentials Form */}
          {!requestSubmitted && authMode === 'credentials' && (
          <form onSubmit={handleCredentialsSubmit}>
            <div style={{ marginBottom: '1rem' }}>
              <label style={{
                display: 'block',
                fontWeight: '600',
                color: '#374151',
                marginBottom: '0.5rem',
                fontSize: '0.9rem'
              }}>
                <User size={14} style={{ marginRight: '0.35rem', verticalAlign: 'middle' }} />
                Username
              </label>
              <input
                type="text"
                name="username"
                value={credentials.username}
                onChange={handleCredentialsChange}
                placeholder="Enter your username"
                required
                disabled={loggingIn}
                autoComplete="username"
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '2px solid #e2e8f0',
                  borderRadius: '6px',
                  fontSize: '0.875rem',
                  transition: 'border-color 0.3s ease',
                  backgroundColor: loggingIn ? '#f3f4f6' : 'white',
                  opacity: loggingIn ? 0.6 : 1,
                  boxSizing: 'border-box'
                }}
                onFocus={(e) => {
                  if (!loggingIn) {
                    e.target.style.borderColor = '#2563eb';
                    e.target.style.boxShadow = '0 0 0 3px rgba(37, 99, 235, 0.1)';
                  }
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = '#e2e8f0';
                  e.target.style.boxShadow = 'none';
                }}
              />
            </div>

            <div style={{ marginBottom: '1rem' }}>
              <label style={{
                display: 'block',
                fontWeight: '600',
                color: '#374151',
                marginBottom: '0.5rem',
                fontSize: '0.9rem'
              }}>
                <Lock size={14} style={{ marginRight: '0.35rem', verticalAlign: 'middle' }} />
                Password
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  type={showPassword ? 'text' : 'password'}
                  name="password"
                  value={credentials.password}
                  onChange={handleCredentialsChange}
                  placeholder="Enter your password"
                  required
                  disabled={loggingIn}
                  autoComplete="current-password"
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    paddingRight: '2.5rem',
                    border: '2px solid #e2e8f0',
                    borderRadius: '6px',
                    fontSize: '0.875rem',
                    transition: 'border-color 0.3s ease',
                    backgroundColor: loggingIn ? '#f3f4f6' : 'white',
                    opacity: loggingIn ? 0.6 : 1,
                    boxSizing: 'border-box'
                  }}
                  onFocus={(e) => {
                    if (!loggingIn) {
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
                  onClick={() => setShowPassword(!showPassword)}
                  disabled={loggingIn}
                  style={{
                    position: 'absolute',
                    top: '50%',
                    right: '0.75rem',
                    transform: 'translateY(-50%)',
                    background: 'none',
                    border: 'none',
                    color: loggingIn ? '#9ca3af' : '#64748b',
                    cursor: loggingIn ? 'not-allowed' : 'pointer',
                    padding: '0.25rem'
                  }}
                  title={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loggingIn}
              style={{
                width: '100%',
                padding: '0.75rem 1rem',
                backgroundColor: loggingIn ? '#9ca3af' : '#2563eb',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                fontSize: '0.9rem',
                fontWeight: '600',
                cursor: loggingIn ? 'not-allowed' : 'pointer',
                transition: 'all 0.3s ease',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.5rem',
                opacity: loggingIn ? 0.6 : 1
              }}
              onMouseOver={(e) => {
                if (!loggingIn) {
                  e.target.style.backgroundColor = '#1d4ed8';
                  e.target.style.transform = 'translateY(-1px)';
                }
              }}
              onMouseOut={(e) => {
                if (!loggingIn) {
                  e.target.style.backgroundColor = '#2563eb';
                  e.target.style.transform = 'translateY(0)';
                }
              }}
            >
              {loggingIn ? (
                <>
                  <div className="loading-spinner" style={{ width: '16px', height: '16px' }} />
                  Signing in...
                </>
              ) : (
                <>
                  <Lock size={18} />
                  Sign in
                </>
              )}
            </button>

            {/* Switch back to token mode */}
            <div style={{
              textAlign: 'center',
              marginTop: '1rem',
              fontSize: '0.85rem',
              color: '#64748b'
            }}>
              <button
                type="button"
                onClick={() => switchAuthMode('token')}
                disabled={loggingIn}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#2563eb',
                  cursor: loggingIn ? 'not-allowed' : 'pointer',
                  padding: 0,
                  fontSize: '0.85rem',
                  textDecoration: 'underline',
                  opacity: loggingIn ? 0.5 : 1
                }}
              >
                or use an access token
              </button>
            </div>
          </form>
          )}

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
