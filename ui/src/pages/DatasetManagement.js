import React, { useEffect, useState } from 'react';
import {
  FileText,
  AlertCircle,
  CheckCircle,
  Plus,
  Trash2
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { generalDatasetAPI, organizationsAPI } from '../services/api';

/**
 * Single-purpose page reached from the "+ New > Dataset" menu. Listing,
 * editing, deletion and publishing live on the Search page now — this
 * page only exposes the create form.
 */
const DatasetManagement = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    name: '',
    title: '',
    owner_org: '',
    notes: '',
    private: false,
    // When true, after a successful create we chain a publish call to
    // the global catalog. The user still has to wait for an admin to
    // approve the submission before the dataset becomes visible.
    publishToGlobal: false
  });
  const [warning, setWarning] = useState(null);
  const [resources, setResources] = useState([
    { url: '', name: '', format: '', description: '' }
  ]);
  const [extrasPairs, setExtrasPairs] = useState([]);
  const [organizations, setOrganizations] = useState([]);
  const [orgsLoading, setOrgsLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  useEffect(() => {
    let cancelled = false;
    organizationsAPI
      .list({ server: 'local' })
      .then((response) => {
        if (cancelled) return;
        const orgs = Array.isArray(response.data) ? response.data : [];
        setOrganizations(orgs);
        // Pre-select the first org so the user doesn't have to do it
        // explicitly when there's only one realistic choice.
        setFormData((prev) =>
          prev.owner_org ? prev : { ...prev, owner_org: orgs[0] || '' }
        );
      })
      .catch(() => {
        if (!cancelled) setOrganizations([]);
      })
      .finally(() => {
        if (!cancelled) setOrgsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const updateResource = (idx, field, value) =>
    setResources((prev) =>
      prev.map((r, i) => (i === idx ? { ...r, [field]: value } : r))
    );

  const addResource = () =>
    setResources((prev) => [
      ...prev,
      { url: '', name: '', format: '', description: '' }
    ]);

  const removeResource = (idx) =>
    setResources((prev) => prev.filter((_, i) => i !== idx));

  const addExtraPair = () =>
    setExtrasPairs((prev) => [...prev, { key: '', value: '' }]);

  const removeExtraPair = (idx) =>
    setExtrasPairs((prev) => prev.filter((_, i) => i !== idx));

  const updateExtraPair = (idx, field, value) =>
    setExtrasPairs((prev) =>
      prev.map((p, i) => (i === idx ? { ...p, [field]: value } : p))
    );

  const buildExtras = () => {
    const out = {};
    for (const { key, value } of extrasPairs) {
      const trimmed = (key || '').trim();
      if (trimmed) out[trimmed] = value;
    }
    return out;
  };

  const buildResources = () => {
    const out = [];
    for (const r of resources) {
      const url = (r.url || '').trim();
      const name = (r.name || '').trim();
      if (!url || !name) continue;
      const entry = { url, name };
      if (r.format) entry.format = r.format;
      if (r.description) entry.description = r.description;
      out.push(entry);
    }
    return out;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setWarning(null);
    setSubmitting(true);

    const payload = {
      name: formData.name,
      title: formData.title,
      owner_org: formData.owner_org,
      private: Boolean(formData.private)
    };
    if (formData.notes) payload.notes = formData.notes;
    const builtResources = buildResources();
    if (builtResources.length > 0) payload.resources = builtResources;
    const extras = buildExtras();
    if (Object.keys(extras).length > 0) payload.extras = extras;

    const datasetName = formData.name;
    const wantsPublish = Boolean(formData.publishToGlobal);
    let createdDatasetId = null;

    try {
      const createResponse = await generalDatasetAPI.create(payload, 'local');
      createdDatasetId = createResponse?.data?.id || null;
    } catch (err) {
      const detail = err.response?.data?.detail;
      const raw = typeof detail === 'string' ? detail : err.message;
      const msg = raw || 'unknown error';
      setError(
        /already exists/i.test(msg)
          ? `A dataset called "${datasetName}" already exists. Pick a different name.`
          : /name/i.test(msg) && /(invalid|must contain|lowercase)/i.test(msg)
            ? 'The dataset name is invalid. Use lowercase letters, numbers, underscores and hyphens (no spaces).'
            : `Could not register the dataset: ${msg}.`
      );
      setSubmitting(false);
      return;
    }

    // From here on the dataset exists locally. Any publish failure is
    // surfaced as a non-fatal warning so the user knows the local
    // registration was kept and the publish action is still available
    // from the Search page.
    let publishWarning = null;
    let publishError = null;
    if (wantsPublish && createdDatasetId) {
      try {
        const publishResponse = await generalDatasetAPI.publish(createdDatasetId);
        publishWarning = publishResponse?.data?.warning || null;
      } catch (err) {
        const detail = err.response?.data?.detail;
        const raw = typeof detail === 'string' ? detail : err.message;
        publishError =
          `Dataset "${datasetName}" was registered, but it could not be ` +
          `published to the global catalog: ${raw || 'unknown error'}. You can ` +
          'try the Publish action from the Search page later.';
      }
    }

    if (publishError) {
      setWarning(publishError);
    } else if (wantsPublish) {
      const tail = publishWarning
        ? ` (note: ${publishWarning})`
        : '';
      setSuccess(
        `Dataset "${datasetName}" registered and submitted to the global ` +
          `catalog. It will only appear there once an administrator approves ` +
          `the submission.${tail}`
      );
    } else {
      setSuccess(
        `Dataset "${datasetName}" registered. You can keep registering more or go back to Search.`
      );
    }

    setFormData((prev) => ({
      ...prev,
      name: '',
      title: '',
      notes: '',
      private: false,
      publishToGlobal: false
      // keep owner_org selected so users registering several datasets
      // in the same org don't have to re-pick it every time.
    }));
    setResources([{ url: '', name: '', format: '', description: '' }]);
    setExtrasPairs([]);
    setSubmitting(false);
  };

  return (
    <div style={{ maxWidth: '760px', margin: '0 auto', padding: '0 1rem' }}>
      <div className="page-header">
        <h1 className="page-title">
          <FileText size={32} style={{ marginRight: '0.5rem' }} />
          New dataset
        </h1>
        <p className="page-subtitle">
          Register a new dataset on the local catalog. Once created, you
          can find it (and remove or publish it) from the Search page.
        </p>
      </div>

      {error && (
        <div className="alert alert-error">
          <AlertCircle size={20} />
          {error}
        </div>
      )}

      {warning && (
        <div
          style={{
            background: '#fffbeb',
            border: '1px solid #fde68a',
            color: '#78350f',
            borderRadius: '8px',
            padding: '0.75rem 1rem',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '0.5rem',
            marginBottom: '1rem',
            fontSize: '0.9rem'
          }}
        >
          <AlertCircle size={20} style={{ marginTop: '2px', flexShrink: 0 }} />
          <span>{warning}</span>
        </div>
      )}

      {success && (
        <div className="alert alert-success">
          <CheckCircle size={20} />
          {success}
        </div>
      )}

      <div className="card">
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Name *</label>
            <input
              type="text"
              name="name"
              value={formData.name}
              onChange={handleInputChange}
              className="form-input"
              placeholder="my-dataset"
              required
            />
            <small style={{ color: '#64748b' }}>
              Unique identifier — lowercase letters, numbers, underscores
              and hyphens only.
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
              placeholder="My Dataset"
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Organization *</label>
            {orgsLoading ? (
              <div style={{ color: '#64748b', fontSize: '0.9rem' }}>
                Loading organizations…
              </div>
            ) : organizations.length === 0 ? (
              <div style={{ color: '#7f1d1d', fontSize: '0.9rem' }}>
                No organizations are available on the local catalog yet.
                Create one from "+ New → Organization" before registering
                a dataset.
              </div>
            ) : (
              <select
                name="owner_org"
                value={formData.owner_org}
                onChange={handleInputChange}
                className="form-select"
                required
              >
                <option value="" disabled>
                  Choose an organization…
                </option>
                {organizations.map((org) => (
                  <option key={org} value={org}>
                    {org}
                  </option>
                ))}
              </select>
            )}
          </div>

          <div className="form-group">
            <label className="form-label">Description</label>
            <textarea
              name="notes"
              value={formData.notes}
              onChange={handleInputChange}
              className="form-input form-textarea"
              placeholder="What does this dataset contain?"
            />
          </div>

          <div className="form-group">
            <label
              className="form-label"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}
            >
              <input
                type="checkbox"
                name="private"
                checked={formData.private}
                onChange={handleInputChange}
                style={{ accentColor: '#2563eb' }}
              />
              Private dataset
            </label>
            <small style={{ color: '#64748b', display: 'block', marginTop: '0.25rem' }}>
              Private datasets are only visible to members of the owning
              organization.
            </small>
          </div>

          <div className="form-group">
            <label
              className="form-label"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}
            >
              <input
                type="checkbox"
                name="publishToGlobal"
                checked={formData.publishToGlobal}
                onChange={handleInputChange}
                style={{ accentColor: '#2563eb' }}
              />
              Publish to the global catalog after creation
            </label>
            <small style={{ color: '#64748b', display: 'block', marginTop: '0.25rem' }}>
              The dataset will not appear in the global catalog until an
              administrator approves the submission.
            </small>
          </div>

          <div className="form-group">
            <label className="form-label">Resources</label>
            <small style={{ color: '#64748b', display: 'block', marginBottom: '0.5rem' }}>
              Files or URLs that belong to the dataset. Rows with no URL
              or name are ignored.
            </small>
            {resources.map((resource, idx) => (
              <div
                key={idx}
                style={{
                  background: '#f8fafc',
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                  padding: '0.75rem',
                  marginBottom: '0.5rem'
                }}
              >
                <div
                  style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}
                >
                  <span style={{ fontWeight: 500, color: '#475569', fontSize: '0.85rem' }}>
                    Resource #{idx + 1}
                  </span>
                  {resources.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeResource(idx)}
                      className="btn btn-secondary"
                      style={{ padding: '0.25rem 0.5rem', fontSize: '0.8rem' }}
                      aria-label="Remove this resource"
                    >
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
                <div style={{ display: 'grid', gap: '0.5rem' }}>
                  <input
                    type="text"
                    value={resource.url}
                    onChange={(e) => updateResource(idx, 'url', e.target.value)}
                    className="form-input"
                    placeholder="URL (e.g. https://example.com/data.csv or s3://bucket/key)"
                  />
                  <input
                    type="text"
                    value={resource.name}
                    onChange={(e) => updateResource(idx, 'name', e.target.value)}
                    className="form-input"
                    placeholder="Resource name"
                  />
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '0.5rem' }}>
                    <input
                      type="text"
                      value={resource.format}
                      onChange={(e) => updateResource(idx, 'format', e.target.value)}
                      className="form-input"
                      placeholder="Format (CSV, JSON, …)"
                    />
                    <input
                      type="text"
                      value={resource.description}
                      onChange={(e) =>
                        updateResource(idx, 'description', e.target.value)
                      }
                      className="form-input"
                      placeholder="Description (optional)"
                    />
                  </div>
                </div>
              </div>
            ))}
            <button
              type="button"
              onClick={addResource}
              className="btn btn-secondary"
              style={{ marginTop: '0.25rem' }}
            >
              <Plus size={16} />
              Add resource
            </button>
          </div>

          <div className="form-group">
            <label className="form-label">Additional metadata</label>
            <small style={{ color: '#64748b', display: 'block', marginBottom: '0.5rem' }}>
              Optional key/value pairs that will be stored on the dataset.
            </small>
            {extrasPairs.map((pair, idx) => (
              <div key={idx} style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' }}>
                <input
                  type="text"
                  value={pair.key}
                  onChange={(e) => updateExtraPair(idx, 'key', e.target.value)}
                  className="form-input"
                  placeholder="key"
                  style={{ flex: 1 }}
                />
                <input
                  type="text"
                  value={pair.value}
                  onChange={(e) => updateExtraPair(idx, 'value', e.target.value)}
                  className="form-input"
                  placeholder="value"
                  style={{ flex: 1 }}
                />
                <button
                  type="button"
                  onClick={() => removeExtraPair(idx)}
                  className="btn btn-secondary"
                  style={{ padding: '0.5rem 0.75rem' }}
                  aria-label="Remove this pair"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
            <button
              type="button"
              onClick={addExtraPair}
              className="btn btn-secondary"
              style={{ marginTop: '0.25rem' }}
            >
              <Plus size={16} />
              Add field
            </button>
          </div>

          <div style={{ display: 'flex', gap: '1rem' }}>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={submitting || orgsLoading || organizations.length === 0}
            >
              {submitting ? (
                <>
                  <div className="loading-spinner" />
                  Registering
                </>
              ) : (
                'Register dataset'
              )}
            </button>
            <button
              type="button"
              onClick={() => navigate('/')}
              className="btn btn-secondary"
              disabled={submitting}
            >
              Back to Search
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default DatasetManagement;
