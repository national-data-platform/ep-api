import React, { useState, useEffect } from 'react';
import {
  Activity,
  Database,
  Server,
  AlertCircle,
  CheckCircle,
  Info,
  User,
  Monitor,
  HardDrive,
  Cpu,
  Wifi,
  ExternalLink,
  Users,
  Shield,
  BookOpen,
  MinusCircle
} from 'lucide-react';
import { statusAPI, userAPI, getApiBaseUrl } from '../services/api';

/**
 * Redesigned Dashboard component with user info and improved metrics display
 * Shows system overview, user information, and key system metrics
 */
const Dashboard = () => {
  const [systemStatus, setSystemStatus] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [kafkaDetails, setKafkaDetails] = useState(null);
  const [userInfo, setUserInfo] = useState(null);
  const [apiVersion, setApiVersion] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  /**
   * Fetch dashboard data on component mount
   */
  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        
        // Fetch all dashboard data in parallel
        const [statusResponse, metricsResponse, kafkaResponse, userResponse] = 
          await Promise.allSettled([
            statusAPI.getStatus(),
            statusAPI.getMetrics(),
            statusAPI.getKafkaDetails(),
            userAPI.getUserInfo()
          ]);

        // Handle status response and extract API version
        if (statusResponse.status === 'fulfilled') {
          const statusData = statusResponse.value.data;
          setSystemStatus(statusData);
          
          // Extract API version from status response
          const version = statusData?.version || statusData?.api_version || 'Unknown';
          setApiVersion(version);
        }

        // Handle metrics response
        if (metricsResponse.status === 'fulfilled') {
          setMetrics(metricsResponse.value.data);
        }

        // Handle Kafka details response
        if (kafkaResponse.status === 'fulfilled') {
          setKafkaDetails(kafkaResponse.value.data);
        }

        // Handle user info response
        if (userResponse.status === 'fulfilled') {
          setUserInfo(userResponse.value.data);
        } else {
          console.error('Failed to fetch user info:', userResponse.reason);
        }

        setError(null);
      } catch (err) {
        console.error('Error fetching dashboard data:', err);
        setError('Failed to load dashboard data');
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  /**
   * Format percentage values for display
   */
  const formatPercentage = (value) => {
    if (!value) return 'N/A';
    // Remove % symbol if present and ensure it's a number
    const numValue = parseFloat(value.toString().replace('%', ''));
    return isNaN(numValue) ? 'N/A' : `${numValue}%`;
  };

  /**
   * Get status color based on percentage value
   */
  const getStatusColor = (value, type = 'general') => {
    if (!value || value === 'N/A') return '#94a3b8';
    
    const numValue = parseFloat(value.toString().replace('%', ''));
    if (isNaN(numValue)) return '#94a3b8';
    
    if (type === 'memory' || type === 'cpu' || type === 'disk') {
      if (numValue < 50) return '#059669'; // Green
      if (numValue < 80) return '#ca8a04'; // Yellow
      return '#dc2626'; // Red
    }
    
    return '#2563eb'; // Default blue
  };

  /**
   * Get API documentation URL
   */
  const getApiDocsUrl = () => {
    return `${getApiBaseUrl()}/docs`;
  };

  /**
   * Get user display name
   */
  const getUserDisplayName = () => {
    if (!userInfo) return 'Unknown User';
    return userInfo.username || userInfo.sub || 'Anonymous';
  };

  /**
   * Get user roles display
   * Handles both string arrays and object arrays (with id, name, path properties)
   */
  const getUserRoles = () => {
    if (!userInfo || !userInfo.roles) return [];
    return userInfo.roles.map(role => {
      if (typeof role === 'string') return role;
      if (typeof role === 'object' && role !== null) {
        return role.name || role.id || JSON.stringify(role);
      }
      return String(role);
    });
  };

  /**
   * Get user groups display
   * Handles both string arrays and object arrays (with id, name, path properties)
   */
  const getUserGroups = () => {
    if (!userInfo || !userInfo.groups) return [];
    return userInfo.groups.map(group => {
      if (typeof group === 'string') return group;
      if (typeof group === 'object' && group !== null) {
        return group.name || group.id || JSON.stringify(group);
      }
      return String(group);
    });
  };

  /**
   * Render loading state
   */
  if (loading) {
    return (
      <div className="dashboard">
        <div className="page-header">
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">System overview and status</p>
        </div>
        
        <div className="card">
          <div style={{ textAlign: 'center', padding: '2rem' }}>
            <div className="loading-spinner" style={{ margin: '0 auto' }}></div>
            <p style={{ marginTop: '1rem' }}>Loading dashboard data...</p>
          </div>
        </div>
      </div>
    );
  }

  /**
   * Render error state
   */
  if (error) {
    return (
      <div className="dashboard">
        <div className="page-header">
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">System overview and status</p>
        </div>
        
        <div className="alert alert-error">
          <AlertCircle size={20} />
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard">
      {/* Page Header with API Version and Documentation Link */}
      <div className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
          <div>
            <h1 className="page-title">Dashboard</h1>
            <p className="page-subtitle">
              System overview and status - Last updated: {new Date().toLocaleTimeString()}
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            {/* API Documentation Link */}
            <a 
              href={getApiDocsUrl()}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                fontSize: '0.875rem',
                color: '#2563eb',
                textDecoration: 'none',
                padding: '0.5rem 0.75rem',
                backgroundColor: '#dbeafe',
                borderRadius: '6px',
                border: '1px solid #bfdbfe',
                transition: 'all 0.2s ease'
              }}
              onMouseOver={(e) => {
                e.target.style.backgroundColor = '#bfdbfe';
                e.target.style.color = '#1d4ed8';
              }}
              onMouseOut={(e) => {
                e.target.style.backgroundColor = '#dbeafe';
                e.target.style.color = '#2563eb';
              }}
            >
              <ExternalLink size={14} />
              API Docs
            </a>
            
            {/* API Version */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              fontSize: '0.875rem',
              color: '#64748b',
              backgroundColor: '#f8fafc',
              padding: '0.5rem 0.75rem',
              borderRadius: '6px',
              border: '1px solid #e2e8f0'
            }}>
              <Info size={14} />
              <span>API:</span>
              <span style={{
                fontFamily: 'monospace',
                fontWeight: '600',
                color: '#374151'
              }}>
                {apiVersion || 'Unknown'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* User Information Card */}
      {userInfo && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <User size={20} />
              Current User
            </h3>
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1.5rem' }}>
            {/* User Info */}
            <div>
              <h4 style={{ color: '#374151', marginBottom: '0.75rem', fontSize: '1rem', fontWeight: '600' }}>
                User Information
              </h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <User size={16} style={{ color: '#64748b' }} />
                  <span style={{ fontWeight: '500' }}>Username:</span>
                  <span style={{ color: '#64748b' }}>{getUserDisplayName()}</span>
                </div>
                {userInfo.sub && userInfo.sub !== getUserDisplayName() && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Info size={16} style={{ color: '#64748b' }} />
                    <span style={{ fontWeight: '500' }}>ID:</span>
                    <span style={{ color: '#64748b', fontFamily: 'monospace', fontSize: '0.875rem' }}>
                      {userInfo.sub}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Roles */}
            <div>
              <h4 style={{ color: '#374151', marginBottom: '0.75rem', fontSize: '1rem', fontWeight: '600' }}>
                Roles ({getUserRoles().length})
              </h4>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                {getUserRoles().length > 0 ? (
                  getUserRoles().map((role, index) => (
                    <span 
                      key={index}
                      className="status-indicator status-info"
                      style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}
                    >
                      <Shield size={12} />
                      {role}
                    </span>
                  ))
                ) : (
                  <span style={{ color: '#64748b', fontSize: '0.875rem' }}>No roles assigned</span>
                )}
              </div>
            </div>

            {/* Groups */}
            <div>
              <h4 style={{ color: '#374151', marginBottom: '0.75rem', fontSize: '1rem', fontWeight: '600' }}>
                Groups ({getUserGroups().length})
              </h4>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                {getUserGroups().length > 0 ? (
                  getUserGroups().map((group, index) => (
                    <span 
                      key={index}
                      className="status-indicator status-success"
                      style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}
                    >
                      <Users size={12} />
                      {group}
                    </span>
                  ))
                ) : (
                  <span style={{ color: '#64748b', fontSize: '0.875rem' }}>No groups assigned</span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* System Metrics Cards */}
      {metrics && (
        <div className="grid grid-2" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
          {/* Public IP Card */}
          <div className="card">
            <div className="card-header" style={{ marginBottom: '0.5rem' }}>
              <h3 className="card-title" style={{ fontSize: '1rem' }}>Public IP</h3>
              <Wifi size={20} style={{ color: '#2563eb' }} />
            </div>
            <div style={{ 
              fontSize: '1.5rem', 
              fontWeight: '600', 
              color: '#1e293b',
              fontFamily: 'monospace'
            }}>
              {metrics.public_ip || 'Unknown'}
            </div>
            <p style={{ marginTop: '0.5rem', color: '#64748b', fontSize: '0.875rem' }}>
              External IP address
            </p>
          </div>

          {/* CPU Usage Card */}
          <div className="card">
            <div className="card-header" style={{ marginBottom: '0.5rem' }}>
              <h3 className="card-title" style={{ fontSize: '1rem' }}>CPU Usage</h3>
              <Cpu size={20} style={{ color: getStatusColor(metrics.cpu, 'cpu') }} />
            </div>
            <div style={{ 
              fontSize: '1.5rem', 
              fontWeight: '600', 
              color: getStatusColor(metrics.cpu, 'cpu'),
              fontFamily: 'monospace'
            }}>
              {formatPercentage(metrics.cpu)}
            </div>
            <p style={{ marginTop: '0.5rem', color: '#64748b', fontSize: '0.875rem' }}>
              Current processor load
            </p>
          </div>

          {/* Memory Usage Card */}
          <div className="card">
            <div className="card-header" style={{ marginBottom: '0.5rem' }}>
              <h3 className="card-title" style={{ fontSize: '1rem' }}>Memory Usage</h3>
              <Monitor size={20} style={{ color: getStatusColor(metrics.memory, 'memory') }} />
            </div>
            <div style={{ 
              fontSize: '1.5rem', 
              fontWeight: '600', 
              color: getStatusColor(metrics.memory, 'memory'),
              fontFamily: 'monospace'
            }}>
              {formatPercentage(metrics.memory)}
            </div>
            <p style={{ marginTop: '0.5rem', color: '#64748b', fontSize: '0.875rem' }}>
              RAM utilization
            </p>
          </div>

          {/* Disk Usage Card */}
          <div className="card">
            <div className="card-header" style={{ marginBottom: '0.5rem' }}>
              <h3 className="card-title" style={{ fontSize: '1rem' }}>Disk Usage</h3>
              <HardDrive size={20} style={{ color: getStatusColor(metrics.disk, 'disk') }} />
            </div>
            <div style={{ 
              fontSize: '1.5rem', 
              fontWeight: '600', 
              color: getStatusColor(metrics.disk, 'disk'),
              fontFamily: 'monospace'
            }}>
              {formatPercentage(metrics.disk)}
            </div>
            <p style={{ marginTop: '0.5rem', color: '#64748b', fontSize: '0.875rem' }}>
              Storage space used
            </p>
          </div>
        </div>
      )}

      {/* Service Status Cards */}
      <div className="grid grid-2">
        {/* Compact Catalog Status Card */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <Database size={24} style={{ color: '#059669' }} />
              <div>
                <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: '600', color: '#1e293b' }}>
                  Catalog Status
                </h3>
                <p style={{ margin: 0, fontSize: '0.875rem', color: '#64748b' }}>
                  CKAN Data Catalog
                </p>
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              {systemStatus ? (
                <div className="status-indicator status-success">
                  <CheckCircle size={16} />
                  Connected
                </div>
              ) : (
                <div className="status-indicator status-warning">
                  <Server size={16} />
                  Checking...
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Streaming Status Card */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <Activity size={24} style={{ color: '#2563eb' }} />
              <div>
                <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: '600', color: '#1e293b' }}>
                  Streaming Status
                </h3>
                <p style={{ margin: 0, fontSize: '0.875rem', color: '#64748b' }}>
                  Kafka Message Broker
                </p>
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              {kafkaDetails ? (
                kafkaDetails.kafka_connection ? (
                  <div>
                    <div className="status-indicator status-success" style={{ marginBottom: '0.25rem' }}>
                      <CheckCircle size={16} />
                      Connected
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                      {kafkaDetails.kafka_host}:{kafkaDetails.kafka_port}
                    </div>
                  </div>
                ) : (
                  <div className="status-indicator status-warning">
                    <MinusCircle size={16} />
                    Disabled
                  </div>
                )
              ) : (
                <div className="status-indicator status-warning">
                  <Server size={16} />
                  Checking...
                </div>
              )}
            </div>
          </div>
        </div>

        {/* JupyterLab Status Card */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <BookOpen size={24} style={{ color: '#f97316' }} />
              <div>
                <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: '600', color: '#1e293b' }}>
                  JupyterLab Status
                </h3>
                <p style={{ margin: 0, fontSize: '0.875rem', color: '#64748b' }}>
                  Interactive Computing
                </p>
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              {systemStatus?.jupyterlab_enabled ? (
                <div>
                  <div className="status-indicator status-success" style={{ marginBottom: '0.25rem' }}>
                    <CheckCircle size={16} />
                    Enabled
                  </div>
                  {systemStatus?.jupyterlab_url && (
                    <a
                      href={systemStatus.jupyterlab_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'flex-end',
                        gap: '0.25rem',
                        fontSize: '0.75rem',
                        color: '#2563eb',
                        textDecoration: 'none',
                        marginTop: '0.25rem'
                      }}
                    >
                      <ExternalLink size={10} />
                      Open
                    </a>
                  )}
                </div>
              ) : (
                <div className="status-indicator status-error">
                  <AlertCircle size={16} />
                  Disabled
                </div>
              )}
            </div>
          </div>
        </div>
      </div>


    </div>
  );
};

export default Dashboard;