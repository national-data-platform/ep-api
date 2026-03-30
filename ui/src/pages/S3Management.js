import React, { useState, useEffect } from 'react';
import { Database, Info, AlertTriangle, AlertCircle } from 'lucide-react';
import S3BucketManager from '../components/S3BucketManager';
import S3ObjectManager from '../components/S3ObjectManager';
import { versionAPI } from '../services/api';

const S3Management = () => {
  const [selectedBucket, setSelectedBucket] = useState(null);
  const [s3Supported, setS3Supported] = useState(null); // null = checking, true/false = result
  const [apiVersion, setApiVersion] = useState(null);

  useEffect(() => {
    const checkS3Support = async () => {
      try {
        const [supported, versionInfo] = await Promise.all([
          versionAPI.supportsS3Features(),
          versionAPI.getVersion()
        ]);
        
        setS3Supported(supported);
        setApiVersion(versionInfo.version);
      } catch (error) {
        console.error('Error checking S3 support:', error);
        setS3Supported(false);
        setApiVersion('unknown');
      }
    };

    checkS3Support();
  }, []);

  // Show loading state while checking version
  if (s3Supported === null) {
    return (
      <div className="s3-management-page">
        <div className="page-header">
          <h1 className="page-title">
            <Database size={32} style={{ marginRight: '0.5rem' }} />
            S3 Bucket & Object Management
          </h1>
          <p className="page-subtitle">
            Checking API version compatibility...
          </p>
        </div>
        
        <div style={{ textAlign: 'center', padding: '3rem' }}>
          <div className="loading-spinner" style={{ margin: '0 auto' }}></div>
          <p style={{ marginTop: '1rem', color: '#64748b' }}>
            Verifying S3 feature availability...
          </p>
        </div>
      </div>
    );
  }

  // Show error if S3 features not supported
  if (!s3Supported) {
    return (
      <div className="s3-management-page">
        <div className="page-header">
          <h1 className="page-title">
            <Database size={32} style={{ marginRight: '0.5rem' }} />
            S3 Bucket & Object Management
          </h1>
          <p className="page-subtitle">
            API version {apiVersion} detected
          </p>
        </div>

        <div className="alert alert-error">
          <AlertCircle size={20} />
          <div>
            <div style={{ fontWeight: '500' }}>S3 Features Not Available</div>
            <div style={{ fontSize: '0.875rem', marginTop: '0.25rem' }}>
              S3 bucket and object management requires API version 0.2.0 or higher. 
              Current API version: <strong>{apiVersion}</strong>
            </div>
            <div style={{ fontSize: '0.875rem', marginTop: '0.5rem' }}>
              Please upgrade the API server to access these features, or use the 
              <strong> S3 Resources</strong> section for CKAN-integrated S3 resource management.
            </div>
          </div>
        </div>

        <div className="card">
          <div style={{ padding: '2rem', textAlign: 'center', color: '#64748b' }}>
            <Database size={64} style={{ marginBottom: '1rem', opacity: 0.3 }} />
            <h3 style={{ marginBottom: '0.5rem' }}>Feature Unavailable</h3>
            <p>Upgrade to API v0.2.0+ to access S3 management features</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="s3-management-page">
      {/* Page Header */}
      <div className="page-header">
        <h1 className="page-title">
          <Database size={32} style={{ marginRight: '0.5rem' }} />
          S3 Bucket & Object Management
        </h1>
        <p className="page-subtitle">
          Manage Amazon S3 buckets and objects directly through the API
        </p>
      </div>

      {/* API Version Notice */}
      <div className="alert" style={{
        backgroundColor: '#eff6ff',
        border: '1px solid #bfdbfe',
        color: '#1e40af',
        marginBottom: '1.5rem'
      }}>
        <Info size={20} />
        <div>
          <div style={{ fontWeight: '500' }}>S3 Management Features (API v{apiVersion})</div>
          <div style={{ fontSize: '0.875rem', marginTop: '0.25rem' }}>
            This page provides direct S3 bucket and object management capabilities. 
            These features require API version 0.2.0 or higher and proper S3 credentials configuration.
          </div>
        </div>
      </div>

      {/* Warning Notice */}
      <div className="alert alert-warning" style={{ marginBottom: '1.5rem' }}>
        <AlertTriangle size={20} />
        <div>
          <div style={{ fontWeight: '500' }}>Important Notice</div>
          <div style={{ fontSize: '0.875rem', marginTop: '0.25rem' }}>
            Direct S3 operations bypass CKAN metadata management. For data catalog integration, 
            use the <strong>S3 Resources</strong> section instead.
          </div>
        </div>
      </div>

      {/* Bucket Management Section */}
      <S3BucketManager 
        onBucketSelect={setSelectedBucket}
        selectedBucket={selectedBucket}
      />

      {/* Object Management Section */}
      <div style={{ marginTop: '1.5rem' }}>
        <S3ObjectManager selectedBucket={selectedBucket} />
      </div>

      {/* Usage Information */}
      <div className="card" style={{ marginTop: '1.5rem' }}>
        <div className="card-header">
          <h3 className="card-title">
            <Info size={20} />
            Usage Information
          </h3>
        </div>
        
        <div style={{ padding: '1rem' }}>
          <div className="grid grid-2">
            <div>
              <h4 style={{ marginBottom: '0.5rem', fontSize: '1rem' }}>Bucket Operations</h4>
              <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: '0.875rem', color: '#64748b' }}>
                <li>Create new S3 buckets with regional configuration</li>
                <li>List all available buckets with creation dates</li>
                <li>Delete empty buckets (must contain no objects)</li>
                <li>View bucket information and metadata</li>
              </ul>
            </div>
            
            <div>
              <h4 style={{ marginBottom: '0.5rem', fontSize: '1rem' }}>Object Operations</h4>
              <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: '0.875rem', color: '#64748b' }}>
                <li>Upload files via drag-and-drop or file selection</li>
                <li>Download objects directly to your computer</li>
                <li>Search objects by prefix/path</li>
                <li>View detailed object metadata</li>
                <li>Generate temporary presigned URLs for sharing</li>
                <li>Delete individual objects</li>
              </ul>
            </div>
          </div>
          
          <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: '#f8fafc', borderRadius: '6px' }}>
            <h4 style={{ marginBottom: '0.5rem', fontSize: '1rem' }}>Presigned URLs</h4>
            <p style={{ margin: 0, fontSize: '0.875rem', color: '#64748b' }}>
              Generate temporary authenticated URLs for secure file sharing. These URLs allow 
              external users to download files without requiring AWS credentials. URLs expire 
              after 1 hour for security.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default S3Management;