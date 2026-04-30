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
  FolderOpen,
  ChevronDown,
  HardDrive,
  ShieldAlert
} from 'lucide-react';
import { isAccessRequestAdmin, userAPI } from '../services/api';

/**
 * Enhanced navigation component similar to nationaldataplatform.org
 * Gray background with improved dropdown logic that always closes properly
 */
const Navigation = () => {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);
  const buttonRef = useRef(null);
  const timeoutRef = useRef(null);
  const [isAdmin, setIsAdmin] = useState(false);

  // Determine admin status from the current token's /user/info response so
  // the "Access Requests" entry is only shown to users that can use it.
  useEffect(() => {
    let cancelled = false;
    userAPI
      .getUserInfo()
      .then((response) => {
        if (!cancelled) setIsAdmin(isAccessRequestAdmin(response.data));
      })
      .catch(() => {
        if (!cancelled) setIsAdmin(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Clear timeout on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        dropdownRef.current && 
        !dropdownRef.current.contains(event.target) &&
        buttonRef.current &&
        !buttonRef.current.contains(event.target)
      ) {
        setIsDropdownOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // Improved dropdown handlers with timeout for better UX
  const handleDropdownEnter = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    setIsDropdownOpen(true);
  };

  const handleDropdownLeave = () => {
    // Add small delay to prevent accidental closes
    timeoutRef.current = setTimeout(() => {
      setIsDropdownOpen(false);
    }, 150);
  };

  // Handle mouse entering other nav items - close dropdown immediately
  const handleOtherNavEnter = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    setIsDropdownOpen(false);
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
              
              {/* Dashboard */}
              <Link
                to="/"
                onMouseEnter={handleOtherNavEnter}
                style={{
                  color: '#6b7280', // Always same color
                  textDecoration: 'none',
                  padding: '0.5rem 0.75rem',
                  borderRadius: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  fontSize: '0.95rem',
                  whiteSpace: 'nowrap',
                  fontWeight: '500', // Always same weight
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

              {/* Organizations */}
              <Link
                to="/organizations"
                onMouseEnter={handleOtherNavEnter}
                style={{
                  color: '#6b7280', // Always same color
                  textDecoration: 'none',
                  padding: '0.5rem 0.75rem',
                  borderRadius: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  fontSize: '0.95rem',
                  whiteSpace: 'nowrap',
                  fontWeight: '500', // Always same weight
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
                <Building2 size={18} />
                <span>Organizations</span>
              </Link>

              {/* Resources Dropdown */}
              <div 
                style={{ position: 'relative' }}
                onMouseEnter={handleDropdownEnter}
                onMouseLeave={handleDropdownLeave}
              >
                <button
                  ref={buttonRef}
                  style={{
                    color: isDropdownOpen ? '#374151' : '#6b7280', // Only changes when dropdown is open
                    background: 'none',
                    border: 'none',
                    padding: '0.75rem 1rem',
                    borderRadius: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    fontSize: '0.95rem',
                    fontWeight: isDropdownOpen ? '600' : '500', // Only changes when dropdown is open
                    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                    cursor: 'pointer',
                    backgroundColor: 'transparent',
                    transition: 'all 0.2s ease'
                  }}
                  onMouseOver={(e) => {
                    if (!isDropdownOpen) {
                      e.target.style.color = '#374151';
                      e.target.style.fontWeight = '600';
                    }
                  }}
                  onMouseOut={(e) => {
                    if (!isDropdownOpen) {
                      e.target.style.color = '#6b7280';
                      e.target.style.fontWeight = '500';
                    }
                  }}
                >
                  <FolderOpen size={18} />
                  <span>Resources</span>
                  <ChevronDown size={16} />
                </button>

                {/* Dropdown */}
                {isDropdownOpen && (
                  <div
                    ref={dropdownRef}
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
                      to="/datasets"
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.75rem',
                        padding: '1rem 1.25rem',
                        color: '#374151', // Always same color
                        textDecoration: 'none',
                        fontSize: '0.9rem',
                        fontWeight: '500', // Always same weight
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
                      <span>Datasets</span>
                    </Link>

                    <Link
                      to="/kafka-topics"
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.75rem',
                        padding: '1rem 1.25rem',
                        color: '#374151', // Always same color
                        textDecoration: 'none',
                        fontSize: '0.9rem',
                        fontWeight: '500', // Always same weight
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
                      <span>Kafka Topics</span>
                    </Link>

                    <Link
                      to="/url-resources"
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.75rem',
                        padding: '1rem 1.25rem',
                        color: '#374151', // Always same color
                        textDecoration: 'none',
                        fontSize: '0.9rem',
                        fontWeight: '500', // Always same weight
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
                      <span>URL Resources</span>
                    </Link>

                    <Link
                      to="/s3-resources"
                      style={{
                        display: 'flex',
                        alignItems:'center',
                        gap: '0.75rem',
                        padding: '1rem 1.25rem',
                        color: '#374151', // Always same color
                        textDecoration: 'none',
                        fontSize: '0.9rem',
                        fontWeight: '500', // Always same weight
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
                      <Database size={18} />
                      <span>S3 Resources</span>
                    </Link>

                    <Link
                      to="/s3-management"
                      style={{
                        display: 'flex',
                        alignItems:'center',
                        gap: '0.75rem',
                        padding: '1rem 1.25rem',
                        color: '#374151', // Always same color
                        textDecoration: 'none',
                        fontSize: '0.9rem',
                        fontWeight: '500', // Always same weight
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
                      <HardDrive size={18} />
                      <span>S3 Management</span>
                    </Link>
                  </div>
                )}
              </div>

              {/* Services */}
              <Link
                to="/services"
                onMouseEnter={handleOtherNavEnter}
                style={{
                  color: '#6b7280', // Always same color
                  textDecoration: 'none',
                  padding: '0.5rem 0.75rem',
                  borderRadius: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  fontSize: '0.95rem',
                  whiteSpace: 'nowrap',
                  fontWeight: '500', // Always same weight
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
                <Settings size={18} />
                <span>Services</span>
              </Link>

              {/* Search */}
              <Link
                to="/search"
                onMouseEnter={handleOtherNavEnter}
                style={{
                  color: '#6b7280', // Always same color
                  textDecoration: 'none',
                  padding: '0.5rem 0.75rem',
                  borderRadius: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  fontSize: '0.95rem',
                  whiteSpace: 'nowrap',
                  fontWeight: '500', // Always same weight
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