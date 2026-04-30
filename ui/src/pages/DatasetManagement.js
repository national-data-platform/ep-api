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
  Link,
  Clock,
  Home
} from 'lucide-react';
import { organizationsAPI, searchAPI, generalDatasetAPI, datasetAPI, resourcesAPI } from '../services/api';

// Extract a human-readable message from an axios error so we never display
// the meaningless string "[object Object]" when the backend returns a
// structured detail payload (e.g. {"error": "...", "detail": "..."}).
const formatApiError = (err) => {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object') {
    return detail.detail || detail.error || JSON.stringify(detail);
  }
  return err?.message || 'Unknown error';
};

// Map a dataset's extras.status to a small icon. The backend currently sets
// extras.status="submitted" after a successful publish to PRE-CKAN; datasets
// that have never been published have no status entry and are local-only.
// Unknown values render a defensive AlertCircle so they are still visible.
const renderDatasetStatusIcon = (status) => {
  let Icon;
  let color;
  let label;
  if (status === 'submitted') {
    Icon = Clock;
    color = '#f59e0b';
    label = 'Submitted';
  } else if (!status) {
    Icon = Home;
    color = '#94a3b8';
    label = 'Local only';
  } else {
    Icon = AlertCircle;
    color = '#64748b';
    label = status;
  }
  return (
    <span title={label} aria-label={`Status: ${label}`} style={{ display: 'inline-flex' }}>
      <Icon size={16} color={color} />
    </span>
  );
};

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
  const [warning, setWarning] = useState(null);
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

  // Resources editor: 'fields' for guided cards, 'json' for raw JSON array
  const [resourcesMode, setResourcesMode] = useState('fields');
  const [resourcesItems, setResourcesItems] = useState([]);
  const [resourcesModeError, setResourcesModeError] = useState(null);

  // The guided editor exposes the canonical resource fields. Anything else
  // present on a loaded resource (mimetype, size, server-managed ids, …) is
  // kept untouched in `_extra` so a fields-mode round-trip never drops data.
  const SIMPLE_RESOURCE_FIELDS = ['name', 'url', 'format', 'description'];

  const emptyResourceItem = () => ({
    name: '',
    url: '',
    format: '',
    description: '',
    _extra: {}
  });

  const resourceToItem = (resource) => {
    const item = emptyResourceItem();
    if (!resource || typeof resource !== 'object') return item;
    for (const [key, value] of Object.entries(resource)) {
      if (SIMPLE_RESOURCE_FIELDS.includes(key)) {
        item[key] = value === null || value === undefined ? '' : String(value);
      } else {
        item._extra[key] = value;
      }
    }
    return item;
  };

  const itemToResource = (item) => {
    const out = { ...(item._extra || {}) };
    for (const f of SIMPLE_RESOURCE_FIELDS) {
      if (item[f] !== undefined && item[f] !== null && item[f] !== '') {
        out[f] = item[f];
      }
    }
    return out;
  };

  const resourcesToItems = (resources) => {
    if (!Array.isArray(resources)) return [];
    return resources.map(resourceToItem);
  };

  const itemsToResources = (items) =>
    items.map(itemToResource).filter((r) => Object.keys(r).length > 0);

  const addResourceItem = () => {
    setResourcesItems((prev) => [...prev, emptyResourceItem()]);
    setResourcesModeError(null);
  };

  const removeResourceItem = (idx) => {
    setResourcesItems((prev) => prev.filter((_, i) => i !== idx));
  };

  const updateResourceItem = (idx, field, value) => {
    setResourcesItems((prev) =>
      prev.map((r, i) => (i === idx ? { ...r, [field]: value } : r))
    );
  };

  const switchResourcesToJsonMode = () => {
    const arr = itemsToResources(resourcesItems);
    setResourcesJson(JSON.stringify(arr, null, 2));
    setResourcesMode('json');
    setResourcesModeError(null);
  };

  const switchResourcesToFieldsMode = () => {
    let parsed;
    try {
      parsed = resourcesJson.trim() === '' ? [] : JSON.parse(resourcesJson);
    } catch {
      setResourcesModeError('Cannot switch to simple fields: the JSON is invalid.');
      return;
    }
    if (!Array.isArray(parsed)) {
      setResourcesModeError(
        'Cannot switch to simple fields: resources must be a JSON array.'
      );
      return;
    }
    if (!parsed.every((r) => r && typeof r === 'object' && !Array.isArray(r))) {
      setResourcesModeError(
        'Cannot switch to simple fields: every resource must be a JSON object.'
      );
      return;
    }
    setResourcesItems(resourcesToItems(parsed));
    setResourcesMode('fields');
    setResourcesModeError(null);
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
    setResourcesMode('fields');
    setResourcesItems([]);
    setResourcesModeError(null);
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
    const resources = resourcesMode === 'fields'
      ? itemsToResources(resourcesItems)
      : parseJsonSafely(resourcesJson, []);

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
      setWarning(null);
      setLoading(true);

      const requestData = prepareFormData();
      const response = await generalDatasetAPI.create(requestData, selectedServer);

      const apiWarning = response?.data?.warning;
      if (apiWarning) {
        setWarning(`WARNING: ${apiWarning}`);
      } else {
        setSuccess('Dataset created successfully!');
      }
      resetForm();
      fetchDatasets();

    } catch (err) {
      console.error('Error creating dataset:', err);
      setError('Failed to create dataset: ' + formatApiError(err));
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
      setWarning(null);
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
    const resources = dataset.resources || [];
    setExtrasJson(JSON.stringify(extras, null, 2));
    setResourcesJson(JSON.stringify(resources, null, 2));

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

    // Resources always default to guided cards. Unknown fields are kept in
    // each item's _extra bucket so they survive the round-trip.
    setResourcesItems(resourcesToItems(resources));
    setResourcesMode('fields');
    setResourcesModeError(null);

    setShowCreateForm(true);
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
      setWarning(null);

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
      setWarning(null);

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
      setWarning(null);

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

      {warning && (
        <div className="alert alert-warning">
          <AlertCircle size={20} />
          {warning}
        </div>
      )}

      {/* Create dataset button */}
      <div style={{ marginBottom: '1rem' }}>
        <button
          onClick={() => setShowCreateForm(!showCreateForm)}
          className="btn btn-primary"
        >
          <Plus size={16} />
          {showCreateForm ? 'Cancel' : 'Create Dataset'}
        </button>
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
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
                  <label className="form-label" style={{ marginBottom: 0 }}>Extras</label>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ fontSize: '0.75rem', padding: '0.25rem 0.5rem' }}
                    onClick={extrasMode === 'fields' ? switchToJsonMode : switchToFieldsMode}
                  >
                    {extrasMode === 'fields' ? 'Advanced (JSON)' : 'Simple fields'}
                  </button>
                </div>

                {extrasMode === 'fields' ? (
                  <>
                    {extrasPairs.length === 0 ? (
                      <small style={{ color: '#64748b', display: 'block', marginBottom: '0.5rem' }}>
                        No extra metadata. Click "Add field" to add one.
                      </small>
                    ) : (
                      extrasPairs.map((pair, idx) => (
                        <div key={idx} style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' }}>
                          <input
                            type="text"
                            value={pair.key}
                            onChange={(e) => updateExtraPair(idx, 'key', e.target.value)}
                            placeholder="Key"
                            className="form-input"
                            style={{ flex: 1 }}
                          />
                          <input
                            type="text"
                            value={pair.value}
                            onChange={(e) => updateExtraPair(idx, 'value', e.target.value)}
                            placeholder="Value"
                            className="form-input"
                            style={{ flex: 1 }}
                          />
                          <button
                            type="button"
                            onClick={() => removeExtraPair(idx)}
                            className="btn btn-secondary"
                            style={{ padding: '0.5rem' }}
                            aria-label="Remove field"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      ))
                    )}
                    <button
                      type="button"
                      onClick={addExtraPair}
                      className="btn btn-secondary"
                      style={{ fontSize: '0.875rem' }}
                    >
                      <Plus size={14} />
                      Add field
                    </button>
                    <small style={{ color: '#64748b', display: 'block', marginTop: '0.5rem' }}>
                      Additional metadata as key/value pairs.
                    </small>
                  </>
                ) : (
                  <>
                    <textarea
                      value={extrasJson}
                      onChange={(e) => setExtrasJson(e.target.value)}
                      className="form-input form-textarea"
                      placeholder='{"version": "1.0", "project": "research"}'
                      style={{ fontFamily: 'monospace', fontSize: '0.875rem', minHeight: '120px' }}
                    />
                    <small style={{ color: '#64748b' }}>
                      Additional metadata as JSON. Use this for nested or non-text values.
                    </small>
                  </>
                )}

                {extrasModeError && (
                  <small style={{ color: '#dc2626', display: 'block', marginTop: '0.5rem' }}>
                    {extrasModeError}
                  </small>
                )}
              </div>

              <div className="form-group">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
                  <label className="form-label" style={{ marginBottom: 0 }}>Resources</label>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ fontSize: '0.75rem', padding: '0.25rem 0.5rem' }}
                    onClick={resourcesMode === 'fields' ? switchResourcesToJsonMode : switchResourcesToFieldsMode}
                  >
                    {resourcesMode === 'fields' ? 'Advanced (JSON)' : 'Simple fields'}
                  </button>
                </div>

                {resourcesMode === 'fields' ? (
                  <>
                    {resourcesItems.length === 0 ? (
                      <small style={{ color: '#64748b', display: 'block', marginBottom: '0.5rem' }}>
                        No resources. Click "Add resource" to attach one.
                      </small>
                    ) : (
                      resourcesItems.map((item, idx) => (
                        <div
                          key={idx}
                          style={{
                            border: '1px solid #e2e8f0',
                            borderRadius: '6px',
                            padding: '0.75rem',
                            marginBottom: '0.5rem',
                            background: '#f8fafc'
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                            <small style={{ color: '#64748b', fontWeight: 500 }}>
                              Resource {idx + 1}
                            </small>
                            <button
                              type="button"
                              onClick={() => removeResourceItem(idx)}
                              className="btn btn-secondary"
                              style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                              aria-label="Remove resource"
                            >
                              <Trash2 size={12} />
                              Remove
                            </button>
                          </div>

                          <div className="form-group" style={{ marginBottom: '0.5rem' }}>
                            <label className="form-label" style={{ fontSize: '0.8rem' }}>URL *</label>
                            <input
                              type="text"
                              value={item.url}
                              onChange={(e) => updateResourceItem(idx, 'url', e.target.value)}
                              className="form-input"
                              placeholder="http://example.com/data.csv"
                              style={{ padding: '0.5rem' }}
                            />
                          </div>

                          <div className="grid grid-2" style={{ marginBottom: '0.5rem' }}>
                            <div className="form-group" style={{ marginBottom: 0 }}>
                              <label className="form-label" style={{ fontSize: '0.8rem' }}>Name *</label>
                              <input
                                type="text"
                                value={item.name}
                                onChange={(e) => updateResourceItem(idx, 'name', e.target.value)}
                                className="form-input"
                                placeholder="main_data"
                                style={{ padding: '0.5rem' }}
                              />
                            </div>
                            <div className="form-group" style={{ marginBottom: 0 }}>
                              <label className="form-label" style={{ fontSize: '0.8rem' }}>Format</label>
                              <input
                                type="text"
                                value={item.format}
                                onChange={(e) => updateResourceItem(idx, 'format', e.target.value)}
                                className="form-input"
                                placeholder="CSV"
                                style={{ padding: '0.5rem' }}
                              />
                            </div>
                          </div>

                          <div className="form-group" style={{ marginBottom: 0 }}>
                            <label className="form-label" style={{ fontSize: '0.8rem' }}>Description</label>
                            <textarea
                              value={item.description}
                              onChange={(e) => updateResourceItem(idx, 'description', e.target.value)}
                              className="form-input"
                              placeholder="What is in this resource"
                              style={{ padding: '0.5rem', minHeight: '50px' }}
                            />
                          </div>
                        </div>
                      ))
                    )}
                    <button
                      type="button"
                      onClick={addResourceItem}
                      className="btn btn-secondary"
                      style={{ fontSize: '0.875rem' }}
                    >
                      <Plus size={14} />
                      Add resource
                    </button>
                    <small style={{ color: '#64748b', display: 'block', marginTop: '0.5rem' }}>
                      Each resource is a downloadable file or link attached to the dataset.
                    </small>
                  </>
                ) : (
                  <>
                    <textarea
                      value={resourcesJson}
                      onChange={(e) => setResourcesJson(e.target.value)}
                      className="form-input form-textarea"
                      placeholder='[{"url": "http://example.com/data.csv", "name": "main_data", "format": "CSV"}]'
                      style={{ fontFamily: 'monospace', fontSize: '0.875rem', minHeight: '120px' }}
                    />
                    <small style={{ color: '#64748b' }}>
                      List of resources as JSON array. Use this to set fields the simple editor does not expose (mimetype, size, …).
                    </small>
                  </>
                )}

                {resourcesModeError && (
                  <small style={{ color: '#dc2626', display: 'block', marginTop: '0.5rem' }}>
                    {resourcesModeError}
                  </small>
                )}
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
                  <th>Organization</th>
                  <th>Status</th>
                  <th>Resources</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {datasets.map((dataset, index) => {
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
                          <span className="status-indicator status-success">
                            {dataset.owner_org || 'No organization'}
                          </span>
                        </td>
                        <td>
                          {renderDatasetStatusIcon(dataset.extras?.status)}
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