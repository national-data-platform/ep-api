import React, { useState, useEffect, useCallback } from 'react';
import {
  Settings,
  Plus,
  AlertCircle,
  Save,
  X,
  Trash2,
  ExternalLink,
  FileText,
  Server,
  Edit3
} from 'lucide-react';
import { servicesAPI, searchAPI, resourcesAPI } from '../services/api';

/**
 * Services page component for managing registered services
 * Allows creating, listing, editing, and deleting services in CKAN
 * Enhanced to match the structure and functionality of other resource pages
 */
const Services = () => {
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingService, setEditingService] = useState(null);

  const [selectedServer] = useState('local'); // Fixed to local for consistency

  // Form state for creating/editing service
  const [formData, setFormData] = useState({
    service_name: '',
    service_title: '',
    owner_org: 'services', // Always 'services' as per API requirement
    service_url: '',
    service_type: '',
    notes: '',
    extras: {},
    health_check_url: '',
    documentation_url: ''
  });

  // JSON editor state for extras
  const [extrasJson, setExtrasJson] = useState('{}');

  // Available service types
  const serviceTypes = [
    'API',
    'Web Service',
    'Microservice',
    'Database',
    'Authentication Service',
    'Storage Service',
    'Analytics Service',
    'Monitoring Service',
    'Other'
  ];

  /**
   * Fetch all services (filtered from all datasets)
   */
  const fetchServices = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Use search to get all datasets, then filter for services
      const response = await searchAPI.searchByTerms([''], null, selectedServer);
      
      // Filter to show only services (owner_org === 'services')
      const filteredServices = (response.data || []).filter(dataset => {
        return dataset.owner_org === 'services';
      });
      
      console.log('All datasets:', response.data); // Debug
      console.log('Filtered services:', filteredServices); // Debug
      
      setServices(filteredServices);
      
    } catch (err) {
      console.error('Error fetching services:', err);
      setError('Failed to load services: ' + 
        (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  }, [selectedServer]);

  /**
   * Fetch services on component mount
   */
  useEffect(() => {
    fetchServices();
  }, [fetchServices]);

  /**
   * Handle form input changes
   */
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  /**
   * Parse JSON string safely
   */
  const parseJsonSafely = (jsonString, fallback = {}) => {
    try {
      return jsonString.trim() === '' ? fallback : JSON.parse(jsonString);
    } catch {
      return fallback;
    }
  };

  /**
   * Reset form to initial state
   */
  const resetForm = () => {
    setFormData({
      service_name: '',
      service_title: '',
      owner_org: 'services',
      service_url: '',
      service_type: '',
      notes: '',
      extras: {},
      health_check_url: '',
      documentation_url: ''
    });
    setExtrasJson('{}');
    setEditingService(null);
    setShowCreateForm(false);
  };

  /**
   * Prepare form data for submission
   */
  const prepareFormData = () => {
    // Parse JSON fields
    const extras = parseJsonSafely(extrasJson, {});

    // Prepare data
    const requestData = {
      ...formData,
      extras: Object.keys(extras).length > 0 ? extras : undefined
    };

    // Remove empty fields
    Object.keys(requestData).forEach(key => {
      if (requestData[key] === '' || requestData[key] === undefined) {
        delete requestData[key];
      }
    });

    return requestData;
  };

  /**
   * Handle form submission for creating service
   */
  const handleCreate = async (e) => {
    e.preventDefault();

    try {
      setError(null);
      setSuccess(null);
      setLoading(true);

      const requestData = prepareFormData();
      await servicesAPI.create(requestData, selectedServer);

      setSuccess('Service registered successfully!');
      resetForm();
      fetchServices();

    } catch (err) {
      console.error('Error creating service:', err);
      setError('Failed to register service: ' +
        (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  /**
   * Handle form submission for updating service
   */
  const handleUpdate = async (e) => {
    e.preventDefault();

    try {
      setError(null);
      setSuccess(null);
      setLoading(true);

      if (!editingService || !editingService.id) {
        throw new Error('Invalid service ID for update operation');
      }

      const requestData = prepareFormData();

      // Ensure all critical fields are present for update
      const updateData = {
        service_name: formData.service_name || editingService.name,
        service_title: formData.service_title || editingService.title,
        owner_org: formData.owner_org || editingService.owner_org,
        service_url: formData.service_url || (editingService.resources?.[0]?.url),
        ...(formData.service_type && { service_type: formData.service_type }),
        ...(formData.notes && { notes: formData.notes }),
        ...(formData.health_check_url && { health_check_url: formData.health_check_url }),
        ...(formData.documentation_url && { documentation_url: formData.documentation_url }),
        ...(requestData.extras && { extras: requestData.extras })
      };

      await servicesAPI.update(editingService.id, updateData, selectedServer);

      setSuccess('Service updated successfully!');
      resetForm();
      fetchServices();

    } catch (err) {
      console.error('Error updating service:', err);
      setError('Failed to update service: ' +
        (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  /**
   * Start editing a service
   */
  const startEditing = (service) => {
    setEditingService(service);
    const extras = service.extras || {};
    const firstResource = service.resources && service.resources[0];

    // Extract service-specific fields from extras
    const serviceType = extras.service_type || '';
    const healthCheckUrl = extras.health_check_url || '';
    const documentationUrl = extras.documentation_url || '';

    // Create clean extras without service-specific fields
    const cleanExtras = { ...extras };
    delete cleanExtras.service_type;
    delete cleanExtras.health_check_url;
    delete cleanExtras.documentation_url;

    const editFormData = {
      service_name: service.name || '',
      service_title: service.title || '',
      owner_org: service.owner_org || 'services',
      service_url: firstResource?.url || '',
      service_type: serviceType,
      notes: service.notes || '',
      extras: cleanExtras,
      health_check_url: healthCheckUrl,
      documentation_url: documentationUrl
    };

    setFormData(editFormData);

    // Set JSON field with proper formatting
    try {
      setExtrasJson(JSON.stringify(cleanExtras, null, 2));
    } catch (jsonError) {
      console.error('Error stringifying JSON for edit form:', jsonError);
      setExtrasJson('{}');
    }

    setShowCreateForm(true);
  };

  /**
   * Handle service deletion
   */
  const handleDeleteService = async (service) => {
    const displayName = service.title || service.name || 'Unnamed Service';
    
    if (!window.confirm(
      `Are you sure you want to delete service "${displayName}"? This will also delete all associated resources. This action cannot be undone.`
    )) {
      return;
    }

    try {
      setError(null);
      setSuccess(null);
      
      // Debug: Log the service being deleted
      console.log('Attempting to delete service with ID:', service.id);
      console.log('Using endpoint: DELETE /resource?resource_id=' + service.id + '&server=local');
      
      // Use the resource deletion endpoint since datasets are resources in CKAN
      await resourcesAPI.deleteById(service.id, 'local');
      
      setSuccess(`Service "${displayName}" deleted successfully!`);
      
      // Refresh the services list
      fetchServices();
      
    } catch (err) {
      console.error('Error deleting service:', err);
      console.error('Full error object:', err);
      console.error('Error response:', err.response);
      
      let errorMessage = 'Failed to delete service: ';
      
      if (err.response?.status === 404) {
        errorMessage += `Service "${displayName}" not found. It may have been already deleted.`;
      } else if (err.response?.status === 405) {
        errorMessage += 'Service deletion method not allowed.';
      } else if (err.response?.status === 401) {
        errorMessage += 'Authentication required. Please login again.';
      } else if (err.response?.status === 403) {
        errorMessage += 'You do not have permission to delete this service.';
      } else {
        errorMessage += (err.response?.data?.detail || err.message);
      }
      
      setError(errorMessage);
    }
  };

  /**
   * Get service type badge color
   */
  const getServiceTypeBadge = (service) => {
    const extras = service.extras || {};
    const serviceType = extras.service_type || 'Unknown';
    
    const typeColors = {
      'API': 'status-info',
      'Web Service': 'status-success',
      'Microservice': 'status-warning',
      'Database': 'status-error',
      'Authentication Service': 'status-info',
      'Storage Service': 'status-success',
      'Analytics Service': 'status-warning',
      'Monitoring Service': 'status-error',
      'Other': 'status-info'
    };
    
    return {
      type: serviceType,
      color: typeColors[serviceType] || 'status-info'
    };
  };

  /**
   * Get the main service URL from resources
   */
  const getMainServiceUrl = (service) => {
    const firstResource = service.resources && service.resources[0];
    return firstResource?.url || 'No URL';
  };

  /**
   * Get documentation URL from service extras
   */
  const getDocumentationUrl = (service) => {
    const extras = service.extras || {};
    return extras.documentation_url || null;
  };

  /**
   * Get health check status (placeholder for future implementation)
   */
  const getHealthStatus = (service) => {
    const extras = service.extras || {};
    if (extras.health_check_url) {
      return { status: 'Unknown', color: 'status-warning' };
    }
    return { status: 'No Health Check', color: 'status-info' };
  };

  return (
    <div className="services-page">
      {/* Page Header */}
      <div className="page-header">
        <h1 className="page-title">
          <Settings size={32} style={{ marginRight: '0.5rem' }} />
          Services Registry
        </h1>
        <p className="page-subtitle">
          Register and manage services in your system
        </p>
      </div>

      {/* Alert Messages */}
      {error && (
        <div className="alert alert-error">
          <AlertCircle size={20} />
          {error}
        </div>
      )}

      {success && (
        <div className="alert alert-success">
          {success}
        </div>
      )}

      {/* Register service button */}
      {!showCreateForm && (
        <div style={{ marginBottom: '1rem' }}>
          <button
            onClick={() => setShowCreateForm(true)}
            className="btn btn-primary"
          >
            <Plus size={16} />
            Register Service
          </button>
        </div>
      )}

      {/* Create/Edit Service Form */}
      {showCreateForm && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">
              {editingService ? (
                <>
                  <Edit3 size={20} />
                  Edit Service
                </>
              ) : (
                <>
                  <Plus size={20} />
                  Register New Service
                </>
              )}
            </h3>
            <button
              onClick={resetForm}
              className="btn btn-secondary"
            >
              <X size={16} />
              Cancel
            </button>
          </div>

          <form onSubmit={editingService ? handleUpdate : handleCreate}>
            {/* Basic Information */}
            <div className="grid grid-2">
              <div className="form-group">
                <label className="form-label">Service Name *</label>
                <input
                  type="text"
                  name="service_name"
                  value={formData.service_name}
                  onChange={handleInputChange}
                  className="form-input"
                  placeholder="user_auth_api"
                  required
                />
                <small style={{ color: '#64748b' }}>
                  Unique identifier for the service
                </small>
              </div>

              <div className="form-group">
                <label className="form-label">Service Title *</label>
                <input
                  type="text"
                  name="service_title"
                  value={formData.service_title}
                  onChange={handleInputChange}
                  className="form-input"
                  placeholder="User Authentication API"
                  required
                />
              </div>
            </div>

            {/* Service URL and Type */}
            <div className="grid grid-2">
              <div className="form-group">
                <label className="form-label">Service URL *</label>
                <input
                  type="url"
                  name="service_url"
                  value={formData.service_url}
                  onChange={handleInputChange}
                  className="form-input"
                  placeholder="https://api.example.com/auth"
                  required
                />
                <small style={{ color: '#64748b' }}>
                  Main endpoint URL for the service
                </small>
              </div>

              <div className="form-group">
                <label className="form-label">Service Type</label>
                <select
                  name="service_type"
                  value={formData.service_type}
                  onChange={handleInputChange}
                  className="form-select"
                >
                  <option value="">Select service type</option>
                  {serviceTypes.map(type => (
                    <option key={type} value={type}>{type}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Additional URLs */}
            <div className="grid grid-2">
              <div className="form-group">
                <label className="form-label">Health Check URL</label>
                <input
                  type="url"
                  name="health_check_url"
                  value={formData.health_check_url}
                  onChange={handleInputChange}
                  className="form-input"
                  placeholder="https://api.example.com/auth/health"
                />
                <small style={{ color: '#64748b' }}>
                  URL for service health monitoring
                </small>
              </div>

              <div className="form-group">
                <label className="form-label">Documentation URL</label>
                <input
                  type="url"
                  name="documentation_url"
                  value={formData.documentation_url}
                  onChange={handleInputChange}
                  className="form-input"
                  placeholder="https://docs.example.com/auth-api"
                />
                <small style={{ color: '#64748b' }}>
                  URL to service documentation
                </small>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Description</label>
              <textarea
                name="notes"
                value={formData.notes}
                onChange={handleInputChange}
                className="form-input form-textarea"
                placeholder="Description of the service..."
              />
            </div>

            {/* Extras Configuration */}
            <div className="form-group">
              <label className="form-label">Additional Metadata (JSON)</label>
              <textarea
                value={extrasJson}
                onChange={(e) => setExtrasJson(e.target.value)}
                className="form-input form-textarea"
                placeholder='{"version": "2.1.0", "environment": "production"}'
                style={{ fontFamily: 'monospace', fontSize: '0.875rem' }}
              />
              <small style={{ color: '#64748b' }}>
                Additional metadata as JSON (version, environment, etc.)
              </small>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
            >
              {loading ? (
                <>
                  <div className="loading-spinner" />
                  {editingService ? 'Updating...' : 'Registering...'}
                </>
              ) : (
                <>
                  <Save size={16} />
                  {editingService ? 'Update Service' : 'Register Service'}
                </>
              )}
            </button>
          </form>
        </div>
      )}

      {/* Services List */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            Registered Services ({services.length})
          </h3>
        </div>

        {loading && !showCreateForm ? (
          <div style={{ textAlign: 'center', padding: '2rem' }}>
            <div className="loading-spinner" style={{ margin: '0 auto' }}></div>
            <p style={{ marginTop: '1rem' }}>Loading services...</p>
          </div>
        ) : services.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: '#64748b' }}>
            <Server size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
            <p>No services registered</p>
            <p>Register your first service using the form above</p>
          </div>
        ) : (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Service</th>
                  <th>Type</th>
                  <th>URL</th>
                  <th>Documentation</th>
                  <th>Health Status</th>
                  <th>Resources</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {services.map((service, index) => {
                  const serviceTypeBadge = getServiceTypeBadge(service);
                  const serviceUrl = getMainServiceUrl(service);
                  const documentationUrl = getDocumentationUrl(service);
                  const healthStatus = getHealthStatus(service);

                  return (
                    <tr key={`${service.id}-${index}`}>
                      <td>
                        <div>
                          <div style={{ fontWeight: '500', marginBottom: '0.25rem' }}>
                            {service.title || service.name}
                          </div>
                          {service.title && service.name && service.title !== service.name && (
                            <div style={{ fontSize: '0.875rem', color: '#64748b' }}>
                              {service.name}
                            </div>
                          )}
                          {service.notes && (
                            <div style={{ 
                              fontSize: '0.875rem', 
                              color: '#64748b',
                              marginTop: '0.25rem',
                              maxWidth: '200px',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap'
                            }}>
                              {service.notes}
                            </div>
                          )}
                          <div style={{ 
                            fontSize: '0.75rem', 
                            color: '#94a3b8',
                            marginTop: '0.25rem',
                            fontFamily: 'monospace'
                          }}>
                            ID: {service.id}
                          </div>
                        </div>
                      </td>
                      <td>
                        <span className={`status-indicator ${serviceTypeBadge.color}`}>
                          {serviceTypeBadge.type}
                        </span>
                      </td>
                      <td>
                        {serviceUrl !== 'No URL' ? (
                          <a
                            href={serviceUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{
                              color: '#2563eb',
                              textDecoration: 'none',
                              fontSize: '0.875rem',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '0.25rem',
                              maxWidth: '200px',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap'
                            }}
                            title={serviceUrl}
                          >
                            <ExternalLink size={12} />
                            Access Service
                          </a>
                        ) : (
                          <span style={{ color: '#94a3b8', fontSize: '0.875rem' }}>
                            No URL
                          </span>
                        )}
                      </td>
                      <td>
                        {documentationUrl ? (
                          <a
                            href={documentationUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{
                              color: '#2563eb',
                              textDecoration: 'none',
                              fontSize: '0.875rem',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '0.25rem',
                              maxWidth: '200px',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap'
                            }}
                            title={documentationUrl}
                          >
                            <FileText size={12} />
                            View Docs
                          </a>
                        ) : (
                          <span style={{ color: '#94a3b8', fontSize: '0.875rem' }}>
                            No Docs
                          </span>
                        )}
                      </td>
                      <td>
                        <span className={`status-indicator ${healthStatus.color}`}>
                          {healthStatus.status}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                          <FileText size={14} />
                          <span>{service.resources?.length || 0}</span>
                        </div>
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                          <button
                            onClick={() => startEditing(service)}
                            className="btn btn-secondary"
                            style={{ padding: '0.375rem 0.75rem' }}
                            title="Edit service"
                          >
                            <Edit3 size={14} />
                            <span style={{ fontSize: '0.75rem' }}>Edit</span>
                          </button>
                          <button
                            onClick={() => handleDeleteService(service)}
                            className="btn btn-danger"
                            style={{ padding: '0.375rem 0.75rem' }}
                            title="Delete service"
                          >
                            <Trash2 size={14} />
                            <span style={{ fontSize: '0.75rem' }}>Delete</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>


    </div>
  );
};

export default Services;