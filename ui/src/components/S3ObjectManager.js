import React, { useState, useEffect, useCallback, useRef } from 'react';
import { 
  File, 
  Upload, 
  Download, 
  Trash2, 
  RefreshCw, 
  Calendar,
  HardDrive,
  AlertCircle,
  Search,
  FolderOpen,
  Eye,
  Link,
  FileText,
  Image,
  Video,
  Music,
  Archive,
  Code
} from 'lucide-react';
import { s3ObjectAPI, s3PresignedAPI } from '../services/api';

const S3ObjectManager = ({ selectedBucket }) => {
  const [objects, setObjects] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [searchPrefix, setSearchPrefix] = useState('');
  const [selectedObject, setSelectedObject] = useState(null);
  const [showMetadata, setShowMetadata] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  
  const fileInputRef = useRef(null);
  const dragRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);

  const fetchObjects = useCallback(async (prefix = null) => {
    if (!selectedBucket) return;
    
    try {
      setLoading(true);
      setError(null);
      
      const response = await s3ObjectAPI.list(selectedBucket, prefix);
      setObjects(response.data.objects || []);
      
    } catch (err) {
      console.error('Error fetching objects:', err);
      setError('Failed to load objects: ' + 
        (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  }, [selectedBucket]);

  useEffect(() => {
    if (selectedBucket) {
      fetchObjects(searchPrefix || null);
    } else {
      setObjects([]);
    }
  }, [selectedBucket, fetchObjects]);

  const handleSearch = () => {
    fetchObjects(searchPrefix || null);
  };

  const handleFileSelect = (event) => {
    const files = Array.from(event.target.files);
    files.forEach(file => uploadFile(file));
  };

  const uploadFile = async (file, customKey = null) => {
    if (!selectedBucket) {
      setError('Please select a bucket first');
      return;
    }

    try {
      setUploading(true);
      setUploadProgress(0);
      setError(null);
      
      // Simulate progress for demo (in real implementation, you'd use axios progress callback)
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 200);

      await s3ObjectAPI.upload(selectedBucket, file, customKey);

      clearInterval(progressInterval);
      setUploadProgress(100);
      
      setSuccess(`File "${file.name}" uploaded successfully!`);
      fetchObjects(searchPrefix || null);
      
      // Reset progress after delay
      setTimeout(() => {
        setUploadProgress(0);
      }, 2000);
      
    } catch (err) {
      console.error('Error uploading file:', err);
      setError('Failed to upload file: ' + 
        (err.response?.data?.detail || err.message));
      setUploadProgress(0);
    } finally {
      setUploading(false);
    }
  };

  const handleDownload = async (object) => {
    try {
      setError(null);
      
      const response = await s3ObjectAPI.download(selectedBucket, object.key);
      
      // Create blob and download
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', object.key.split('/').pop() || object.key);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      setSuccess(`Downloaded "${object.key}" successfully!`);
      
    } catch (err) {
      console.error('Error downloading file:', err);
      setError('Failed to download file: ' + 
        (err.response?.data?.detail || err.message));
    }
  };

  const handleDelete = async (object) => {
    if (!window.confirm(`Are you sure you want to delete "${object.key}"? This action cannot be undone.`)) {
      return;
    }

    try {
      setError(null);
      
      await s3ObjectAPI.delete(selectedBucket, object.key);
      
      setSuccess(`Deleted "${object.key}" successfully!`);
      fetchObjects(searchPrefix || null);
      
    } catch (err) {
      console.error('Error deleting file:', err);
      setError('Failed to delete file: ' + 
        (err.response?.data?.detail || err.message));
    }
  };

  const handleShowMetadata = async (object) => {
    try {
      setError(null);
      
      const response = await s3ObjectAPI.getMetadata(selectedBucket, object.key);
      setSelectedObject({
        ...object,
        metadata: response.data
      });
      setShowMetadata(true);
      
    } catch (err) {
      console.error('Error fetching metadata:', err);
      setError('Failed to fetch metadata: ' + 
        (err.response?.data?.detail || err.message));
    }
  };

  const generatePresignedUrl = async (object, type = 'download') => {
    try {
      setError(null);
      
      const response = type === 'download' 
        ? await s3PresignedAPI.getDownloadUrl(selectedBucket, object.key, 3600)
        : await s3PresignedAPI.getUploadUrl(selectedBucket, object.key, 3600);
      
      // Copy to clipboard
      await navigator.clipboard.writeText(response.data.url);
      setSuccess(`${type === 'download' ? 'Download' : 'Upload'} URL copied to clipboard! Valid for 1 hour.`);
      
    } catch (err) {
      console.error('Error generating presigned URL:', err);
      setError('Failed to generate presigned URL: ' + 
        (err.response?.data?.detail || err.message));
    }
  };

  // Drag and drop handlers
  const handleDragEnter = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!dragRef.current?.contains(e.relatedTarget)) {
      setIsDragging(false);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    
    const files = Array.from(e.dataTransfer.files);
    files.forEach(file => uploadFile(file));
  };

  const formatSize = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown';
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return 'Invalid date';
    }
  };

  const getFileIcon = (filename, contentType) => {
    const ext = filename.split('.').pop()?.toLowerCase();
    const type = contentType?.toLowerCase() || '';
    
    if (type.startsWith('image/') || ['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp'].includes(ext)) {
      return <Image size={16} style={{ color: '#10b981' }} />;
    }
    if (type.startsWith('video/') || ['mp4', 'avi', 'mov', 'mkv'].includes(ext)) {
      return <Video size={16} style={{ color: '#f59e0b' }} />;
    }
    if (type.startsWith('audio/') || ['mp3', 'wav', 'flac', 'aac'].includes(ext)) {
      return <Music size={16} style={{ color: '#8b5cf6' }} />;
    }
    if (['zip', 'rar', 'tar', 'gz', '7z'].includes(ext)) {
      return <Archive size={16} style={{ color: '#ef4444' }} />;
    }
    if (['js', 'jsx', 'ts', 'tsx', 'py', 'java', 'cpp', 'c', 'html', 'css'].includes(ext)) {
      return <Code size={16} style={{ color: '#3b82f6' }} />;
    }
    if (['txt', 'md', 'csv', 'json', 'xml'].includes(ext)) {
      return <FileText size={16} style={{ color: '#64748b' }} />;
    }
    return <File size={16} style={{ color: '#64748b' }} />;
  };

  if (!selectedBucket) {
    return (
      <div className="card">
        <div style={{ textAlign: 'center', padding: '3rem', color: '#64748b' }}>
          <FolderOpen size={64} style={{ marginBottom: '1rem', opacity: 0.5 }} />
          <h3 style={{ marginBottom: '0.5rem' }}>No Bucket Selected</h3>
          <p>Please select a bucket from the list above to manage its objects</p>
        </div>
      </div>
    );
  }

  return (
    <div className="s3-object-manager">
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
            <File size={20} />
            Objects in "{selectedBucket}" ({objects.length})
          </h3>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <div style={{ display: 'flex', gap: '0.25rem' }}>
              <input
                type="text"
                placeholder="Search prefix..."
                value={searchPrefix}
                onChange={(e) => setSearchPrefix(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                style={{
                  padding: '0.5rem 0.75rem',
                  border: '1px solid #e2e8f0',
                  borderRadius: '6px',
                  fontSize: '0.875rem',
                  width: '200px'
                }}
              />
              <button
                onClick={handleSearch}
                className="btn btn-secondary"
                title="Search objects by prefix"
              >
                <Search size={16} />
              </button>
            </div>
            <button
              onClick={() => fetchObjects(searchPrefix || null)}
              className="btn btn-secondary"
              disabled={loading}
            >
              <RefreshCw size={16} />
              Refresh
            </button>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              onChange={handleFileSelect}
              style={{ display: 'none' }}
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              className="btn btn-primary"
              disabled={uploading}
            >
              <Upload size={16} />
              Upload Files
            </button>
          </div>
        </div>

        {/* Upload Progress */}
        {uploading && (
          <div style={{ 
            padding: '1rem',
            borderTop: '1px solid #e2e8f0',
            backgroundColor: '#f8fafc'
          }}>
            <div style={{ marginBottom: '0.5rem', fontSize: '0.875rem', color: '#64748b' }}>
              Uploading... {uploadProgress}%
            </div>
            <div style={{
              width: '100%',
              height: '8px',
              backgroundColor: '#e2e8f0',
              borderRadius: '4px',
              overflow: 'hidden'
            }}>
              <div style={{
                width: `${uploadProgress}%`,
                height: '100%',
                backgroundColor: '#3b82f6',
                transition: 'width 0.3s ease'
              }} />
            </div>
          </div>
        )}

        {/* Drag and Drop Area */}
        <div
          ref={dragRef}
          onDragEnter={handleDragEnter}
          onDragLeave={handleDragLeave}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          style={{
            border: isDragging ? '2px dashed #3b82f6' : '2px dashed #e2e8f0',
            borderRadius: '8px',
            padding: '2rem',
            margin: '1rem',
            textAlign: 'center',
            backgroundColor: isDragging ? '#eff6ff' : '#f8fafc',
            transition: 'all 0.2s ease'
          }}
        >
          <Upload size={32} style={{ 
            color: isDragging ? '#3b82f6' : '#94a3b8',
            marginBottom: '1rem'
          }} />
          <p style={{ 
            margin: 0, 
            color: isDragging ? '#3b82f6' : '#64748b',
            fontSize: '0.875rem'
          }}>
            {isDragging 
              ? 'Drop files here to upload'
              : 'Drag and drop files here, or click "Upload Files" button'
            }
          </p>
        </div>

        {/* Objects List */}
        {loading ? (
          <div style={{ textAlign: 'center', padding: '2rem' }}>
            <div className="loading-spinner" style={{ margin: '0 auto' }}></div>
            <p style={{ marginTop: '1rem' }}>Loading objects...</p>
          </div>
        ) : objects.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: '#64748b' }}>
            {searchPrefix ? (
              <>
                <Search size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
                <p>No objects found with prefix "{searchPrefix}"</p>
                <button 
                  onClick={() => {
                    setSearchPrefix('');
                    fetchObjects();
                  }}
                  className="btn btn-secondary"
                  style={{ marginTop: '0.5rem' }}
                >
                  Clear search
                </button>
              </>
            ) : (
              <>
                <File size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
                <p>No objects in this bucket</p>
                <p>Upload some files using the button above or drag and drop</p>
              </>
            )}
          </div>
        ) : (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Size</th>
                  <th>Last Modified</th>
                  <th>Type</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {objects.map((object, index) => (
                  <tr key={`${object.key}-${index}`}>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        {getFileIcon(object.key, object.content_type)}
                        <div style={{ minWidth: 0, flex: 1 }}>
                          <div style={{ 
                            fontWeight: '500',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap'
                          }}>
                            {object.key.split('/').pop() || object.key}
                          </div>
                          {object.key.includes('/') && (
                            <div style={{ 
                              fontSize: '0.75rem', 
                              color: '#64748b',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap'
                            }}>
                              {object.key.substring(0, object.key.lastIndexOf('/'))}
                            </div>
                          )}
                        </div>
                      </div>
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                        <HardDrive size={14} style={{ color: '#64748b' }} />
                        <span style={{ fontSize: '0.875rem' }}>
                          {formatSize(object.size)}
                        </span>
                      </div>
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                        <Calendar size={14} style={{ color: '#64748b' }} />
                        <span style={{ fontSize: '0.875rem', color: '#64748b' }}>
                          {formatDate(object.last_modified)}
                        </span>
                      </div>
                    </td>
                    <td>
                      <span style={{ 
                        fontSize: '0.75rem',
                        padding: '0.25rem 0.5rem',
                        backgroundColor: '#f1f5f9',
                        color: '#475569',
                        borderRadius: '4px',
                        fontFamily: 'monospace'
                      }}>
                        {object.content_type || 'unknown'}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.25rem', flexWrap: 'wrap' }}>
                        <button
                          onClick={() => handleDownload(object)}
                          className="btn btn-secondary"
                          style={{ padding: '0.25rem 0.5rem' }}
                          title="Download file"
                        >
                          <Download size={12} />
                        </button>
                        
                        <button
                          onClick={() => handleShowMetadata(object)}
                          className="btn btn-secondary"
                          style={{ padding: '0.25rem 0.5rem' }}
                          title="View metadata"
                        >
                          <Eye size={12} />
                        </button>
                        
                        <button
                          onClick={() => generatePresignedUrl(object, 'download')}
                          className="btn btn-secondary"
                          style={{ padding: '0.25rem 0.5rem' }}
                          title="Generate download link"
                        >
                          <Link size={12} />
                        </button>
                        
                        <button
                          onClick={() => handleDelete(object)}
                          className="btn btn-danger"
                          style={{ padding: '0.25rem 0.5rem' }}
                          title="Delete file"
                        >
                          <Trash2 size={12} />
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

      {/* Metadata Modal */}
      {showMetadata && selectedObject && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div className="card" style={{ 
            width: '90%',
            maxWidth: '600px',
            maxHeight: '80vh',
            overflow: 'auto'
          }}>
            <div className="card-header">
              <h3 className="card-title">
                <Eye size={20} />
                Object Metadata
              </h3>
              <button
                onClick={() => setShowMetadata(false)}
                className="btn btn-secondary"
              >
                Close
              </button>
            </div>
            
            <div style={{ padding: '1rem' }}>
              <div style={{ marginBottom: '1rem' }}>
                <h4 style={{ marginBottom: '0.5rem' }}>Basic Information</h4>
                <div className="grid grid-2">
                  <div>
                    <strong>Key:</strong> {selectedObject.key}
                  </div>
                  <div>
                    <strong>Size:</strong> {formatSize(selectedObject.size)}
                  </div>
                  <div>
                    <strong>Content Type:</strong> {selectedObject.content_type || 'unknown'}
                  </div>
                  <div>
                    <strong>Last Modified:</strong> {formatDate(selectedObject.last_modified)}
                  </div>
                  <div>
                    <strong>ETag:</strong> 
                    <code style={{ 
                      fontSize: '0.75rem',
                      backgroundColor: '#f1f5f9',
                      padding: '0.125rem 0.25rem',
                      borderRadius: '3px',
                      marginLeft: '0.25rem'
                    }}>
                      {selectedObject.etag}
                    </code>
                  </div>
                </div>
              </div>
              
              {selectedObject.metadata?.metadata && Object.keys(selectedObject.metadata.metadata).length > 0 && (
                <div>
                  <h4 style={{ marginBottom: '0.5rem' }}>Custom Metadata</h4>
                  <div style={{ 
                    backgroundColor: '#f8fafc',
                    padding: '1rem',
                    borderRadius: '6px',
                    fontFamily: 'monospace',
                    fontSize: '0.875rem'
                  }}>
                    <pre style={{ margin: 0 }}>
                      {JSON.stringify(selectedObject.metadata.metadata, null, 2)}
                    </pre>
                  </div>
                </div>
              )}
              
              <div style={{ marginTop: '1rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                <button
                  onClick={() => generatePresignedUrl(selectedObject, 'download')}
                  className="btn btn-secondary"
                >
                  <Link size={16} />
                  Copy Download Link
                </button>
                <button
                  onClick={() => handleDownload(selectedObject)}
                  className="btn btn-primary"
                >
                  <Download size={16} />
                  Download
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default S3ObjectManager;