import React, { useState, useEffect, useCallback } from 'react';
import {
  Database,
  Plus,
  AlertCircle,
  Edit3,
  Save,
  X,
  FileText,
  Trash2,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Link
} from 'lucide-react';
import { organizationsAPI, searchAPI, generalDatasetAPI, datasetAPI, resourcesAPI } from '../services/api';

/**
 * Dataset Management component for creating and managing general datasets
 * Provides full CRUD operations for datasets with flexible schema
 */
const DatasetManagement = () => {
  const [datasets, setDatasets] = useState([]);
  const [organizations, setOrganizations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingDataset, setEditingDataset] = useState(null);
  const [selectedServer] = useState('local'); // Fixed to local for consistency
  const [expandedDatasets, setExpandedDatasets] = useState({});
  const [editingResource, setEditingResource] = useState(null);
  const [resourceFormData, setResourceFormData] = useState({
    name: '',
    description: '',
    url: '',
    format: ''
  });

  // Form state for creating/editing dataset
  const [formData, setFormData] = useState({
    name: '',
    title: '',
    owner_org: '',
    notes: '',
    extras: {},
    resources: []
  });

  // JSON editor states for complex fields
  const [extrasJson, setExtrasJson] = useState('{}');
  const [resourcesJson, setResourcesJson] = useState('[]');

  // Extras editor: 'fields' for guided key/value rows, 'json' for raw JSON
  const [extrasMode, setExtrasMode] = useState('fields');
  const [extrasPairs, setExtrasPairs] = useState([]);
  const [extrasModeError, setExtrasModeError] = useState(null);

  /**
   * True when value is a flat object whose values are all string/number/boolean/null.
   * The guided key/value editor can only round-trip this shape; nested objects or
   * arrays force the user into raw JSON mode.
   */
  const isFlatPrimitiveMap = (obj) => {
    if (!obj || typeof obj !== 'object' || Array.isArray(obj)) return false;
    return Object.values(obj).every((v) =>
      v === null || ['string', 'number', 'boolean'].includes(typeof v)
    );
  };

  const objectToPairs = (obj) => {
    if (!obj || typeof obj !== 'object') return [];
    return Object.entries(obj).map(([key, value]) => ({
      key,
      value: value === null || value === undefined ? '' : String(value)
    }));
  };

  const pairsToObject = (pairs) => {
    const out = {};
    for (const { key, value } of pairs) {
      const trimmed = (key || '').trim();
      if (trimmed === '') continue;
      out[trimmed] = value;
    }
    return out;
  };

  const addExtraPair = () => {
    setExtrasPairs((prev) => [...prev, { key: '', value: '' }]);
    setExtrasModeError(null);
  };

  const removeExtraPair = (idx) => {
    setExtrasPairs((prev) => prev.filter((_, i) => i !== idx));
  };

  const updateExtraPair = (idx, field, value) => {
    setExtrasPairs((prev) =>
      prev.map((p, i) => (i === idx ? { ...p, [field]: value } : p))
    );
  };

  const switchToJsonMode = () => {
    const obj = pairsToObject(extrasPairs);
    setExtrasJson(JSON.stringify(obj, null, 2));
    setExtrasMode('json');
    setExtrasModeError(null);
  };

  const switchToFieldsMode = () => {
    let parsed;
    try {
      parsed = extrasJson.trim() === '' ? {} : JSON.parse(extrasJson);
    } catch {
      setExtrasModeError('Cannot switch to simple fields: the JSON is invalid.');
      return;
    }
    if (!isFlatPrimitiveMap(parsed)) {
      setExtrasModeError(
        'Cannot switch to simple fields: this metadata has nested or non-text values. Stay in advanced mode to edit it.'
      );
      return;
    }
    setExtrasPairs(objectToPairs(parsed));
    setExtrasMode('fields');
    setExtrasModeError(null);
  };

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
   * Fetch all datasets (filtered to show only general datasets)
   */
  const fetchDatasets = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Use search to get all datasets
      const response = await searchAPI.searchByTerms([''], null, selectedServer);
      
      // Filter out specific resource types to show only general datasets
      const filteredDatasets = (response.data || []).filter(dataset => {
        const extras = dataset.extras || {};
        const resources = dataset.resources || [];
        
        // Exclude if it's a Kafka topic
        if (extras.kafka_topic || extras.kafka_host) {
          return false;
        }
        
        // Exclude if it's in the services organization
        if (dataset.owner_org === 'services') {
          return false;
        }
        
        // Exclude if it has S3 resources
        if (resources.some(resource => 
          resource.url && (
            resource.url.startsWith('s3://') || 
            resource.url.includes('s3.amazonaws.com') ||
            resource.url.includes('.s3.')
          )
        )) {
          return false;
        }
        
        // Exclude if it's primarily a URL resource (single URL resource with no other content)
        if (resources.length === 1 && 
            resources[0].url && 
            !resources[0].url.startsWith('s3://') &&
            Object.keys(extras).length === 0 &&
            (!dataset.notes || dataset.notes.trim() === '')) {
          return false;
        }
        
        // Include everything else (general datasets)
        return true;
      });
      
      setDatasets(filteredDatasets);
      
    } catch (err) {
      console.error('Error fetching datasets:', err);
      setError('Failed to load datasets: ' + 
        (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  }, [selectedServer]);

  /**
   * Fetch organizations and datasets on component mount
   */
  useEffect(() => {
    fetchOrganizations();
    fetchDatasets();
  }, [fetchOrganizations, fetchDatasets]);

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
      name: '',
      title: '',
      owner_org: '',
      notes: '',
      extras: {},
      resources: []
    });
    setExtrasJson('{}');
    setResourcesJson('[]');
    setExtrasMode('fields');
    setExtrasPairs([]);
    setExtrasModeError(null);
    setEditingDataset(null);
    setShowCreateForm(false);
  };

  /**
   * Prepare form data for submission
   */
  const prepareFormData = () => {
    // Parse JSON fields
    const extras = extrasMode === 'fields'
      ? pairsToObject(extrasPairs)
      : parseJsonSafely(extrasJson, {});
    const resources = parseJsonSafely(resourcesJson, []);

    // Prepare final data
    const requestData = {
      ...formData,
      extras: Object.keys(extras).length > 0 ? extras : undefined,
      resources: resources.length > 0 ? resources : undefined
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
   * Handle form submission for creating dataset
   */
  const handleCreate = async (e) => {
    e.preventDefault();
    
    try {
      setError(null);
      setSuccess(null);
      setLoading(true);

      const requestData = prepareFormData();
      await generalDatasetAPI.create(requestData, selectedServer);

      setSuccess('Dataset created successfully!');
      resetForm();
      fetchDatasets();
      
    } catch (err) {
      console.error('Error creating dataset:', err);
      setError('Failed to create dataset: ' + 
        (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  /**
   * Handle form submission for updating dataset
   */
  const handleUpdate = async (e) => {
    e.preventDefault();
    
    try {
      setError(null);
      setSuccess(null);
      setLoading(true);

      const requestData = prepareFormData();
      await generalDatasetAPI.partialUpdate(editingDataset.id, requestData, selectedServer);

      setSuccess('Dataset updated successfully!');
      resetForm();
      fetchDatasets();
      
    } catch (err) {
      console.error('Error updating dataset:', err);
      setError('Failed to update dataset: ' + 
        (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  /**
   * Start editing a dataset
   */
  const startEditing = (dataset) => {
    setEditingDataset(dataset);
    setFormData({
      name: dataset.name || '',
      title: dataset.title || '',
      owner_org: dataset.owner_org || '',
      notes: dataset.notes || '',
      extras: dataset.extras || {},
      resources: dataset.resources || []
    });
    
    // Set JSON fields
    const extras = dataset.extras || {};
    setExtrasJson(JSON.stringify(extras, null, 2));
    setResourcesJson(JSON.stringify(dataset.resources || [], null, 2));

    // Default the extras editor to guided fields when the data is a flat
    // primitive map; fall back to raw JSON for nested/non-text values.
    if (isFlatPrimitiveMap(extras)) {
      setExtrasPairs(objectToPairs(extras));
      setExtrasMode('fields');
    } else {
      setExtrasPairs([]);
      setExtrasMode('json');
    }
    setExtrasModeError(null);

    setShowCreateForm(true);
  };

  /**
   * Handle sending dataset to pre-ckan server
   */
  const handleSendToPreCkan = async (dataset) => {
    const displayName = dataset.title || dataset.name || 'Unnamed Dataset';
    
    if (!window.confirm(
      `Send dataset "${displayName}" to Pre-CKAN server? This will create a copy of the dataset on the pre-ckan server with required Pre-CKAN metadata.`
    )) {
      return;
    }

    try {
      setError(null);
      setSuccess(null);
      
      // Debug: Log the dataset being sent
      console.log('Attempting to send dataset to pre-ckan:', dataset);
      
      // Prepare the dataset data for pre-ckan with all required fields
      const currentDate = new Date().toISOString().split('T')[0]; // YYYY-MM-DD format
      const existingExtras = dataset.extras || {};
      
      // Ensure all required Pre-CKAN fields are present
      const datasetForPreCkan = {
        name: dataset.name,
        title: dataset.title,
        owner_org: dataset.owner_org,
        // Required: notes
        notes: dataset.notes || 'Dataset transferred from local CKAN server',
        // Optional fields
        version: dataset.version,
        // Required and optional extras for Pre-CKAN
        extras: {
          // Keep existing extras
          ...existingExtras,
          // Required Pre-CKAN extras
          uploadType: existingExtras.uploadType || 'manual',
          dataType: existingExtras.dataType || 'dataset',
          purpose: existingExtras.purpose || 'Data sharing and analysis',
          publisherName: existingExtras.publisherName || 'Local CKAN Administrator',
          publisherEmail: existingExtras.publisherEmail || 'admin@example.com',
          creatorName: existingExtras.creatorName || 'Local CKAN System',
          creatorEmail: existingExtras.creatorEmail || 'system@example.com',
          pocName: existingExtras.pocName || 'Local CKAN Administrator',
          pocEmail: existingExtras.pocEmail || 'admin@example.com',
          otherLicense: existingExtras.otherLicense || 'Standard license terms apply',
          issueDate: existingExtras.issueDate || currentDate,
          lastUpdateDate: existingExtras.lastUpdateDate || currentDate
        },
        // Required: resources with required fields
        resources: (dataset.resources && dataset.resources.length > 0) 
          ? dataset.resources.map(resource => {
              console.log('Processing resource:', resource); // Debug log
              return {
                url: resource.url || 'http://example.com/placeholder',
                // Required resource fields for Pre-CKAN
                name: resource.name || 'Transferred Resource',
                description: resource.description || 'Resource transferred from local CKAN server',
                mimetype: resource.mimetype || resource.format 
                  ? `application/${(resource.format || 'octet-stream').toLowerCase()}`
                  : 'application/octet-stream',
                status: resource.status || 'active',
                // Optional resource fields
                format: resource.format || 'Unknown'
              };
            })
          : [
              // Default placeholder resource if none exist
              {
                url: 'http://example.com/placeholder',
                name: 'Placeholder Resource',
                description: 'This dataset was transferred without resources from local CKAN',
                mimetype: 'text/plain',
                status: 'active',
                format: 'TXT'
              }
            ]
      };
      
      // If no resources exist, add a placeholder
      if (!datasetForPreCkan.resources || datasetForPreCkan.resources.length === 0) {
        datasetForPreCkan.resources = [{
          url: 'http://example.com/placeholder',
          name: 'Placeholder Resource',
          description: 'This dataset was transferred without resources from local CKAN',
          mimetype: 'text/plain',
          status: 'active',
          format: 'TXT'
        }];
      }
      
      // Debug: Log each resource to verify required fields
      console.log('Final resources being sent to Pre-CKAN:');
      datasetForPreCkan.resources.forEach((resource, index) => {
        console.log(`Resource ${index + 1}:`, {
          name: resource.name,
          description: resource.description,
          mimetype: resource.mimetype,
          status: resource.status,
          url: resource.url,
          format: resource.format
        });
      });
      
      console.log('Sending dataset to pre-ckan with Pre-CKAN required fields:');
      console.log('Dataset basics:', {
        name: datasetForPreCkan.name,
        title: datasetForPreCkan.title,
        notes: datasetForPreCkan.notes,
        license_id: datasetForPreCkan.license_id
      });
      console.log('Dataset extras:', datasetForPreCkan.extras);
      console.log('Dataset resources count:', datasetForPreCkan.resources.length);
      
      // Send to pre-ckan server
      await generalDatasetAPI.create(datasetForPreCkan, 'pre_ckan');
      
      setSuccess(`Dataset "${displayName}" sent to Pre-CKAN server successfully! Note: Some fields were auto-filled to meet Pre-CKAN requirements.`);
      
    } catch (err) {
      console.error('Error sending dataset to pre-ckan:', err);
      console.error('Full error object:', err);
      console.error('Error response:', err.response);
      
      let errorMessage = 'Failed to send dataset to Pre-CKAN: ';
      
      if (err.response?.status === 409) {
        errorMessage += `Dataset "${displayName}" already exists on Pre-CKAN server.`;
      } else if (err.response?.status === 400) {
        const detail = err.response?.data?.detail || 'Unknown validation error';
        errorMessage += 'Invalid dataset data. ' + detail;
        
        // If it's still missing fields, show which ones
        if (detail.includes('Missing required fields')) {
          errorMessage += '\n\nTip: Some Pre-CKAN fields may need to be manually configured. Please check the Pre-CKAN documentation for specific requirements.';
        }
      } else if (err.response?.status === 401) {
        errorMessage += 'Authentication required. Please login again.';
      } else if (err.response?.status === 403) {
        errorMessage += 'You do not have permission to create datasets on Pre-CKAN server.';
      } else if (err.response?.status === 404) {
        errorMessage += 'Pre-CKAN server is not available or configured.';
      } else {
        errorMessage += (err.response?.data?.detail || err.message);
      }
      
      setError(errorMessage);
    }
  };

  /**
   * Handle dataset deletion
   */
  const handleDeleteDataset = async (dataset) => {
    const displayName = dataset.title || dataset.name || 'Unnamed Dataset';
    
    if (!window.confirm(
      `Are you sure you want to delete dataset "${displayName}"? This will also delete all associated resources. This action cannot be undone.`
    )) {
      return;
    }

    try {
      setError(null);
      setSuccess(null);
      
      // Debug: Log the dataset being deleted
      console.log('Attempting to delete dataset with ID:', dataset.id);
      console.log('Using endpoint: DELETE /resource?resource_id=' + dataset.id + '&server=local');
      
      // Use the resource deletion endpoint since datasets are resources in CKAN
      await datasetAPI.delete(dataset.id, 'local'); // Always use local for deletion
      
      setSuccess(`Dataset "${displayName}" deleted successfully!`);
      
      // Refresh the datasets list
      fetchDatasets();
      
    } catch (err) {
      console.error('Error deleting dataset:', err);
      console.error('Full error object:', err);
      console.error('Error response:', err.response);
      
      let errorMessage = 'Failed to delete dataset: ';
      
      if (err.response?.status === 404) {
        errorMessage += `Dataset "${displayName}" not found. It may have been already deleted.`;
      } else if (err.response?.status === 405) {
        errorMessage += 'Dataset deletion method not allowed.';
      } else if (err.response?.status === 401) {
        errorMessage += 'Authentication required. Please login again.';
      } else if (err.response?.status === 403) {
        errorMessage += 'You do not have permission to delete this dataset.';
      } else {
        errorMessage += (err.response?.data?.detail || err.message);
      }
      
      setError(errorMessage);
    }
  };

  /**
   * Get dataset type badge
   */
  const getDatasetTypeBadge = (dataset) => {
    const extras = dataset.extras || {};
    
    // Check for specific resource types
    if (dataset.resources && dataset.resources.length > 0) {
      const resource = dataset.resources[0];
      if (extras.kafka_topic) return { type: 'Kafka', color: 'status-info' };
      if (resource.url && resource.url.startsWith('s3://')) return { type: 'S3', color: 'status-warning' };
      if (resource.url) return { type: 'URL', color: 'status-success' };
    }
    
    return { type: 'General', color: 'status-info' };
  };

  /**
   * Toggle dataset expansion to show/hide resources
   */
  const toggleDatasetExpansion = (datasetId) => {
    setExpandedDatasets(prev => ({
      ...prev,
      [datasetId]: !prev[datasetId]
    }));
  };

  /**
   * Start editing a resource
   */
  const startEditingResource = (resource, datasetId) => {
    setEditingResource({ ...resource, datasetId });
    setResourceFormData({
      name: resource.name || '',
      description: resource.description || '',
      url: resource.url || '',
      format: resource.format || ''
    });
  };

  /**
   * Cancel resource editing
   */
  const cancelResourceEdit = () => {
    setEditingResource(null);
    setResourceFormData({
      name: '',
      description: '',
      url: '',
      format: ''
    });
  };

  /**
   * Handle resource form input changes
   */
  const handleResourceInputChange = (e) => {
    const { name, value } = e.target;
    setResourceFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  /**
   * Save resource changes
   */
  const handleSaveResource = async () => {
    if (!editingResource) return;

    try {
      setError(null);
      setSuccess(null);

      await resourcesAPI.patch(editingResource.id, resourceFormData, selectedServer);

      setSuccess(`Resource "${resourceFormData.name}" updated successfully!`);
      cancelResourceEdit();
      fetchDatasets();

    } catch (err) {
      console.error('Error updating resource:', err);
      setError('Failed to update resource: ' +
        (err.response?.data?.detail || err.message));
    }
  };

  /**
   * Delete a resource
   */
  const handleDeleteResource = async (resource) => {
    const displayName = resource.name || 'Unnamed Resource';

    if (!window.confirm(
      `Are you sure you want to delete resource "${displayName}"? This action cannot be undone.`
    )) {
      return;
    }

    try {
      setError(null);
      setSuccess(null);

      await resourcesAPI.deleteById(resource.id, selectedServer);

      setSuccess(`Resource "${displayName}" deleted successfully!`);
      fetchDatasets();

    } catch (err) {
      console.error('Error deleting resource:', err);
      setError('Failed to delete resource: ' +
        (err.response?.data?.detail || err.message));
    }
  };

  return (
    <div className="dataset-management-page">
      {/* Page Header */}
      <div className="page-header">
        <h1 className="page-title">
          <Database size={32} style={{ marginRight: '0.5rem' }} />
          Dataset Management
        </h1>
        <p className="page-subtitle">
          Create and manage general datasets (excludes URL, S3, Kafka, and Service resources)
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
              onClick={() => setShowCreateForm(!showCreateForm)}
              className="btn btn-primary"
            >
              <Plus size={16} />
              {showCreateForm ? 'Cancel' : 'Create Dataset'}
            </button>
          </div>
        </div>
      </div>

      {/* Create/Edit Dataset Form */}
      {showCreateForm && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">
              {editingDataset ? (
                <>
                  <Edit3 size={20} />
                  Edit Dataset: {editingDataset.title}
                </>
              ) : (
                <>
                  <Plus size={20} />
                  Create New Dataset
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

          <form onSubmit={editingDataset ? handleUpdate : handleCreate}>
            {/* Basic Information */}
            <div className="grid grid-2">
              <div className="form-group">
                <label className="form-label">Dataset Name *</label>
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleInputChange}
                  className="form-input"
                  placeholder="my_dataset_name"
                  required
                  disabled={editingDataset} // Cannot change name when editing
                />
                <small style={{ color: '#64748b' }}>
                  Unique identifier (lowercase, no spaces)
                </small>
              </div>

              <div className="form-group">
                <label className="form-label">Dataset Title *</label>
                <input
                  type="text"
                  name="title"
                  value={formData.title}
                  onChange={handleInputChange}
                  className="form-input"
                  placeholder="My Dataset Title"
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

            <div className="form-group">
              <label className="form-label">Description</label>
              <textarea
                name="notes"
                value={formData.notes}
                onChange={handleInputChange}
                className="form-input form-textarea"
                placeholder="Description of the dataset..."
              />
            </div>

            {/* Advanced Configuration */}
            <div className="grid grid-2">
              <div className="form-group">
                <label className="form-label">Extras (JSON)</label>
                <textarea
                  value={extrasJson}
                  onChange={(e) => setExtrasJson(e.target.value)}
                  className="form-input form-textarea"
                  placeholder='{"version": "1.0", "project": "research"}'
                  style={{ fontFamily: 'monospace', fontSize: '0.875rem', minHeight: '120px' }}
                />
                <small style={{ color: '#64748b' }}>
                  Additional metadata as JSON
                </small>
              </div>

              <div className="form-group">
                <label className="form-label">Resources (JSON)</label>
                <textarea
                  value={resourcesJson}
                  onChange={(e) => setResourcesJson(e.target.value)}
                  className="form-input form-textarea"
                  placeholder='[{"url": "http://example.com/data.csv", "name": "main_data", "format": "CSV"}]'
                  style={{ fontFamily: 'monospace', fontSize: '0.875rem', minHeight: '120px' }}
                />
                <small style={{ color: '#64748b' }}>
                  List of resources as JSON array
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
                  {editingDataset ? 'Updating...' : 'Creating...'}
                </>
              ) : (
                <>
                  <Save size={16} />
                  {editingDataset ? 'Update Dataset' : 'Create Dataset'}
                </>
              )}
            </button>
          </form>
        </div>
      )}

      {/* Datasets List */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            Datasets ({datasets.length})
          </h3>
        </div>

        {loading && !showCreateForm ? (
          <div style={{ textAlign: 'center', padding: '2rem' }}>
            <div className="loading-spinner" style={{ margin: '0 auto' }}></div>
            <p style={{ marginTop: '1rem' }}>Loading datasets...</p>
          </div>
        ) : datasets.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: '#64748b' }}>
            <Database size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
            <p>No general datasets found</p>
            <p>Create your first general dataset using the form above, or check other pages for specific resource types (URL, S3, Kafka, Services)</p>
          </div>
        ) : (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Dataset</th>
                  <th>Type</th>
                  <th>Organization</th>
                  <th>Resources</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {datasets.map((dataset, index) => {
                  const typeBadge = getDatasetTypeBadge(dataset);
                  const isExpanded = expandedDatasets[dataset.id];
                  const hasResources = dataset.resources && dataset.resources.length > 0;

                  return (
                    <React.Fragment key={`${dataset.id}-${index}`}>
                      <tr style={{ cursor: hasResources ? 'pointer' : 'default' }}>
                        <td onClick={() => hasResources && toggleDatasetExpansion(dataset.id)}>
                          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem' }}>
                            {hasResources && (
                              <span style={{ marginTop: '0.125rem', color: '#64748b' }}>
                                {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                              </span>
                            )}
                            <div>
                              <div style={{ fontWeight: '500', marginBottom: '0.25rem' }}>
                                {dataset.title || dataset.name}
                              </div>
                              {dataset.title && dataset.name && dataset.title !== dataset.name && (
                                <div style={{ fontSize: '0.875rem', color: '#64748b' }}>
                                  {dataset.name}
                                </div>
                              )}
                              {dataset.notes && (
                                <div style={{
                                  fontSize: '0.875rem',
                                  color: '#64748b',
                                  marginTop: '0.25rem',
                                  maxWidth: '300px',
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                  whiteSpace: 'nowrap'
                                }}>
                                  {dataset.notes}
                                </div>
                              )}
                              <div style={{
                                fontSize: '0.75rem',
                                color: '#94a3b8',
                                marginTop: '0.25rem',
                                fontFamily: 'monospace'
                              }}>
                                ID: {dataset.id}
                              </div>
                            </div>
                          </div>
                        </td>
                        <td>
                          <span className="status-indicator status-info">
                            General
                          </span>
                        </td>
                        <td>
                          <span className="status-indicator status-success">
                            {dataset.owner_org || 'No organization'}
                          </span>
                        </td>
                        <td>
                          <button
                            onClick={() => hasResources && toggleDatasetExpansion(dataset.id)}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '0.25rem',
                              background: 'none',
                              border: 'none',
                              cursor: hasResources ? 'pointer' : 'default',
                              color: hasResources ? '#2563eb' : '#64748b',
                              padding: '0.25rem 0.5rem',
                              borderRadius: '4px'
                            }}
                            title={hasResources ? 'Click to expand resources' : 'No resources'}
                          >
                            <FileText size={14} />
                            <span>{dataset.resources?.length || 0}</span>
                          </button>
                        </td>
                        <td>
                          <div style={{ display: 'flex', gap: '0.5rem' }}>
                            <button
                              onClick={() => startEditing(dataset)}
                              className="btn btn-secondary"
                              style={{ padding: '0.375rem 0.75rem' }}
                              title="Edit dataset"
                            >
                              <Edit3 size={14} />
                              <span style={{ fontSize: '0.75rem' }}>Edit</span>
                            </button>

                            <button
                              onClick={() => handleDeleteDataset(dataset)}
                              className="btn btn-danger"
                              style={{ padding: '0.375rem 0.75rem' }}
                              title="Delete dataset"
                            >
                              <Trash2 size={14} />
                              <span style={{ fontSize: '0.75rem' }}>Delete</span>
                            </button>
                          </div>
                        </td>
                      </tr>

                      {/* Expanded Resources Row */}
                      {isExpanded && hasResources && (
                        <tr>
                          <td colSpan="5" style={{ backgroundColor: '#f8fafc', padding: '1rem' }}>
                            <div style={{ marginLeft: '1.5rem' }}>
                              <h4 style={{ marginBottom: '0.75rem', color: '#374151', fontSize: '0.9rem' }}>
                                Resources ({dataset.resources.length})
                              </h4>
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                {dataset.resources.map((resource, resIndex) => (
                                  <div
                                    key={resource.id || resIndex}
                                    style={{
                                      backgroundColor: 'white',
                                      border: '1px solid #e2e8f0',
                                      borderRadius: '8px',
                                      padding: '1rem'
                                    }}
                                  >
                                    {editingResource && editingResource.id === resource.id ? (
                                      /* Resource Edit Form */
                                      <div>
                                        <div className="grid grid-2" style={{ marginBottom: '0.75rem' }}>
                                          <div className="form-group" style={{ marginBottom: '0.5rem' }}>
                                            <label className="form-label" style={{ fontSize: '0.8rem' }}>Name</label>
                                            <input
                                              type="text"
                                              name="name"
                                              value={resourceFormData.name}
                                              onChange={handleResourceInputChange}
                                              className="form-input"
                                              style={{ padding: '0.5rem' }}
                                            />
                                          </div>
                                          <div className="form-group" style={{ marginBottom: '0.5rem' }}>
                                            <label className="form-label" style={{ fontSize: '0.8rem' }}>Format</label>
                                            <input
                                              type="text"
                                              name="format"
                                              value={resourceFormData.format}
                                              onChange={handleResourceInputChange}
                                              className="form-input"
                                              style={{ padding: '0.5rem' }}
                                            />
                                          </div>
                                        </div>
                                        <div className="form-group" style={{ marginBottom: '0.5rem' }}>
                                          <label className="form-label" style={{ fontSize: '0.8rem' }}>URL</label>
                                          <input
                                            type="text"
                                            name="url"
                                            value={resourceFormData.url}
                                            onChange={handleResourceInputChange}
                                            className="form-input"
                                            style={{ padding: '0.5rem' }}
                                          />
                                        </div>
                                        <div className="form-group" style={{ marginBottom: '0.75rem' }}>
                                          <label className="form-label" style={{ fontSize: '0.8rem' }}>Description</label>
                                          <textarea
                                            name="description"
                                            value={resourceFormData.description}
                                            onChange={handleResourceInputChange}
                                            className="form-input"
                                            style={{ padding: '0.5rem', minHeight: '60px' }}
                                          />
                                        </div>
                                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                                          <button
                                            onClick={handleSaveResource}
                                            className="btn btn-primary"
                                            style={{ padding: '0.375rem 0.75rem' }}
                                          >
                                            <Save size={14} />
                                            <span style={{ fontSize: '0.75rem' }}>Save</span>
                                          </button>
                                          <button
                                            onClick={cancelResourceEdit}
                                            className="btn btn-secondary"
                                            style={{ padding: '0.375rem 0.75rem' }}
                                          >
                                            <X size={14} />
                                            <span style={{ fontSize: '0.75rem' }}>Cancel</span>
                                          </button>
                                        </div>
                                      </div>
                                    ) : (
                                      /* Resource Display */
                                      <div>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                          <div style={{ flex: 1 }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                                              <Link size={14} style={{ color: '#64748b' }} />
                                              <span style={{ fontWeight: '500' }}>{resource.name || 'Unnamed Resource'}</span>
                                              {resource.format && (
                                                <span className="status-indicator status-info" style={{ fontSize: '0.7rem', padding: '0.125rem 0.375rem' }}>
                                                  {resource.format}
                                                </span>
                                              )}
                                            </div>
                                            {resource.description && (
                                              <p style={{ fontSize: '0.875rem', color: '#64748b', margin: '0.25rem 0' }}>
                                                {resource.description}
                                              </p>
                                            )}
                                            {resource.url && (
                                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.5rem' }}>
                                                <a
                                                  href={resource.url}
                                                  target="_blank"
                                                  rel="noopener noreferrer"
                                                  style={{
                                                    fontSize: '0.8rem',
                                                    color: '#2563eb',
                                                    textDecoration: 'none',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '0.25rem'
                                                  }}
                                                >
                                                  <ExternalLink size={12} />
                                                  {resource.url.length > 60 ? resource.url.substring(0, 60) + '...' : resource.url}
                                                </a>
                                              </div>
                                            )}
                                            <div style={{ fontSize: '0.7rem', color: '#94a3b8', marginTop: '0.25rem', fontFamily: 'monospace' }}>
                                              ID: {resource.id}
                                            </div>
                                          </div>
                                          <div style={{ display: 'flex', gap: '0.5rem' }}>
                                            <button
                                              onClick={() => startEditingResource(resource, dataset.id)}
                                              className="btn btn-secondary"
                                              style={{ padding: '0.25rem 0.5rem' }}
                                              title="Edit resource"
                                            >
                                              <Edit3 size={12} />
                                            </button>
                                            <button
                                              onClick={() => handleDeleteResource(resource)}
                                              className="btn btn-danger"
                                              style={{ padding: '0.25rem 0.5rem' }}
                                              title="Delete resource"
                                            >
                                              <Trash2 size={12} />
                                            </button>
                                          </div>
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                ))}
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
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

export default DatasetManagement;