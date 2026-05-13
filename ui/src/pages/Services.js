import React, { useState } from 'react';
import { Settings, AlertCircle, CheckCircle, Plus, Trash2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { servicesAPI } from '../services/api';

/**
 * Single-purpose page reached from the "+ New > Service" menu. Listing
 * and deletion live on the Search page now — this page only exposes the
 * create form.
 */
const Services = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    service_name: '',
    service_title: '',
    service_url: '',
    service_type: '',
    notes: '',
    health_check_url: '',
    documentation_url: ''
  });
  const [extrasPairs, setExtrasPairs] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

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

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setSubmitting(true);

    const payload = {
      service_name: formData.service_name,
      service_title: formData.service_title,
      // Services always live under the "services" org by API contract,
      // so we set it on the client and don't expose it as an input.
      owner_org: 'services',
      service_url: formData.service_url
    };
    if (formData.service_type) payload.service_type = formData.service_type;
    if (formData.notes) payload.notes = formData.notes;
    if (formData.health_check_url)
      payload.health_check_url = formData.health_check_url;
    if (formData.documentation_url)
      payload.documentation_url = formData.documentation_url;
    const extras = buildExtras();
    if (Object.keys(extras).length > 0) payload.extras = extras;

    try {
      await servicesAPI.create(payload, 'local');
      setSuccess(
        `Service "${formData.service_name}" registered. You can keep registering more or go back to Search.`
      );
      setFormData({
        service_name: '',
        service_title: '',
        service_url: '',
        service_type: '',
        notes: '',
        health_check_url: '',
        documentation_url: ''
      });
      setExtrasPairs([]);
    } catch (err) {
      const detail = err.response?.data?.detail;
      const raw = typeof detail === 'string' ? detail : err.message;
      const msg = raw || 'unknown error';
      setError(
        /already exists/i.test(msg)
          ? `A service called "${formData.service_name}" already exists. Pick a different name.`
          : /name/i.test(msg) && /invalid/i.test(msg)
            ? 'The service name is invalid. Use lowercase letters, numbers and hyphens (no spaces).'
            : `Could not register the service: ${msg}.`
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ maxWidth: '720px', margin: '0 auto', padding: '0 1rem' }}>
      <div className="page-header">
        <h1 className="page-title">
          <Settings size={32} style={{ marginRight: '0.5rem' }} />
          New service
        </h1>
        <p className="page-subtitle">
          Register a new service on the local catalog. Once created, you
          can find it (and remove it if you change your mind) from the
          Search page.
        </p>
      </div>

      {error && (
        <div className="alert alert-error">
          <AlertCircle size={20} />
          {error}
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
            <label className="form-label">Service name *</label>
            <input
              type="text"
              name="service_name"
              value={formData.service_name}
              onChange={handleInputChange}
              className="form-input"
              placeholder="my-service"
              required
            />
            <small style={{ color: '#64748b' }}>
              Unique identifier — lowercase, numbers and hyphens only.
            </small>
          </div>

          <div className="form-group">
            <label className="form-label">Title *</label>
            <input
              type="text"
              name="service_title"
              value={formData.service_title}
              onChange={handleInputChange}
              className="form-input"
              placeholder="My Service"
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Service URL *</label>
            <input
              type="url"
              name="service_url"
              value={formData.service_url}
              onChange={handleInputChange}
              className="form-input"
              placeholder="https://api.example.com/my-service"
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Service type</label>
            <input
              type="text"
              name="service_type"
              value={formData.service_type}
              onChange={handleInputChange}
              className="form-input"
              placeholder="API, Web Service, Microservice…"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Description</label>
            <textarea
              name="notes"
              value={formData.notes}
              onChange={handleInputChange}
              className="form-input form-textarea"
              placeholder="What is this service for?"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Health check URL</label>
            <input
              type="url"
              name="health_check_url"
              value={formData.health_check_url}
              onChange={handleInputChange}
              className="form-input"
              placeholder="https://api.example.com/my-service/health"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Documentation URL</label>
            <input
              type="url"
              name="documentation_url"
              value={formData.documentation_url}
              onChange={handleInputChange}
              className="form-input"
              placeholder="https://docs.example.com/my-service"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Additional metadata</label>
            <small style={{ color: '#64748b', display: 'block', marginBottom: '0.5rem' }}>
              Optional key/value pairs that will be stored on the service.
            </small>
            {extrasPairs.map((pair, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  gap: '0.5rem',
                  marginBottom: '0.5rem'
                }}
              >
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
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? (
                <>
                  <div className="loading-spinner" />
                  Registering
                </>
              ) : (
                'Register service'
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

export default Services;
