import React, { useState, useEffect } from 'react';
import { Building2, Plus, Trash2, Search, AlertCircle } from 'lucide-react';
import { organizationsAPI } from '../services/api';

/**
 * Organizations page component for managing organizations
 * Allows creating, listing, and deleting organizations
 */
const Organizations = () => {
  const [organizations, setOrganizations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedServer, setSelectedServer] = useState('global');

  // Form state for creating new organization
  const [formData, setFormData] = useState({
    name: '',
    title: '',
    description: ''
  });

  /**
   * Fetch organizations list on component mount and when server changes
   */
  useEffect(() => {
    fetchOrganizations();
  }, [selectedServer]);

  /**
   * Fetch organizations from the API
   */
  const fetchOrganizations = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await organizationsAPI.list({
        server: selectedServer,
        name: searchTerm || undefined
      });
      
      setOrganizations(response.data || []);
    } catch (err) {
      console.error('Error fetching organizations:', err);
      setError('Failed to load organizations: ' + 
        (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

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
   * Handle form submission for creating organization
   */
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      setError(null);
      setSuccess(null);
      
      await organizationsAPI.create(formData, 'local');
      
      setSuccess('Organization created successfully!');
      setFormData({ name: '', title: '', description: '' });
      setShowCreateForm(false);
      
      // Refresh the list if viewing local server
      if (selectedServer === 'local') {
        fetchOrganizations();
      }
    } catch (err) {
      console.error('Error creating organization:', err);
      setError('Failed to create organization: ' + 
        (err.response?.data?.detail || err.message));
    }
  };

  /**
   * Handle organization deletion
   */
  const handleDelete = async (orgName) => {
    if (!window.confirm(`Are you sure you want to delete organization "${orgName}"? This will also delete all associated datasets and resources.`)) {
      return;
    }

    try {
      setError(null);
      setSuccess(null);
      
      await organizationsAPI.delete(orgName, 'local');
      
      setSuccess(`Organization "${orgName}" deleted successfully!`);
      
      // Refresh the list
      fetchOrganizations();
    } catch (err) {
      console.error('Error deleting organization:', err);
      setError('Failed to delete organization: ' + 
        (err.response?.data?.detail || err.message));
    }
  };

  /**
   * Handle search
   */
  const handleSearch = (e) => {
    e.preventDefault();
    fetchOrganizations();
  };

  return (
    <div className="organizations-page">
      {/* Page Header */}
      <div className="page-header">
        <h1 className="page-title">
          <Building2 size={32} style={{ marginRight: '0.5rem' }} />
          Organizations
        </h1>
        <p className="page-subtitle">
          Manage organizations in your CKAN instance
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
          <button
            onClick={() => setShowCreateForm(!showCreateForm)}
            className="btn btn-primary"
          >
            <Plus size={16} />
            Create Organization
          </button>
        </div>

        {/* Server Selection */}
        <div className="form-group">
          <label className="form-label">Server</label>
          <select
            value={selectedServer}
            onChange={(e) => setSelectedServer(e.target.value)}
            className="form-select"
          >
            <option value="global">Global</option>
            <option value="local">Local</option>
            <option value="pre_ckan">Pre-CKAN</option>
          </select>
        </div>

        {/* Search */}
        <form onSubmit={handleSearch} style={{ display: 'flex', gap: '1rem' }}>
          <div className="form-group" style={{ flex: 1, marginBottom: 0 }}>
            <input
              type="text"
              placeholder="Search organizations by name..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="form-input"
            />
          </div>
          <button type="submit" className="btn btn-secondary">
            <Search size={16} />
            Search
          </button>
        </form>
      </div>

      {/* Create Organization Form */}
      {showCreateForm && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Create New Organization</h3>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label">Name *</label>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleInputChange}
                className="form-input"
                placeholder="organization_name"
                required
              />
              <small style={{ color: '#64748b' }}>
                Unique identifier (lowercase, no spaces)
              </small>
            </div>

            <div className="form-group">
              <label className="form-label">Title *</label>
              <input
                type="text"
                name="title"
                value={formData.title}
                onChange={handleInputChange}
                className="form-input"
                placeholder="Organization Title"
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Description</label>
              <textarea
                name="description"
                value={formData.description}
                onChange={handleInputChange}
                className="form-input form-textarea"
                placeholder="Organization description..."
              />
            </div>

            <div style={{ display: 'flex', gap: '1rem' }}>
              <button type="submit" className="btn btn-primary">
                Create Organization
              </button>
              <button
                type="button"
                onClick={() => setShowCreateForm(false)}
                className="btn btn-secondary"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Organizations List */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            Organizations ({organizations.length})
          </h3>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: '2rem' }}>
            <div className="loading-spinner" style={{ margin: '0 auto' }}></div>
            <p style={{ marginTop: '1rem' }}>Loading organizations...</p>
          </div>
        ) : organizations.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: '#64748b' }}>
            <Building2 size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
            <p>No organizations found</p>
            {searchTerm && (
              <p>Try adjusting your search term or check a different server</p>
            )}
          </div>
        ) : (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Server</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {organizations.map((org, index) => (
                  <tr key={`${org}-${index}`}>
                    <td>
                      <div>
                        <div style={{ fontWeight: '500' }}>{org}</div>
                      </div>
                    </td>
                    <td>
                      <span className="status-indicator status-success">
                        {selectedServer}
                      </span>
                    </td>
                    <td>
                      {selectedServer === 'local' && (
                        <button
                          onClick={() => handleDelete(org)}
                          className="btn btn-danger"
                          style={{ padding: '0.5rem' }}
                          title="Delete organization"
                        >
                          <Trash2 size={16} />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default Organizations;