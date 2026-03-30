import React, { useState, useEffect, useCallback } from 'react';
import { 
  Radio, 
  Plus, 
  AlertCircle, 
  Edit3,
  Save,
  X,
  Trash2,
  RefreshCw,
  Database
} from 'lucide-react';
import { kafkaAPI, organizationsAPI, searchAPI, resourcesAPI } from '../services/api';

/**
 * Kafka Topics page component for managing Kafka data sources
 * Allows creating, listing, editing, and deleting Kafka topic datasets
 */
const KafkaTopics = () => {
  const [kafkaTopics, setKafkaTopics] = useState([]);
  const [organizations, setOrganizations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingTopic, setEditingTopic] = useState(null);
  const [selectedServer] = useState('local'); // Fixed to local for consistency

  // Form state for creating/editing Kafka topic
  const [formData, setFormData] = useState({
    dataset_name: '',
    dataset_title: '',
    owner_org: '',
    kafka_topic: '',
    kafka_host: '',
    kafka_port: '',
    dataset_description: '',
    extras: {},
    mapping: {},
    processing: {}
  });

  // JSON editor states for complex fields
  const [extrasJson, setExtrasJson] = useState('{}');
  const [mappingJson, setMappingJson] = useState('{}');
  const [processingJson, setProcessingJson] = useState('{}');

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
   * Fetch all Kafka topics (filtered from all datasets)
   */
  const fetchKafkaTopics = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Use search to get all datasets, then filter for Kafka topics
      const response = await searchAPI.searchByTerms([''], null, selectedServer);
      
      // Filter to show only Kafka topics
      const filteredTopics = (response.data || []).filter(dataset => {
        const extras = dataset.extras || {};
        
        // Include if it has Kafka-specific metadata
        // Check for both old format (kafka_*) and new format (host, port, topic)
        return (
          extras.kafka_topic || extras.kafka_host || extras.kafka_port || // Old format
          extras.topic || extras.host || extras.port || // New format
          // Also check if any resource has format "kafka"
          (dataset.resources && dataset.resources.some(resource => 
            resource.format === 'kafka'
          ))
        );
      });
      
      console.log('All datasets:', response.data); // Debug
      console.log('Filtered Kafka topics:', filteredTopics); // Debug
      
      setKafkaTopics(filteredTopics);
      
    } catch (err) {
      console.error('Error fetching Kafka topics:', err);
      setError('Failed to load Kafka topics: ' + 
        (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  }, [selectedServer]);

  /**
   * Fetch organizations and Kafka topics on component mount
   */
  useEffect(() => {
    fetchOrganizations();
    fetchKafkaTopics();
  }, [fetchOrganizations, fetchKafkaTopics]);

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
      dataset_name: '',
      dataset_title: '',
      owner_org: '',
      kafka_topic: '',
      kafka_host: '',
      kafka_port: '',
      dataset_description: '',
      extras: {},
      mapping: {},
      processing: {}
    });
    setExtrasJson('{}');
    setMappingJson('{}');
    setProcessingJson('{}');
    setEditingTopic(null);
    setShowCreateForm(false);
  };

  /**
   * Prepare form data for submission
   */
  const prepareFormData = () => {
    // Parse JSON fields
    const extras = parseJsonSafely(extrasJson, {});
    const mapping = parseJsonSafely(mappingJson, {});
    const processing = parseJsonSafely(processingJson, {});

    // Prepare data
    const requestData = {
      ...formData,
      extras: Object.keys(extras).length > 0 ? extras : undefined,
      mapping: Object.keys(mapping).length > 0 ? mapping : undefined,
      processing: Object.keys(processing).length > 0 ? processing : undefined
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
   * Handle form submission for creating Kafka topic
   */
  const handleCreate = async (e) => {
    e.preventDefault();
    
    try {
      setError(null);
      setSuccess(null);
      setLoading(true);

      const requestData = prepareFormData();
      await kafkaAPI.create(requestData, selectedServer);
      
      setSuccess('Kafka topic dataset created successfully!');
      resetForm();
      fetchKafkaTopics();
      
    } catch (err) {
      console.error('Error creating Kafka topic:', err);
      setError('Failed to create Kafka topic: ' + 
        (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  /**
   * Handle form submission for updating Kafka topic
   */
  const handleUpdate = async (e) => {
    e.preventDefault();
    
    try {
      setError(null);
      setSuccess(null);
      setLoading(true);

      const requestData = prepareFormData();
      await kafkaAPI.update(editingTopic.id, requestData, selectedServer);
      
      setSuccess('Kafka topic updated successfully!');
      resetForm();
      fetchKafkaTopics();
      
    } catch (err) {
      console.error('Error updating Kafka topic:', err);
      setError('Failed to update Kafka topic: ' + 
        (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  /**
   * Start editing a Kafka topic
   * FIXED: Properly separate Kafka-specific fields from general extras
   */
  const startEditing = (topic) => {
    setEditingTopic(topic);
    const extras = topic.extras || {};
    
    // Extract Kafka-specific fields from extras
    const kafkaFields = {
      kafka_topic: extras.kafka_topic || extras.topic || '',
      kafka_host: extras.kafka_host || extras.host || '',
      kafka_port: extras.kafka_port || extras.port || ''
    };
    
    // Create a clean extras object without the reserved Kafka fields
    const cleanExtras = { ...extras };
    
    // Remove reserved Kafka fields from extras
    const reservedKafkaFields = [
      'kafka_topic', 'topic',
      'kafka_host', 'host', 
      'kafka_port', 'port'
    ];
    
    reservedKafkaFields.forEach(field => {
      delete cleanExtras[field];
    });
    
    // Also extract mapping and processing from extras if they exist
    const mapping = cleanExtras.mapping || {};
    const processing = cleanExtras.processing || {};
    
    // Remove mapping and processing from cleanExtras since they have their own fields
    delete cleanExtras.mapping;
    delete cleanExtras.processing;
    
    setFormData({
      dataset_name: topic.name || '',
      dataset_title: topic.title || '',
      owner_org: topic.owner_org || '',
      kafka_topic: kafkaFields.kafka_topic,
      kafka_host: kafkaFields.kafka_host,
      kafka_port: kafkaFields.kafka_port,
      dataset_description: topic.notes || '',
      extras: cleanExtras,
      mapping: mapping,
      processing: processing
    });
    
    // Set JSON fields with clean data
    setExtrasJson(JSON.stringify(cleanExtras, null, 2));
    setMappingJson(JSON.stringify(mapping, null, 2));
    setProcessingJson(JSON.stringify(processing, null, 2));
    setShowCreateForm(true);
  };

  /**
   * Handle Kafka topic deletion
   */
  const handleDeleteTopic = async (topic) => {
    const displayName = topic.title || topic.name || 'Unnamed Topic';
    
    if (!window.confirm(
      `Are you sure you want to delete Kafka topic "${displayName}"? This will also delete all associated resources. This action cannot be undone.`
    )) {
      return;
    }

    try {
      setError(null);
      setSuccess(null);
      
      // Debug: Log the topic being deleted
      console.log('Attempting to delete Kafka topic with ID:', topic.id);
      console.log('Using endpoint: DELETE /resource?resource_id=' + topic.id + '&server=local');
      
      // Use the resource deletion endpoint since datasets are resources in CKAN
      await resourcesAPI.deleteById(topic.id, 'local');
      
      setSuccess(`Kafka topic "${displayName}" deleted successfully!`);
      
      // Refresh the topics list
      fetchKafkaTopics();
      
    } catch (err) {
      console.error('Error deleting Kafka topic:', err);
      console.error('Full error object:', err);
      console.error('Error response:', err.response);
      
      let errorMessage = 'Failed to delete Kafka topic: ';
      
      if (err.response?.status === 404) {
        errorMessage += `Topic "${displayName}" not found. It may have been already deleted.`;
      } else if (err.response?.status === 405) {
        errorMessage += 'Topic deletion method not allowed.';
      } else if (err.response?.status === 401) {
        errorMessage += 'Authentication required. Please login again.';
      } else if (err.response?.status === 403) {
        errorMessage += 'You do not have permission to delete this topic.';
      } else {
        errorMessage += (err.response?.data?.detail || err.message);
      }
      
      setError(errorMessage);
    }
  };

  /**
   * Get connection status badge
   */
  const getConnectionStatus = (topic) => {
    const extras = topic.extras || {};
    // Check both old format (kafka_*) and new format (host, port, topic)
    const hasHost = extras.kafka_host || extras.host;
    const hasPort = extras.kafka_port || extras.port;
    const hasTopic = extras.kafka_topic || extras.topic;
    
    if (hasHost && hasPort && hasTopic) {
      return { status: 'Connected', color: 'status-success' };
    }
    return { status: 'Incomplete', color: 'status-warning' };
  };

  return (
    <div className="kafka-topics-page">
      {/* Page Header */}
      <div className="page-header">
        <h1 className="page-title">
          <Radio size={32} style={{ marginRight: '0.5rem' }} />
          Kafka Topics
        </h1>
        <p className="page-subtitle">
          Register and manage Kafka topics as datasets in your CKAN instance
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
              onClick={fetchKafkaTopics}
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
              {showCreateForm ? 'Cancel' : 'Create Kafka Topic'}
            </button>
          </div>
        </div>
      </div>

      {/* Create/Edit Kafka Topic Form */}
      {showCreateForm && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">
              {editingTopic ? (
                <>
                  <Edit3 size={20} />
                  Edit Kafka Topic: {editingTopic.title}
                </>
              ) : (
                <>
                  <Plus size={20} />
                  Create New Kafka Topic Dataset
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

          <form onSubmit={editingTopic ? handleUpdate : handleCreate}>
            {/* Basic Information */}
            <div className="grid grid-2">
              <div className="form-group">
                <label className="form-label">Dataset Name *</label>
                <input
                  type="text"
                  name="dataset_name"
                  value={formData.dataset_name}
                  onChange={handleInputChange}
                  className="form-input"
                  placeholder="kafka_topic_example"
                  required
                  disabled={editingTopic} // Cannot change name when editing
                />
                <small style={{ color: '#64748b' }}>
                  Unique identifier for the dataset
                </small>
              </div>

              <div className="form-group">
                <label className="form-label">Dataset Title *</label>
                <input
                  type="text"
                  name="dataset_title"
                  value={formData.dataset_title}
                  onChange={handleInputChange}
                  className="form-input"
                  placeholder="Kafka Topic Example"
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

            {/* Kafka Configuration */}
            <div className="grid grid-3">
              <div className="form-group">
                <label className="form-label">Kafka Topic *</label>
                <input
                  type="text"
                  name="kafka_topic"
                  value={formData.kafka_topic}
                  onChange={handleInputChange}
                  className="form-input"
                  placeholder="example_topic"
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Kafka Host *</label>
                <input
                  type="text"
                  name="kafka_host"
                  value={formData.kafka_host}
                  onChange={handleInputChange}
                  className="form-input"
                  placeholder="localhost"
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Kafka Port *</label>
                <input
                  type="text"
                  name="kafka_port"
                  value={formData.kafka_port}
                  onChange={handleInputChange}
                  className="form-input"
                  placeholder="9092"
                  required
                />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Dataset Description</label>
              <textarea
                name="dataset_description"
                value={formData.dataset_description}
                onChange={handleInputChange}
                className="form-input form-textarea"
                placeholder="Description of the Kafka topic dataset..."
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
                  Additional metadata as JSON (excluding Kafka fields)
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
                  placeholder='{"data_key": "data", "info_key": "info"}'
                  style={{ fontFamily: 'monospace', fontSize: '0.875rem' }}
                />
                <small style={{ color: '#64748b' }}>
                  Processing configuration
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
                  {editingTopic ? 'Updating...' : 'Creating...'}
                </>
              ) : (
                <>
                  <Save size={16} />
                  {editingTopic ? 'Update Kafka Topic' : 'Create Kafka Topic Dataset'}
                </>
              )}
            </button>
          </form>
        </div>
      )}

      {/* Kafka Topics List */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            Kafka Topics ({kafkaTopics.length})
          </h3>
        </div>

        {loading && !showCreateForm ? (
          <div style={{ textAlign: 'center', padding: '2rem' }}>
            <div className="loading-spinner" style={{ margin: '0 auto' }}></div>
            <p style={{ marginTop: '1rem' }}>Loading Kafka topics...</p>
          </div>
        ) : kafkaTopics.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: '#64748b' }}>
            <Radio size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
            <p>No Kafka topics found</p>
            <p>Create your first Kafka topic using the form above</p>
          </div>
        ) : (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Topic</th>
                  <th>Kafka Details</th>
                  <th>Organization</th>
                  <th>Status</th>
                  <th>Resources</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {kafkaTopics.map((topic, index) => {
                  const extras = topic.extras || {};
                  const connectionStatus = getConnectionStatus(topic);
                  
                  return (
                    <tr key={`${topic.id}-${index}`}>
                      <td>
                        <div>
                          <div style={{ fontWeight: '500', marginBottom: '0.25rem' }}>
                            {topic.title || topic.name}
                          </div>
                          {topic.title && topic.name && topic.title !== topic.name && (
                            <div style={{ fontSize: '0.875rem', color: '#64748b' }}>
                              {topic.name}
                            </div>
                          )}
                          {topic.notes && (
                            <div style={{ 
                              fontSize: '0.875rem', 
                              color: '#64748b',
                              marginTop: '0.25rem',
                              maxWidth: '200px',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap'
                            }}>
                              {topic.notes}
                            </div>
                          )}
                          <div style={{ 
                            fontSize: '0.75rem', 
                            color: '#94a3b8',
                            marginTop: '0.25rem',
                            fontFamily: 'monospace'
                          }}>
                            ID: {topic.id}
                          </div>
                        </div>
                      </td>
                      <td>
                        <div>
                          <div style={{ fontSize: '0.875rem', fontWeight: '500' }}>
                            Topic: {extras.topic || extras.kafka_topic || 'N/A'}
                          </div>
                          <div style={{ fontSize: '0.875rem', color: '#64748b' }}>
                            Host: {extras.host || extras.kafka_host || 'N/A'}
                          </div>
                          <div style={{ fontSize: '0.875rem', color: '#64748b' }}>
                            Port: {extras.port || extras.kafka_port || 'N/A'}
                          </div>
                        </div>
                      </td>
                      <td>
                        <span className="status-indicator status-success">
                          {topic.owner_org || 'No organization'}
                        </span>
                      </td>
                      <td>
                        <span className={`status-indicator ${connectionStatus.color}`}>
                          {connectionStatus.status}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                          <Database size={14} />
                          <span>{topic.resources?.length || 0}</span>
                        </div>
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                          <button
                            onClick={() => startEditing(topic)}
                            className="btn btn-secondary"
                            style={{ padding: '0.375rem 0.75rem' }}
                            title="Edit Kafka topic"
                          >
                            <Edit3 size={14} />
                            <span style={{ fontSize: '0.75rem' }}>Edit</span>
                          </button>
                          
                          <button
                            onClick={() => handleDeleteTopic(topic)}
                            className="btn btn-danger"
                            style={{ padding: '0.375rem 0.75rem' }}
                            title="Delete Kafka topic"
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

export default KafkaTopics;