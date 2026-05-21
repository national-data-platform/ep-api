import React, { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Home,
  Building2,
  Radio,
  Link as LinkIcon,
  Database,
  Settings,
  Search,
  FileText,
  LogOut,
  ChevronDown,
  HardDrive,
  ShieldAlert,
  Plus
} from 'lucide-react';
import { isAccessRequestAdmin, userAPI } from '../services/api';

/**
 * Enhanced navigation component similar to nationaldataplatform.org
 * Gray background with improved dropdown logic that always closes properly
 */
const Navigation = () => {
  const [isNewMenuOpen, setIsNewMenuOpen] = useState(false);
  const newMenuRef = useRef(null);
  const newButtonRef = useRef(null);
  const newTimeoutRef = useRef(null);
  const [isAdmin, setIsAdmin] = useState(false);
  // canWrite drives the visibility of the "+ New" menu — viewers and
  // users with no role can browse but cannot create new resources.
  const [canWrite, setCanWrite] = useState(false);

  // Determine admin and write-capability status from the current token's
  // /user/info response so the admin-only and writer-only entries are
  // only shown to users that can actually use them.
  useEffect(() => {
    let cancelled = false;
    userAPI
      .getUserInfo()
      .then((response) => {
        if (cancelled) return;
        setIsAdmin(isAccessRequestAdmin(response.data));
        const role = response.data?.effective_role || 'none';
        setCanWrite(role === 'admin' || role === 'writer');
      })
      .catch(() => {
        if (!cancelled) {
          setIsAdmin(false);
          setCanWrite(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Clear timeout on unmount
  useEffect(() => {
    return () => {
      if (newTimeoutRef.current) clearTimeout(newTimeoutRef.current);
    };
  }, []);

  // Close the "+ New" menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        newMenuRef.current &&
        !newMenuRef.current.contains(event.target) &&
        newButtonRef.current &&
        !newButtonRef.current.contains(event.target)
      ) {
        setIsNewMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleNewMenuEnter = () => {
    if (newTimeoutRef.current) clearTimeout(newTimeoutRef.current);
    setIsNewMenuOpen(true);
  };

  const handleNewMenuLeave = () => {
    newTimeoutRef.current = setTimeout(() => {
      setIsNewMenuOpen(false);
    }, 150);
  };

  // Handle mouse entering other nav items - close the menu immediately
  const handleOtherNavEnter = () => {
    if (newTimeoutRef.current) clearTimeout(newTimeoutRef.current);
    setIsNewMenuOpen(false);
  };

  const handleLogout = () => {
    if (window.confirm('Are you sure you want to logout?')) {
      localStorage.removeItem('authToken');
      window.location.href = `${window.__EP_CONFIG__?.rootPath ?? ''}/ui/`;
    }
  };

  return (
    <header style={{
      background: '#f8fafc', // Gray background like the image
      color: '#374151',
      padding: '1rem 0',
      boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
      borderBottom: '1px solid #e5e7eb'
    }}>
      <div style={{
        maxWidth: '1400px',
        margin: '0 auto',
        padding: '0 1rem'
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '1rem'
        }}>
          
          {/* Left: NDP Logo */}
          <div style={{ flex: '0 0 auto' }}>
            <img 
              src="https://nationaldataplatform.org/National_Data_Platform_horiz_stacked.svg"
              alt="National Data Platform"
              style={{
                height: '40px',
                width: 'auto',
                maxWidth: '180px'
              }}
              onError={(e) => {
                e.target.style.display = 'none';
              }}
            />
          </div>

          {/* Center: Navigation Menu */}
          <nav style={{ flex: 1, display: 'flex', justifyContent: 'center' }}>
            <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>

              {/* Search (landing page) */}
              <Link
                to="/"
                onMouseEnter={handleOtherNavEnter}
                style={{
                  color: '#6b7280',
                  textDecoration: 'none',
                  padding: '0.5rem 0.75rem',
                  borderRadius: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  fontSize: '0.95rem',
                  whiteSpace: 'nowrap',
                  fontWeight: '500',
                  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                  backgroundColor: 'transparent',
                  transition: 'all 0.2s ease'
                }}
                onMouseOver={(e) => {
                  e.target.style.color = '#374151';
                  e.target.style.fontWeight = '600';
                }}
                onMouseOut={(e) => {
                  e.target.style.color = '#6b7280';
                  e.target.style.fontWeight = '500';
                }}
              >
                <Search size={18} />
                <span>Search</span>
              </Link>

              {/* S3 Management (bucket/object storage tool) */}
              <Link
                to="/s3-management"
                onMouseEnter={handleOtherNavEnter}
                style={{
                  color: '#6b7280',
                  textDecoration: 'none',
                  padding: '0.5rem 0.75rem',
                  borderRadius: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  fontSize: '0.95rem',
                  whiteSpace: 'nowrap',
                  fontWeight: '500',
                  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                  backgroundColor: 'transparent',
                  transition: 'all 0.2s ease'
                }}
                onMouseOver={(e) => {
                  e.target.style.color = '#374151';
                  e.target.style.fontWeight = '600';
                }}
                onMouseOut={(e) => {
                  e.target.style.color = '#6b7280';
                  e.target.style.fontWeight = '500';
                }}
              >
                <HardDrive size={18} />
                <span>S3 Management</span>
              </Link>

              {/* + New menu — only visible to users that can write */}
              {canWrite && (
              <div
                style={{ position: 'relative' }}
                onMouseEnter={handleNewMenuEnter}
                onMouseLeave={handleNewMenuLeave}
              >
                <button
                  ref={newButtonRef}
                  style={{
                    color: isNewMenuOpen ? '#374151' : '#6b7280',
                    background: 'none',
                    border: 'none',
                    padding: '0.5rem 0.75rem',
                    borderRadius: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.4rem',
                    fontSize: '0.95rem',
                    fontWeight: isNewMenuOpen ? '600' : '500',
                    fontFamily:
                      '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                    cursor: 'pointer',
                    backgroundColor: 'transparent',
                    transition: 'all 0.2s ease',
                    whiteSpace: 'nowrap'
                  }}
                  onMouseOver={(e) => {
                    if (!isNewMenuOpen) {
                      e.target.style.color = '#374151';
                      e.target.style.fontWeight = '600';
                    }
                  }}
                  onMouseOut={(e) => {
                    if (!isNewMenuOpen) {
                      e.target.style.color = '#6b7280';
                      e.target.style.fontWeight = '500';
                    }
                  }}
                >
                  <Plus size={18} />
                  <span>New</span>
                  <ChevronDown size={16} />
                </button>

                {isNewMenuOpen && (
                  <div
                    ref={newMenuRef}
                    style={{
                      position: 'absolute',
                      top: '100%',
                      left: '0',
                      backgroundColor: 'white',
                      borderRadius: '10px',
                      boxShadow: '0 10px 25px rgba(0, 0, 0, 0.15)',
                      border: '1px solid #e5e7eb',
                      minWidth: '220px',
                      zIndex: 1000,
                      marginTop: '0.5rem'
                    }}
                  >
                    <Link
                      to="/organizations"
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.75rem',
                        padding: '1rem 1.25rem',
                        color: '#374151',
                        textDecoration: 'none',
                        fontSize: '0.9rem',
                        fontWeight: '500',
                        backgroundColor: 'white',
                        borderBottom: '1px solid #f3f4f6'
                      }}
                      onMouseOver={(e) => {
                        e.target.style.backgroundColor = '#f9fafb';
                        e.target.style.color = '#2563eb';
                        e.target.style.fontWeight = '600';
                      }}
                      onMouseOut={(e) => {
                        e.target.style.backgroundColor = 'white';
                        e.target.style.color = '#374151';
                        e.target.style.fontWeight = '500';
                      }}
                    >
                      <Building2 size={18} />
                      <span>Organization</span>
                    </Link>

                    <Link
                      to="/datasets"
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.75rem',
                        padding: '1rem 1.25rem',
                        color: '#374151',
                        textDecoration: 'none',
                        fontSize: '0.9rem',
                        fontWeight: '500',
                        backgroundColor: 'white',
                        borderBottom: '1px solid #f3f4f6'
                      }}
                      onMouseOver={(e) => {
                        e.target.style.backgroundColor = '#f9fafb';
                        e.target.style.color = '#2563eb';
                        e.target.style.fontWeight = '600';
                      }}
                      onMouseOut={(e) => {
                        e.target.style.backgroundColor = 'white';
                        e.target.style.color = '#374151';
                        e.target.style.fontWeight = '500';
                      }}
                    >
                      <FileText size={18} />
                      <span>Dataset</span>
                    </Link>

                    <Link
                      to="/services"
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.75rem',
                        padding: '1rem 1.25rem',
                        color: '#374151',
                        textDecoration: 'none',
                        fontSize: '0.9rem',
                        fontWeight: '500',
                        backgroundColor: 'white',
                        borderBottom: '1px solid #f3f4f6'
                      }}
                      onMouseOver={(e) => {
                        e.target.style.backgroundColor = '#f9fafb';
                        e.target.style.color = '#2563eb';
                        e.target.style.fontWeight = '600';
                      }}
                      onMouseOut={(e) => {
                        e.target.style.backgroundColor = 'white';
                        e.target.style.color = '#374151';
                        e.target.style.fontWeight = '500';
                      }}
                    >
                      <Settings size={18} />
                      <span>Service</span>
                    </Link>

                    <Link
                      to="/kafka-topics"
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.75rem',
                        padding: '1rem 1.25rem',
                        color: '#374151',
                        textDecoration: 'none',
                        fontSize: '0.9rem',
                        fontWeight: '500',
                        backgroundColor: 'white',
                        borderBottom: '1px solid #f3f4f6'
                      }}
                      onMouseOver={(e) => {
                        e.target.style.backgroundColor = '#f9fafb';
                        e.target.style.color = '#2563eb';
                        e.target.style.fontWeight = '600';
                      }}
                      onMouseOut={(e) => {
                        e.target.style.backgroundColor = 'white';
                        e.target.style.color = '#374151';
                        e.target.style.fontWeight = '500';
                      }}
                    >
                      <Radio size={18} />
                      <span>Kafka topic</span>
                    </Link>

                    <Link
                      to="/url-resources"
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.75rem',
                        padding: '1rem 1.25rem',
                        color: '#374151',
                        textDecoration: 'none',
                        fontSize: '0.9rem',
                        fontWeight: '500',
                        backgroundColor: 'white',
                        borderBottom: '1px solid #f3f4f6'
                      }}
                      onMouseOver={(e) => {
                        e.target.style.backgroundColor = '#f9fafb';
                        e.target.style.color = '#2563eb';
                        e.target.style.fontWeight = '600';
                      }}
                      onMouseOut={(e) => {
                        e.target.style.backgroundColor = 'white';
                        e.target.style.color = '#374151';
                        e.target.style.fontWeight = '500';
                      }}
                    >
                      <LinkIcon size={18} />
                      <span>URL resource</span>
                    </Link>

                    <Link
                      to="/s3-resources"
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.75rem',
                        padding: '1rem 1.25rem',
                        color: '#374151',
                        textDecoration: 'none',
                        fontSize: '0.9rem',
                        fontWeight: '500',
                        backgroundColor: 'white'
                      }}
                      onMouseOver={(e) => {
                        e.target.style.backgroundColor = '#f9fafb';
                        e.target.style.color = '#2563eb';
                        e.target.style.fontWeight = '600';
                      }}
                      onMouseOut={(e) => {
                        e.target.style.backgroundColor = 'white';
                        e.target.style.color = '#374151';
                        e.target.style.fontWeight = '500';
                      }}
                    >
                      <Database size={18} />
                      <span>S3 resource</span>
                    </Link>
                  </div>
                )}
              </div>
              )}

              {/* Dashboard (admin only) */}
              {isAdmin && (
                <Link
                  to="/dashboard"
                  onMouseEnter={handleOtherNavEnter}
                  style={{
                    color: '#6b7280',
                    textDecoration: 'none',
                    padding: '0.5rem 0.75rem',
                    borderRadius: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    fontSize: '0.95rem',
                    whiteSpace: 'nowrap',
                    fontWeight: '500',
                    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                    backgroundColor: 'transparent',
                    transition: 'all 0.2s ease'
                  }}
                  onMouseOver={(e) => {
                    e.target.style.color = '#374151';
                    e.target.style.fontWeight = '600';
                  }}
                  onMouseOut={(e) => {
                    e.target.style.color = '#6b7280';
                    e.target.style.fontWeight = '500';
                  }}
                >
                  <Home size={18} />
                  <span>Dashboard</span>
                </Link>
              )}

              {/* Access Requests (admin only) */}
              {isAdmin && (
                <Link
                  to="/access-requests"
                  onMouseEnter={handleOtherNavEnter}
                  style={{
                    color: '#6b7280',
                    textDecoration: 'none',
                    padding: '0.75rem 1rem',
                    borderRadius: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    fontSize: '0.95rem',
                    fontWeight: '500',
                    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                    backgroundColor: 'transparent',
                    transition: 'all 0.2s ease'
                  }}
                  onMouseOver={(e) => {
                    e.target.style.color = '#374151';
                    e.target.style.fontWeight = '600';
                  }}
                  onMouseOut={(e) => {
                    e.target.style.color = '#6b7280';
                    e.target.style.fontWeight = '500';
                  }}
                >
                  <ShieldAlert size={18} />
                  <span>Access Requests</span>
                </Link>
              )}
            </div>
          </nav>

          {/* Right: NSF Logo + Logout Button */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '1rem',
            flex: '0 0 auto'
          }}>
            {/* NSF Logo */}
            <img 
              src="https://nationaldataplatform.org/nsf-logo.png"
              alt="NSF Logo"
              style={{
                height: '35px',
                width: 'auto'
              }}
              onError={(e) => {
                e.target.style.display = 'none';
              }}
            />

            {/* Logout Button - Blue like the image */}
            <button
              onClick={handleLogout}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.5rem 1rem',
                backgroundColor: '#3b82f6', // Blue like in the image
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                fontSize: '0.9rem',
                fontWeight: '600',
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                transition: 'all 0.2s ease',
                fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
              }}
              onMouseOver={(e) => {
                e.target.style.backgroundColor = '#2563eb';
                e.target.style.transform = 'translateY(-1px)';
              }}
              onMouseOut={(e) => {
                e.target.style.backgroundColor = '#3b82f6';
                e.target.style.transform = 'translateY(0)';
              }}
            >
              <LogOut size={16} />
              <span>Logout</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Navigation;