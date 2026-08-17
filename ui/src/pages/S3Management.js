import React, { useState, useEffect } from 'react';
import { Navigate } from 'react-router-dom';
import { Database, Info, AlertTriangle } from 'lucide-react';
import S3BucketManager from '../components/S3BucketManager';
import S3ObjectManager from '../components/S3ObjectManager';
import { statusAPI } from '../services/api';

const S3Management = () => {
  const [selectedBucket, setSelectedBucket] = useState(null);
  // null = still checking, true/false = whether S3 is enabled on this Endpoint.
  const [s3Enabled, setS3Enabled] = useState(null);
  const [apiVersion, setApiVersion] = useState(null);
  // Whether this Endpoint has a local catalog changes what the notice below
  // should say: with one, direct S3 bypasses it (use S3 Resources to register);
  // without one, there is simply nothing to register into.
  const [hasLocalCatalog, setHasLocalCatalog] = useState(false);

  useEffect(() => {
    let cancelled = false;
    statusAPI
      .getStatus()
      .then((response) => {
        if (cancelled) return;
        setS3Enabled(response.data?.s3_enabled === true);
        setApiVersion(response.data?.api_version || null);
        const backend = response.data?.local_catalog_backend;
        setHasLocalCatalog(!!backend && backend !== 'none');
      })
      .catch((error) => {
        if (cancelled) return;
        console.error('Error checking S3 availability:', error);
        setS3Enabled(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Show loading state while checking whether S3 is enabled
  if (s3Enabled === null) {
    return (
      <div className="s3-management-page">
        <div className="page-header">
          <h1 className="page-title">
            <Database size={32} style={{ marginRight: '0.5rem' }} />
            S3 Bucket & Object Management
          </h1>
          <p className="page-subtitle">
            Checking S3 availability...
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

  // When S3 is not enabled on this Endpoint the feature does not exist for the
  // user: send them back to the landing page rather than showing a page that
  // can only fail. The navigation entry is hidden in the same case.
  if (!s3Enabled) {
    return <Navigate to="/" replace />;
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
          <div style={{ fontWeight: '500' }}>
            S3 Management Features{apiVersion ? ` (API v${apiVersion})` : ''}
          </div>
          <div style={{ fontSize: '0.875rem', marginTop: '0.25rem' }}>
            This page provides direct S3 bucket and object management capabilities
            for the S3 storage configured on this Endpoint.
          </div>
        </div>
      </div>

      {/* Warning Notice */}
      <div className="alert alert-warning" style={{ marginBottom: '1.5rem' }}>
        <AlertTriangle size={20} />
        <div>
          <div style={{ fontWeight: '500' }}>Important Notice</div>
          <div style={{ fontSize: '0.875rem', marginTop: '0.25rem' }}>
            {hasLocalCatalog ? (
              <>
                Direct S3 operations bypass the local catalog. To register an
                S3 file in the catalog so it shows up in Search, use the{' '}
                <strong>S3 resource</strong> option in the <strong>+ New</strong> menu instead.
              </>
            ) : (
              <>
                This Endpoint has no local catalog, so nothing here is registered
                in one — these are direct S3 storage operations only. The files
                you upload live in S3 and will not appear in catalog Search.
              </>
            )}
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