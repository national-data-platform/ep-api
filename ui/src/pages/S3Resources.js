import React, { useState, useEffect, useCallback } from 'react';
import { 
  Database, 
  Plus, 
  AlertCircle, 
  Edit3,
  Save,
  X,
  Trash2,
  RefreshCw,
  ExternalLink,
  FileText,
  Cloud
} from 'lucide-react';
import { s3API, organizationsAPI, searchAPI, resourcesAPI } from '../services/api';

/**
 * S3 Resources page component for managing S3 bucket resources
 * Allows creating, listing, editing, and deleting S3 resources in CKAN
 */
const S3Resources = () => {
  const [s3Resources, setS3Resources] = useState([]);
  const [organizations, setOrganizations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingResource, setEditingResource] = useState(null);
  const [selectedServer] = useState('local'); // Fixed to local for consistency

  // Form state for creating/editing S3 resource
  const [formData, setFormData] = useState({
    resource_name: '',
    resource_title: '',
    owner_org: '',
    resource_s3: '',
    notes: '',
    extras: {}
  });

  // JSON editor state for extras
  const [extrasJson, setExtrasJson] = useState('{}');

  /**
   * Fetch organizations for dropdown
   */
  const fetchOrganizations = useCallback(async () => {
    try {
      const response = await organizationsAPI.list({ server: selectedServer });
      setOrganizations(response.data || []);
    } catch (err) {
      console.error('Error fetching organizations:', err);
    }
  }, [selectedServer]);

  /**
   * Fetch all S3 resources (filtered from all datasets)
   */
  const fetchS3Resources = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Use search to get all datasets, then filter for S3 resources
      const response = await searchAPI.searchByTerms([''], null, selectedServer);
      
      // Filter to show only S3 resources
      const filteredResources = (response.data || []).filter(dataset => {
        const resources = dataset.resources || [];
        
        // Include if it has S3 resources
        return resources.some(resource => 
          resource.url && (
            resource.url.startsWith('s3://') ||
            resource.url.includes('s3.amazonaws.com') ||
            resource.url.includes('.s3.')
          )
        ) && 
        // Exclude Kafka topics (no Kafka extras)
        !(dataset.extras && (
          dataset.extras.kafka_topic || dataset.extras.kafka_host || 
          dataset.extras.topic || dataset.extras.host
        )) &&
        // Exclude services organization
        dataset.owner_org !== 'services';
      });
      
      console.log('All datasets:', response.data); // Debug
      console.log('Filtered S3 resources:', filteredResources); // Debug
      
      setS3Resources(filteredResources);
      
    } catch (err) {
      console.error('Error fetching S3 resources:', err);
      setError('Failed to load S3 resources: ' + 
        (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  }, [selectedServer]);

  /**
   * Fetch organizations and S3 resources on component mount
   */
  useEffect(() => {
    fetchOrganizations();
    fetchS3Resources();
  }, [fetchOrganizations, fetchS3Resources]);

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
      resource_name: '',
      resource_title: '',
      owner_org: '',
      resource_s3: '',
      notes: '',
      extras: {}
    });
    setExtrasJson('{}');
    setEditingResource(null);
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
   * Handle form submission for creating S3 resource
   */
  const handleCreate = async (e) => {
    e.preventDefault();
    
    try {
      setError(null);
      setSuccess(null);
      setLoading(true);

      const requestData = prepareFormData();
      await s3API.create(requestData, selectedServer);
      
      setSuccess('S3 resource created successfully!');
      resetForm();
      fetchS3Resources();
      
    } catch (err) {
      console.error('Error creating S3 resource:', err);
      setError('Failed to create S3 resource: ' + 
        (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  /**
   * Handle form submission for updating S3 resource
   */
  const handleUpdate = async (e) => {
    e.preventDefault();
    
    try {
      setError(null);
      setSuccess(null);
      setLoading(true);

      const requestData = prepareFormData();
      await s3API.update(editingResource.id, requestData, selectedServer);
      
      setSuccess('S3 resource updated successfully!');
      resetForm();
      fetchS3Resources();
      
    } catch (err) {
      console.error('Error updating S3 resource:', err);
      setError('Failed to update S3 resource: ' + 
        (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  /**
   * Start editing an S3 resource
   */
  const startEditing = (resource) => {
    setEditingResource(resource);
    const extras = resource.extras || {};
    const firstResource = resource.resources && resource.resources[0];
    
    setFormData({
      resource_name: resource.name || '',
      resource_title: resource.title || '',
      owner_org: resource.owner_org || '',
      resource_s3: firstResource?.url || '',
      notes: resource.notes || '',
      extras: extras
    });
    
    // Set JSON fields
    setExtrasJson(JSON.stringify(extras, null, 2));
    setShowCreateForm(true);
  };

  /**
   * Handle S3 resource deletion
   */
  const handleDeleteResource = async (resource) => {
    const displayName = resource.title || resource.name || 'Unnamed Resource';
    
    if (!window.confirm(
      `Are you sure you want to delete S3 resource "${displayName}"? This will also delete all associated resources. This action cannot be undone.`
    )) {
      return;
    }

    try {
      setError(null);
      setSuccess(null);
      
      // Debug: Log the resource being deleted
      console.log('Attempting to delete S3 resource with ID:', resource.id);
      console.log('Using endpoint: DELETE /resource?resource_id=' + resource.id + '&server=local');
      
      // Use the resource deletion endpoint since datasets are resources in CKAN
      await resourcesAPI.deleteById(resource.id, 'local');
      
      setSuccess(`S3 resource "${displayName}" deleted successfully!`);
      
      // Refresh the resources list
      fetchS3Resources();
      
    } catch (err) {
      console.error('Error deleting S3 resource:', err);
      console.error('Full error object:', err);
      console.error('Error response:', err.response);
      
      let errorMessage = 'Failed to delete S3 resource: ';
      
      if (err.response?.status === 404) {
        errorMessage += `Resource "${displayName}" not found. It may have been already deleted.`;
      } else if (err.response?.status === 405) {
        errorMessage += 'Resource deletion method not allowed.';
      } else if (err.response?.status === 401) {
        errorMessage += 'Authentication required. Please login again.';
      } else if (err.response?.status === 403) {
        errorMessage += 'You do not have permission to delete this resource.';
      } else {
        errorMessage += (err.response?.data?.detail || err.message);
      }
      
      setError(errorMessage);
    }
  };

  /**
   * Validate S3 URL format
   */
  const isValidS3Url = (url) => {
    const s3Patterns = [
      /^s3:\/\/[a-z0-9.-]+\/.*$/,
      /^https:\/\/[a-z0-9.-]+\.s3[.-][a-z0-9.-]+\.amazonaws\.com\/.*$/,
      /^https:\/\/s3[.-][a-z0-9.-]+\.amazonaws\.com\/[a-z0-9.-]+\/.*$/
    ];
    return s3Patterns.some(pattern => pattern.test(url));
  };

  /**
   * Get the main S3 URL from resources
   */
  const getMainS3Url = (resource) => {
    const firstResource = resource.resources && resource.resources[0];
    return firstResource?.url || 'No URL';
  };

  /**
   * Extract bucket name from S3 URL
   */
  const getBucketName = (url) => {
    if (!url || url === 'No URL') return 'Unknown';
    
    try {
      if (url.startsWith('s3://')) {
        return url.split('/')[2];
      } else if (url.includes('s3')) {
        const match = url.match(/https:\/\/([^.]+)\.s3/);
        if (match) return match[1];
        
        const bucketMatch = url.match(/amazonaws\.com\/([^\/]+)/);
        if (bucketMatch) return bucketMatch[1];
      }
    } catch (e) {
      console.error('Error parsing bucket name:', e);
    }
    
    return 'Unknown';
  };

  /**
   * Get S3 region from URL or extras
   */
  const getS3Region = (resource) => {
    const extras = resource.extras || {};
    if (extras.region) return extras.region;
    
    const firstResource = resource.resources && resource.resources[0];
    if (!firstResource?.url) return 'Unknown';
    
    try {
      const regionMatch = firstResource.url.match(/s3[.-]([a-z0-9-]+)\.amazonaws\.com/);
      if (regionMatch) return regionMatch[1];
    } catch (e) {
      console.error('Error parsing region:', e);
    }
    
    return 'us-east-1'; // Default region
  };

  return (
    <div className="s3-resources-page">
      {/* Page Header */}
      <div className="page-header">
        <h1 className="page-title">
          <Database size={32} style={{ marginRight: '0.5rem' }} />
          S3 Resources
        </h1>
        <p className="page-subtitle">
          Register and manage Amazon S3 bucket resources in your CKAN instance
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

      {/* Controls */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Controls</h3>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <span style={{ 
              fontSize: '0.875rem', 
              color: '#64748b',
              padding: '0.375rem 0.75rem',
              backgroundColor: '#f1f5f9',
              borderRadius: '6px',
              border: '1px solid #e2e8f0'
            }}>
              📍 Local Server Only
            </span>
            <button
              onClick={fetchS3Resources}
              className="btn btn-secondary"
              disabled={loading}
            >
              <RefreshCw size={16} />
              Refresh
            </button>
            <button
              onClick={() => setShowCreateForm(!showCreateForm)}
              className="btn btn-primary"
            >
              <Plus size={16} />
              {showCreateForm ? 'Cancel' : 'Create S3 Resource'}
            </button>
          </div>
        </div>
      </div>

      {/* Create/Edit S3 Resource Form */}
      {showCreateForm && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">
              {editingResource ? (
                <>
                  <Edit3 size={20} />
                  Edit S3 Resource: {editingResource.title}
                </>
              ) : (
                <>
                  <Plus size={20} />
                  Create New S3 Resource
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

          <form onSubmit={editingResource ? handleUpdate : handleCreate}>
            {/* Basic Information */}
            <div className="grid grid-2">
              <div className="form-group">
                <label className="form-label">Resource Name *</label>
                <input
                  type="text"
                  name="resource_name"
                  value={formData.resource_name}
                  onChange={handleInputChange}
                  className="form-input"
                  placeholder="my_s3_dataset"
                  required
                  disabled={editingResource} // Cannot change name when editing
                />
                <small style={{ color: '#64748b' }}>
                  Unique identifier for the S3 resource
                </small>
              </div>

              <div className="form-group">
                <label className="form-label">Resource Title *</label>
                <input
                  type="text"
                  name="resource_title"
                  value={formData.resource_title}
                  onChange={handleInputChange}
                  className="form-input"
                  placeholder="My S3 Dataset"
                  required
                />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Organization *</label>
              <select
                name="owner_org"
                value={formData.owner_org}
                onChange={handleInputChange}
                className="form-select"
                required
              >
                <option value="">Select an organization</option>
                {organizations.map(org => (
                  <option key={org} value={org}>{org}</option>
                ))}
              </select>
            </div>

            {/* S3 URL */}
            <div className="form-group">
              <label className="form-label">S3 URL *</label>
              <input
                type="text"
                name="resource_s3"
                value={formData.resource_s3}
                onChange={handleInputChange}
                className="form-input"
                placeholder="s3://my-bucket/path/to/file.csv"
                required
              />
              <small style={{ color: '#64748b' }}>
                S3 URL in format: s3://bucket-name/path/to/file or HTTPS URL
              </small>
              {formData.resource_s3 && !isValidS3Url(formData.resource_s3) && (
                <div style={{ color: '#ef4444', fontSize: '0.875rem', marginTop: '0.25rem' }}>
                  ⚠️ URL format may not be valid. Expected formats:
                  <br />• s3://bucket-name/path/to/file
                  <br />• https://bucket-name.s3.region.amazonaws.com/path/to/file
                </div>
              )}
            </div>

            <div className="form-group">
              <label className="form-label">Notes</label>
              <textarea
                name="notes"
                value={formData.notes}
                onChange={handleInputChange}
                className="form-input form-textarea"
                placeholder="Additional notes about the S3 resource..."
              />
            </div>

            {/* Extras Configuration */}
            <div className="form-group">
              <label className="form-label">Extras (JSON)</label>
              <textarea
                value={extrasJson}
                onChange={(e) => setExtrasJson(e.target.value)}
                className="form-input form-textarea"
                placeholder='{"region": "us-east-1", "access_key": "AKIA...", "secret_key": "..."}'
                style={{ fontFamily: 'monospace', fontSize: '0.875rem' }}
              />
              <small style={{ color: '#64748b' }}>
                Additional metadata including AWS credentials and configuration
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
                  {editingResource ? 'Updating...' : 'Creating...'}
                </>
              ) : (
                <>
                  <Save size={16} />
                  {editingResource ? 'Update S3 Resource' : 'Create S3 Resource'}
                </>
              )}
            </button>
          </form>
        </div>
      )}

      {/* S3 Resources List */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            S3 Resources ({s3Resources.length})
          </h3>
        </div>

        {loading && !showCreateForm ? (
          <div style={{ textAlign: 'center', padding: '2rem' }}>
            <div className="loading-spinner" style={{ margin: '0 auto' }}></div>
            <p style={{ marginTop: '1rem' }}>Loading S3 resources...</p>
          </div>
        ) : s3Resources.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: '#64748b' }}>
            <Cloud size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
            <p>No S3 resources found</p>
            <p>Create your first S3 resource using the form above</p>
          </div>
        ) : (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Resource</th>
                  <th>S3 Details</th>
                  <th>Organization</th>
                  <th>URL</th>
                  <th>Resources</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {s3Resources.map((resource, index) => {
                  const s3Url = getMainS3Url(resource);
                  const bucketName = getBucketName(s3Url);
                  const region = getS3Region(resource);
                  
                  return (
                    <tr key={`${resource.id}-${index}`}>
                      <td>
                        <div>
                          <div style={{ fontWeight: '500', marginBottom: '0.25rem' }}>
                            {resource.title || resource.name}
                          </div>
                          {resource.title && resource.name && resource.title !== resource.name && (
                            <div style={{ fontSize: '0.875rem', color: '#64748b' }}>
                              {resource.name}
                            </div>
                          )}
                          {resource.notes && (
                            <div style={{ 
                              fontSize: '0.875rem', 
                              color: '#64748b',
                              marginTop: '0.25rem',
                              maxWidth: '200px',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap'
                            }}>
                              {resource.notes}
                            </div>
                          )}
                          <div style={{ 
                            fontSize: '0.75rem', 
                            color: '#94a3b8',
                            marginTop: '0.25rem',
                            fontFamily: 'monospace'
                          }}>
                            ID: {resource.id}
                          </div>
                        </div>
                      </td>
                      <td>
                        <div>
                          <div style={{ fontSize: '0.875rem', fontWeight: '500' }}>
                            <Cloud size={14} style={{ display: 'inline', marginRight: '0.25rem' }} />
                            {bucketName}
                          </div>
                          <div style={{ fontSize: '0.875rem', color: '#64748b' }}>
                            Region: {region}
                          </div>
                        </div>
                      </td>
                      <td>
                        <span className="status-indicator status-success">
                          {resource.owner_org || 'No organization'}
                        </span>
                      </td>
                      <td>
                        {s3Url !== 'No URL' ? (
                          <a 
                            href={s3Url}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{
                              color: '#2563eb',
                              textDecoration: 'none',
                              fontSize: '0.875rem',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '0.25rem',
                              maxWidth: '150px',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap'
                            }}
                            title={s3Url}
                          >
                            <ExternalLink size={12} />
                            S3 Link
                          </a>
                        ) : (
                          <span style={{ color: '#94a3b8', fontSize: '0.875rem' }}>
                            No URL
                          </span>
                        )}
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                          <FileText size={14} />
                          <span>{resource.resources?.length || 0}</span>
                        </div>
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                          <button
                            onClick={() => startEditing(resource)}
                            className="btn btn-secondary"
                            style={{ padding: '0.375rem 0.75rem' }}
                            title="Edit S3 resource"
                          >
                            <Edit3 size={14} />
                            <span style={{ fontSize: '0.75rem' }}>Edit</span>
                          </button>
                          
                          <button
                            onClick={() => handleDeleteResource(resource)}
                            className="btn btn-danger"
                            style={{ padding: '0.375rem 0.75rem' }}
                            title="Delete S3 resource"
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

export default S3Resources;