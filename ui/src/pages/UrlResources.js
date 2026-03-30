import React, { useState, useEffect, useCallback } from 'react';
import { 
  Link as LinkIcon, 
  Plus, 
  AlertCircle, 
  Edit3,
  Save,
  X,
  Trash2,
  RefreshCw,
  ExternalLink,
  FileText
} from 'lucide-react';
import { urlAPI, organizationsAPI, searchAPI, resourcesAPI } from '../services/api';

/**
 * URL Resources page component for managing URL-based resources
 * Allows creating, listing, editing, and deleting URL resources in CKAN
 * FIXED: Resolved URL resource update serialization error
 */
const UrlResources = () => {
  const [urlResources, setUrlResources] = useState([]);
  const [organizations, setOrganizations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingResource, setEditingResource] = useState(null);
  const [selectedServer] = useState('local'); // Fixed to local for consistency

  // Form state for creating/editing URL resource
  const [formData, setFormData] = useState({
    resource_name: '',
    resource_title: '',
    owner_org: '',
    resource_url: '',
    file_type: '',
    notes: '',
    extras: {},
    mapping: {},
    processing: {}
  });

  // JSON editor states for complex fields
  const [extrasJson, setExtrasJson] = useState('{}');
  const [mappingJson, setMappingJson] = useState('{}');
  const [processingJson, setProcessingJson] = useState('{}');

  // Available file types
  const fileTypes = [
    'stream',
    'CSV',
    'TXT',
    'JSON',
    'NetCDF'
  ];

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
   * Fetch all URL resources (filtered from all datasets)
   */
  const fetchUrlResources = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Use search to get all datasets, then filter for URL resources
      const response = await searchAPI.searchByTerms([''], null, selectedServer);
      
      // Filter to show only URL resources
      const filteredResources = (response.data || []).filter(dataset => {
        const resources = dataset.resources || [];
        
        // Include if it has URL resources but exclude S3 URLs and Kafka topics
        return resources.some(resource => 
          resource.url && 
          !resource.url.startsWith('s3://') &&
          !resource.url.includes('s3.amazonaws.com') &&
          !resource.url.includes('.s3.') &&
          resource.format !== 'kafka'
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
      console.log('Filtered URL resources:', filteredResources); // Debug
      
      setUrlResources(filteredResources);
      
    } catch (err) {
      console.error('Error fetching URL resources:', err);
      setError('Failed to load URL resources: ' + 
        (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  }, [selectedServer]);

  /**
   * Fetch organizations and URL resources on component mount
   */
  useEffect(() => {
    fetchOrganizations();
    fetchUrlResources();
  }, [fetchOrganizations, fetchUrlResources]);

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
   * Parse JSON string safely with better error handling
   * FIXED: Improved JSON parsing with detailed error logging
   */
  const parseJsonSafely = (jsonString, fallback = {}, fieldName = 'JSON') => {
    try {
      if (!jsonString || jsonString.trim() === '') {
        return fallback;
      }
      
      const parsed = JSON.parse(jsonString);
      console.log(`Successfully parsed ${fieldName}:`, parsed); // Debug log
      return parsed;
    } catch (parseError) {
      console.error(`Error parsing ${fieldName}:`, parseError);
      console.error(`Invalid ${fieldName} string:`, jsonString);
      
      // Return fallback but also set a user-friendly error
      setError(`Invalid ${fieldName} format. Please check your JSON syntax.`);
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
      resource_url: '',
      file_type: '',
      notes: '',
      extras: {},
      mapping: {},
      processing: {}
    });
    setExtrasJson('{}');
    setMappingJson('{}');
    setProcessingJson('{}');
    setEditingResource(null);
    setShowCreateForm(false);
  };

  /**
   * Prepare form data for submission
   * FIXED: Improved data preparation with better validation and error handling
   */
  const prepareFormData = () => {
    console.log('Preparing form data for submission...'); // Debug log
    console.log('Current form data:', formData); // Debug log
    console.log('JSON fields:', { extrasJson, mappingJson, processingJson }); // Debug log

    // Parse JSON fields with better error handling
    const extras = parseJsonSafely(extrasJson, {}, 'Extras');
    const mapping = parseJsonSafely(mappingJson, {}, 'Mapping');
    const processing = parseJsonSafely(processingJson, {}, 'Processing');

    // If there was a JSON parsing error, return early
    if (error && error.includes('Invalid') && error.includes('format')) {
      return null;
    }

    // Prepare the request data according to the API specification
    const requestData = {
      // Always include required fields even if empty (let API validate)
      resource_name: formData.resource_name || undefined,
      resource_title: formData.resource_title || undefined,
      owner_org: formData.owner_org || undefined,
      resource_url: formData.resource_url || undefined,
      notes: formData.notes || undefined,
      // Only include complex objects if they have content (not empty objects)
      extras: (extras && Object.keys(extras).length > 0) ? extras : undefined,
      mapping: (mapping && Object.keys(mapping).length > 0) ? mapping : undefined,
      processing: (processing && Object.keys(processing).length > 0) ? processing : undefined
    };

    // FIXED: Handle file_type validation - only include if it's a valid enum value
    const validFileTypes = ['stream', 'CSV', 'TXT', 'JSON', 'NetCDF'];
    if (formData.file_type && validFileTypes.includes(formData.file_type)) {
      requestData.file_type = formData.file_type;
    }
    // If file_type is empty or "Auto-detect", don't include it in the request

    // Remove undefined fields completely (API might not like them)
    const cleanedData = {};
    Object.keys(requestData).forEach(key => {
      if (requestData[key] !== undefined && requestData[key] !== '') {
        cleanedData[key] = requestData[key];
      }
    });

    console.log('Final prepared data:', cleanedData); // Debug log
    return cleanedData;
  };

  /**
   * Handle form submission for creating URL resource
   */
  const handleCreate = async (e) => {
    e.preventDefault();
    
    try {
      setError(null);
      setSuccess(null);
      setLoading(true);

      const requestData = prepareFormData();
      
      // If data preparation failed due to JSON parsing error, stop here
      if (!requestData) {
        setLoading(false);
        return;
      }

      console.log('Creating URL resource with data:', requestData); // Debug log
      await urlAPI.create(requestData, selectedServer);
      
      setSuccess('URL resource created successfully!');
      resetForm();
      fetchUrlResources();
      
    } catch (err) {
      console.error('Error creating URL resource:', err);
      console.error('Full error object:', err.response); // Additional debug
      
      let errorMessage = 'Failed to create URL resource: ';
      
      // Better error message handling
      if (err.response?.data?.detail) {
        if (typeof err.response.data.detail === 'object') {
          errorMessage += JSON.stringify(err.response.data.detail);
        } else {
          errorMessage += err.response.data.detail;
        }
      } else if (err.message) {
        errorMessage += err.message;
      } else {
        errorMessage += 'Unknown error occurred';
      }
      
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Handle form submission for updating URL resource
   * FIXED: Improved validation and data preparation for updates
   */
  const handleUpdate = async (e) => {
    e.preventDefault();
    
    try {
      setError(null);
      setSuccess(null);
      setLoading(true);

      // FIXED: Ensure we're using the correct resource ID from the editing resource
      if (!editingResource || !editingResource.id) {
        throw new Error('Invalid resource ID for update operation');
      }

      const requestData = prepareFormData();
      
      // If data preparation failed due to JSON parsing error, stop here
      if (!requestData) {
        setLoading(false);
        return;
      }

      // FIXED: Ensure all critical fields are present for update
      // Even though API says they're optional, practice shows some are required
      const updateData = {
        // Always include these fields even if they haven't changed
        resource_name: formData.resource_name || editingResource.name,
        resource_title: formData.resource_title || editingResource.title,
        owner_org: formData.owner_org || editingResource.owner_org,
        resource_url: formData.resource_url || (editingResource.resources?.[0]?.url),
        // Optional fields - only include if they have valid values
        ...(formData.notes && { notes: formData.notes }),
        ...(requestData.extras && { extras: requestData.extras }),
        ...(requestData.mapping && { mapping: requestData.mapping }),
        ...(requestData.processing && { processing: requestData.processing })
      };

      // FIXED: Handle file_type validation - only include if it's a valid enum value
      const validFileTypes = ['stream', 'CSV', 'TXT', 'JSON', 'NetCDF'];
      if (formData.file_type && validFileTypes.includes(formData.file_type)) {
        updateData.file_type = formData.file_type;
      }
      // If file_type is empty or "Auto-detect", don't include it in the request
      // The API will handle it appropriately

      // Validate required fields before sending
      const requiredFields = ['resource_name', 'resource_title', 'owner_org', 'resource_url'];
      const missingFields = requiredFields.filter(field => !updateData[field]);
      
      if (missingFields.length > 0) {
        throw new Error(`Missing required fields: ${missingFields.join(', ')}`);
      }

      console.log('Updating URL resource with ID:', editingResource.id); // Debug log
      console.log('Final update data:', updateData); // Debug log
      console.log('API endpoint will be:', `PUT /url/${editingResource.id}?server=${selectedServer}`); // Debug log

      await urlAPI.update(editingResource.id, updateData, selectedServer);
      
      setSuccess('URL resource updated successfully!');
      resetForm();
      fetchUrlResources();
      
    } catch (err) {
      console.error('Error updating URL resource:', err);
      console.error('Full error object:', err.response); // Additional debug
      console.error('Error config:', err.config); // Request configuration debug
      
      let errorMessage = 'Failed to update URL resource: ';
      
      // Better error message handling for updates
      if (err.response?.status === 404) {
        errorMessage += 'Resource not found. It may have been deleted.';
      } else if (err.response?.status === 400) {
        errorMessage += 'Invalid data provided. Please check your inputs.';
      } else if (err.response?.status === 422) {
        const detail = err.response?.data?.detail;
        if (detail) {
          if (typeof detail === 'object') {
            // Handle validation error details
            if (detail.error && detail.detail) {
              errorMessage += `${detail.error}: ${detail.detail}`;
            } else if (Array.isArray(detail)) {
              // Handle array of validation errors
              const validationErrors = detail.map(error => 
                `Field '${error.loc?.join('.')}': ${error.msg || error.type}`
              ).join(', ');
              errorMessage += `Validation errors: ${validationErrors}`;
            } else {
              errorMessage += JSON.stringify(detail, null, 2);
            }
          } else {
            errorMessage += detail;
          }
        } else {
          errorMessage += 'Validation error. Please check required fields (resource_name, resource_title, owner_org, resource_url).';
        }
      } else if (err.message) {
        errorMessage += err.message;
      } else {
        errorMessage += 'Unknown error occurred';
      }
      
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Start editing a URL resource
   * FIXED: Improved data extraction and JSON field preparation
   */
  const startEditing = (resource) => {
    console.log('Starting to edit resource:', resource); // Debug log
    
    setEditingResource(resource);
    const extras = resource.extras || {};
    const firstResource = resource.resources && resource.resources[0];
    
    // Extract mapping and processing from extras if they exist
    const mapping = extras.mapping || {};
    const processing = extras.processing || {};
    
    // Create clean extras without mapping and processing (since they have separate fields)
    const cleanExtras = { ...extras };
    delete cleanExtras.mapping;
    delete cleanExtras.processing;
    
    const editFormData = {
      resource_name: resource.name || '',
      resource_title: resource.title || '',
      owner_org: resource.owner_org || '',
      resource_url: firstResource?.url || '',
      file_type: firstResource?.format || '',
      notes: resource.notes || '',
      extras: cleanExtras,
      mapping: mapping,
      processing: processing
    };
    
    console.log('Setting edit form data:', editFormData); // Debug log
    
    setFormData(editFormData);
    
    // Set JSON fields with proper formatting
    try {
      setExtrasJson(JSON.stringify(cleanExtras, null, 2));
      setMappingJson(JSON.stringify(mapping, null, 2));
      setProcessingJson(JSON.stringify(processing, null, 2));
    } catch (jsonError) {
      console.error('Error stringifying JSON for edit form:', jsonError);
      // Fallback to empty objects
      setExtrasJson('{}');
      setMappingJson('{}');
      setProcessingJson('{}');
    }
    
    setShowCreateForm(true);
  };

  /**
   * Handle URL resource deletion
   */
  const handleDeleteResource = async (resource) => {
    const displayName = resource.title || resource.name || 'Unnamed Resource';
    
    if (!window.confirm(
      `Are you sure you want to delete URL resource "${displayName}"? This will also delete all associated resources. This action cannot be undone.`
    )) {
      return;
    }

    try {
      setError(null);
      setSuccess(null);
      
      // Debug: Log the resource being deleted
      console.log('Attempting to delete URL resource with ID:', resource.id);
      console.log('Using endpoint: DELETE /resource?resource_id=' + resource.id + '&server=local');
      
      // Use the resource deletion endpoint since datasets are resources in CKAN
      await resourcesAPI.deleteById(resource.id, 'local');
      
      setSuccess(`URL resource "${displayName}" deleted successfully!`);
      
      // Refresh the resources list
      fetchUrlResources();
      
    } catch (err) {
      console.error('Error deleting URL resource:', err);
      console.error('Full error object:', err);
      console.error('Error response:', err.response);
      
      let errorMessage = 'Failed to delete URL resource: ';
      
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
   * Get the main URL from resources
   */
  const getMainUrl = (resource) => {
    const firstResource = resource.resources && resource.resources[0];
    return firstResource?.url || 'No URL';
  };

  /**
   * Get file type badge
   */
  const getFileType = (resource) => {
    const firstResource = resource.resources && resource.resources[0];
    return firstResource?.format || 'Unknown';
  };

  return (
    <div className="url-resources-page">
      {/* Page Header */}
      <div className="page-header">
        <h1 className="page-title">
          <LinkIcon size={32} style={{ marginRight: '0.5rem' }} />
          URL Resources
        </h1>
        <p className="page-subtitle">
          Register and manage URL-based resources in your CKAN instance
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
              onClick={fetchUrlResources}
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
              {showCreateForm ? 'Cancel' : 'Create URL Resource'}
            </button>
          </div>
        </div>
      </div>

      {/* Create/Edit URL Resource Form */}
      {showCreateForm && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">
              {editingResource ? (
                <>
                  <Edit3 size={20} />
                  Edit URL Resource: {editingResource.title}
                </>
              ) : (
                <>
                  <Plus size={20} />
                  Create New URL Resource
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
                  placeholder="example_resource_name"
                  required
                  disabled={editingResource} // Cannot change name when editing
                />
                <small style={{ color: '#64748b' }}>
                  Unique identifier for the resource
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
                  placeholder="Example Resource Title"
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

            {/* URL and File Type */}
            <div className="grid grid-2">
              <div className="form-group">
                <label className="form-label">Resource URL *</label>
                <input
                  type="url"
                  name="resource_url"
                  value={formData.resource_url}
                  onChange={handleInputChange}
                  className="form-input"
                  placeholder="https://example.com/data.csv"
                  required
                />
                <small style={{ color: '#64748b' }}>
                  Direct URL to the resource file
                </small>
              </div>

              <div className="form-group">
                <label className="form-label">File Type</label>
                <select
                  name="file_type"
                  value={formData.file_type}
                  onChange={handleInputChange}
                  className="form-select"
                >
                  <option value="">Auto-detect</option>
                  {fileTypes.map(type => (
                    <option key={type} value={type}>{type}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Description</label>
              <textarea
                name="notes"
                value={formData.notes}
                onChange={handleInputChange}
                className="form-input form-textarea"
                placeholder="Additional notes about the resource..."
              />
            </div>

            {/* Advanced Configuration */}
            <div className="grid grid-3">
              <div className="form-group">
                <label className="form-label">Extras (JSON)</label>
                <textarea
                  value={extrasJson}
                  onChange={(e) => setExtrasJson(e.target.value)}
                  className="form-input form-textarea"
                  placeholder='{"key1": "value1", "key2": "value2"}'
                  style={{ fontFamily: 'monospace', fontSize: '0.875rem' }}
                />
                <small style={{ color: '#64748b' }}>
                  Additional metadata as JSON
                </small>
              </div>

              <div className="form-group">
                <label className="form-label">Mapping (JSON)</label>
                <textarea
                  value={mappingJson}
                  onChange={(e) => setMappingJson(e.target.value)}
                  className="form-input form-textarea"
                  placeholder='{"field1": "mapping1", "field2": "mapping2"}'
                  style={{ fontFamily: 'monospace', fontSize: '0.875rem' }}
                />
                <small style={{ color: '#64748b' }}>
                  Field mapping configuration
                </small>
              </div>

              <div className="form-group">
                <label className="form-label">Processing (JSON)</label>
                <textarea
                  value={processingJson}
                  onChange={(e) => setProcessingJson(e.target.value)}
                  className="form-input form-textarea"
                  placeholder='{"delimiter": ",", "header_line": 1}'
                  style={{ fontFamily: 'monospace', fontSize: '0.875rem' }}
                />
                <small style={{ color: '#64748b' }}>
                  Processing configuration for CSV files
                </small>
              </div>
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
                  {editingResource ? 'Update URL Resource' : 'Create URL Resource'}
                </>
              )}
            </button>
          </form>
        </div>
      )}

      {/* URL Resources List */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            URL Resources ({urlResources.length})
          </h3>
        </div>

        {loading && !showCreateForm ? (
          <div style={{ textAlign: 'center', padding: '2rem' }}>
            <div className="loading-spinner" style={{ margin: '0 auto' }}></div>
            <p style={{ marginTop: '1rem' }}>Loading URL resources...</p>
          </div>
        ) : urlResources.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: '#64748b' }}>
            <LinkIcon size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
            <p>No URL resources found</p>
            <p>Create your first URL resource using the form above</p>
          </div>
        ) : (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Resource</th>
                  <th>URL</th>
                  <th>File Type</th>
                  <th>Organization</th>
                  <th>Resources</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {urlResources.map((resource, index) => {
                  const mainUrl = getMainUrl(resource);
                  const fileType = getFileType(resource);
                  
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
                        {mainUrl !== 'No URL' ? (
                          <a 
                            href={mainUrl}
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
                            title={mainUrl}
                          >
                            <ExternalLink size={12} />
                            {mainUrl}
                          </a>
                        ) : (
                          <span style={{ color: '#94a3b8', fontSize: '0.875rem' }}>
                            No URL
                          </span>
                        )}
                      </td>
                      <td>
                        <span className="status-indicator status-info">
                          {fileType}
                        </span>
                      </td>
                      <td>
                        <span className="status-indicator status-success">
                          {resource.owner_org || 'No organization'}
                        </span>
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
                            title="Edit URL resource"
                          >
                            <Edit3 size={14} />
                            <span style={{ fontSize: '0.75rem' }}>Edit</span>
                          </button>
                          
                          <button
                            onClick={() => handleDeleteResource(resource)}
                            className="btn btn-danger"
                            style={{ padding: '0.375rem 0.75rem' }}
                            title="Delete URL resource"
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

export default UrlResources;