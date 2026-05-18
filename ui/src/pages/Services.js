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
    // The service type is split between a canonical choice (API/UI/
    // Trigger) and an "Other" escape hatch with its own text input.
    // The submitted value is derived from these two fields below.
    service_type_choice: '',
    service_type_custom: '',
    notes: '',
    health_check_url: '',
    documentation_url: ''
  });
  const [extrasPairs, setExtrasPairs] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [typeHelpOpen, setTypeHelpOpen] = useState(false);

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
    // Resolve service_type from the choice + Other free-text. Sending
    // no field at all when nothing is selected preserves the previous
    // "blank type is fine" behavior.
    const resolvedType =
      formData.service_type_choice === 'Other'
        ? (formData.service_type_custom || '').trim()
        : formData.service_type_choice;
    if (resolvedType) payload.service_type = resolvedType;
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
        service_type_choice: '',
        service_type_custom: '',
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
            <select
              name="service_type_choice"
              value={formData.service_type_choice}
              onChange={handleInputChange}
              className="form-select"
            >
              <option value="">(none)</option>
              <option value="API">API</option>
              <option value="UI">UI</option>
              <option value="Trigger">Trigger</option>
              <option value="Other">Other…</option>
            </select>
            {formData.service_type_choice === 'Other' && (
              <input
                type="text"
                name="service_type_custom"
                value={formData.service_type_custom}
                onChange={handleInputChange}
                className="form-input"
                placeholder="Describe the service type"
                style={{ marginTop: '0.5rem' }}
                maxLength={50}
              />
            )}
            <button
              type="button"
              onClick={() => setTypeHelpOpen((v) => !v)}
              aria-expanded={typeHelpOpen}
              style={{
                marginTop: '0.5rem',
                background: 'transparent',
                border: 'none',
                padding: 0,
                color: '#2563eb',
                fontSize: '0.85rem',
                fontWeight: 500,
                cursor: 'pointer'
              }}
            >
              {typeHelpOpen
                ? 'Hide service type guide'
                : "What's this? Show service type guide"}
            </button>
            {typeHelpOpen && (
              <div
                style={{
                  marginTop: '0.5rem',
                  background: '#f8fafc',
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                  padding: '0.75rem 1rem',
                  fontSize: '0.85rem',
                  color: '#334155',
                  lineHeight: 1.55
                }}
              >
                <ul style={{ margin: 0, paddingLeft: '1.25rem' }}>
                  <li style={{ marginBottom: '0.5rem' }}>
                    <strong>API</strong>: A programmatic interface
                    (REST/HTTP, GraphQL, gRPC, etc.) intended to be
                    consumed by other software. Pick this for endpoints
                    designed to be called by code.
                  </li>
                  <li style={{ marginBottom: '0.5rem' }}>
                    <strong>UI</strong>: A user-facing interface (web
                    app, dashboard, data viewer, etc.) intended to be
                    opened in a browser by a human. Pick this when the
                    service is a website or visual tool.
                  </li>
                  <li>
                    <strong>Trigger</strong>: An event source or
                    scheduled job that initiates work on its own
                    (webhooks, cron jobs, message producers,
                    schedulers, etc.). Pick this when the service runs
                    without a direct user request.
                  </li>
                </ul>
                <small style={{ display: 'block', marginTop: '0.5rem', color: '#64748b' }}>
                  Use the <strong>Other…</strong> option above if none
                  of these applies.
                </small>
              </div>
            )}
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
