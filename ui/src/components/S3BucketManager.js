import React, { useState, useEffect, useCallback } from 'react';
import { 
  FolderOpen, 
  Plus, 
  Trash2, 
  RefreshCw, 
  Calendar,
  AlertCircle,
  Info,
  Search,
  Upload,
  FolderPlus
} from 'lucide-react';
import { s3BucketAPI } from '../services/api';

const S3BucketManager = ({ onBucketSelect, selectedBucket }) => {
  const [buckets, setBuckets] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [searchFilter, setSearchFilter] = useState('');

  const [formData, setFormData] = useState({
    name: '',
    region: 'us-east-1'
  });

  const fetchBuckets = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await s3BucketAPI.list();
      setBuckets(response.data.buckets || []);
      
    } catch (err) {
      console.error('Error fetching buckets:', err);
      setError('Failed to load S3 buckets: ' + 
        (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBuckets();
  }, [fetchBuckets]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const resetForm = () => {
    setFormData({
      name: '',
      region: 'us-east-1'
    });
    setShowCreateForm(false);
  };

  const handleCreateBucket = async (e) => {
    e.preventDefault();
    
    try {
      setError(null);
      setSuccess(null);
      setLoading(true);

      await s3BucketAPI.create(formData);
      
      setSuccess(`Bucket "${formData.name}" created successfully!`);
      resetForm();
      fetchBuckets();
      
    } catch (err) {
      console.error('Error creating bucket:', err);
      setError('Failed to create bucket: ' + 
        (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteBucket = async (bucket) => {
    if (!window.confirm(
      `Are you sure you want to delete bucket "${bucket.name}"? This action cannot be undone and the bucket must be empty.`
    )) {
      return;
    }

    try {
      setError(null);
      setSuccess(null);
      
      await s3BucketAPI.delete(bucket.name);
      
      setSuccess(`Bucket "${bucket.name}" deleted successfully!`);
      
      // If this was the selected bucket, clear selection
      if (selectedBucket === bucket.name) {
        onBucketSelect(null);
      }
      
      fetchBuckets();
      
    } catch (err) {
      console.error('Error deleting bucket:', err);
      setError('Failed to delete bucket: ' + 
        (err.response?.data?.detail || err.message));
    }
  };

  // Filter buckets based on search
  const filteredBuckets = buckets.filter(bucket =>
    bucket.name.toLowerCase().includes(searchFilter.toLowerCase())
  );

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown';
    try {
      return new Date(dateString).toLocaleDateString();
    } catch {
      return 'Invalid date';
    }
  };

  return (
    <div className="s3-bucket-manager">
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

      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            <FolderOpen size={20} />
            S3 Buckets ({filteredBuckets.length})
          </h3>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <div style={{ position: 'relative' }}>
              <Search size={16} style={{ 
                position: 'absolute', 
                left: '0.75rem', 
                top: '50%', 
                transform: 'translateY(-50%)',
                color: '#64748b'
              }} />
              <input
                type="text"
                placeholder="Search buckets..."
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                style={{
                  paddingLeft: '2.5rem',
                  padding: '0.5rem 0.75rem',
                  border: '1px solid #e2e8f0',
                  borderRadius: '6px',
                  fontSize: '0.875rem',
                  width: '200px'
                }}
              />
            </div>
            <button
              onClick={fetchBuckets}
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
              {showCreateForm ? 'Cancel' : 'Create Bucket'}
            </button>
          </div>
        </div>

        {/* Create Bucket Form */}
        {showCreateForm && (
          <div style={{ 
            borderTop: '1px solid #e2e8f0', 
            padding: '1rem',
            backgroundColor: '#f8fafc'
          }}>
            <form onSubmit={handleCreateBucket}>
              <div className="grid grid-2">
                <div className="form-group">
                  <label className="form-label">Bucket Name *</label>
                  <input
                    type="text"
                    name="name"
                    value={formData.name}
                    onChange={handleInputChange}
                    className="form-input"
                    placeholder="my-unique-bucket-name"
                    required
                    pattern="^[a-z0-9.-]*$"
                    title="Bucket names must be lowercase letters, numbers, dots, and hyphens only"
                  />
                  <small style={{ color: '#64748b' }}>
                    Must be globally unique, lowercase, 3-63 characters
                  </small>
                </div>

                <div className="form-group">
                  <label className="form-label">Region</label>
                  <select
                    name="region"
                    value={formData.region}
                    onChange={handleInputChange}
                    className="form-select"
                  >
                    <option value="us-east-1">US East (N. Virginia)</option>
                    <option value="us-east-2">US East (Ohio)</option>
                    <option value="us-west-1">US West (N. California)</option>
                    <option value="us-west-2">US West (Oregon)</option>
                    <option value="eu-west-1">Europe (Ireland)</option>
                    <option value="eu-central-1">Europe (Frankfurt)</option>
                    <option value="ap-southeast-1">Asia Pacific (Singapore)</option>
                    <option value="ap-northeast-1">Asia Pacific (Tokyo)</option>
                  </select>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
                <button 
                  type="submit" 
                  className="btn btn-primary"
                  disabled={loading}
                >
                  {loading ? (
                    <>
                      <div className="loading-spinner" />
                      Creating...
                    </>
                  ) : (
                    <>
                      <FolderPlus size={16} />
                      Create Bucket
                    </>
                  )}
                </button>
                <button
                  type="button"
                  onClick={resetForm}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Buckets List */}
        {loading && !showCreateForm ? (
          <div style={{ textAlign: 'center', padding: '2rem' }}>
            <div className="loading-spinner" style={{ margin: '0 auto' }}></div>
            <p style={{ marginTop: '1rem' }}>Loading S3 buckets...</p>
          </div>
        ) : filteredBuckets.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: '#64748b' }}>
            {searchFilter ? (
              <>
                <Search size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
                <p>No buckets found matching "{searchFilter}"</p>
                <button 
                  onClick={() => setSearchFilter('')}
                  className="btn btn-secondary"
                  style={{ marginTop: '0.5rem' }}
                >
                  Clear search
                </button>
              </>
            ) : (
              <>
                <FolderOpen size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
                <p>No S3 buckets found</p>
                <p>Create your first bucket using the button above</p>
              </>
            )}
          </div>
        ) : (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Bucket Name</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredBuckets.map((bucket) => (
                  <tr 
                    key={bucket.name}
                    style={{
                      backgroundColor: selectedBucket === bucket.name ? '#eff6ff' : 'transparent',
                      cursor: 'pointer'
                    }}
                    onClick={() => onBucketSelect(bucket.name)}
                  >
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <FolderOpen 
                          size={18} 
                          style={{ 
                            color: selectedBucket === bucket.name ? '#2563eb' : '#64748b' 
                          }} 
                        />
                        <div>
                          <div style={{ 
                            fontWeight: '500',
                            color: selectedBucket === bucket.name ? '#2563eb' : '#374151'
                          }}>
                            {bucket.name}
                          </div>
                          {selectedBucket === bucket.name && (
                            <div style={{ 
                              fontSize: '0.75rem', 
                              color: '#2563eb',
                              marginTop: '0.125rem'
                            }}>
                              ✓ Selected
                            </div>
                          )}
                        </div>
                      </div>
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                        <Calendar size={14} style={{ color: '#64748b' }} />
                        <span style={{ fontSize: '0.875rem', color: '#64748b' }}>
                          {formatDate(bucket.creation_date)}
                        </span>
                      </div>
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onBucketSelect(bucket.name);
                          }}
                          className={`btn ${selectedBucket === bucket.name ? 'btn-primary' : 'btn-secondary'}`}
                          style={{ padding: '0.375rem 0.75rem' }}
                          title={selectedBucket === bucket.name ? 'Currently selected' : 'Select bucket'}
                        >
                          {selectedBucket === bucket.name ? (
                            <>
                              <Info size={14} />
                              <span style={{ fontSize: '0.75rem' }}>Selected</span>
                            </>
                          ) : (
                            <>
                              <Upload size={14} />
                              <span style={{ fontSize: '0.75rem' }}>Select</span>
                            </>
                          )}
                        </button>
                        
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteBucket(bucket);
                          }}
                          className="btn btn-danger"
                          style={{ padding: '0.375rem 0.75rem' }}
                          title="Delete bucket"
                        >
                          <Trash2 size={14} />
                          <span style={{ fontSize: '0.75rem' }}>Delete</span>
                        </button>
                      </div>
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

export default S3BucketManager;