import React, { useEffect, useState } from 'react';
import { Radio, AlertCircle, CheckCircle, Plus, Trash2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { kafkaAPI, organizationsAPI } from '../services/api';

/**
 * Single-purpose page reached from "+ New > Kafka topic". Registers a
 * Kafka topic as a catalog dataset. Listing and deletion live on the
 * Search page (Kafka topics are CKAN packages and show up there).
 */
const KafkaTopics = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    dataset_name: '',
    dataset_title: '',
    owner_org: '',
    dataset_description: '',
    kafka_topic: '',
    kafka_host: '',
    kafka_port: ''
  });
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
      dataset_name: formData.dataset_name,
      dataset_title: formData.dataset_title,
      owner_org: formData.owner_org,
      kafka_topic: formData.kafka_topic,
      kafka_host: formData.kafka_host,
      kafka_port: Number(formData.kafka_port)
    };
    if (formData.dataset_description)
      payload.dataset_description = formData.dataset_description;
    const extras = buildExtras();
    if (Object.keys(extras).length > 0) payload.extras = extras;

    try {
      await kafkaAPI.create(payload, 'local');
      setSuccess(
        `Kafka topic "${formData.dataset_name}" registered. You can keep registering more or go back to Search.`
      );
      setFormData((prev) => ({
        ...prev,
        dataset_name: '',
        dataset_title: '',
        dataset_description: '',
        kafka_topic: '',
        kafka_host: '',
        kafka_port: ''
      }));
      setExtrasPairs([]);
    } catch (err) {
      const detail = err.response?.data?.detail;
      const raw = typeof detail === 'string' ? detail : err.message;
      const msg = raw || 'unknown error';
      setError(
        /already exists/i.test(msg)
          ? `A dataset called "${formData.dataset_name}" already exists. Pick a different name.`
          : `Could not register the Kafka topic: ${msg}.`
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ maxWidth: '720px', margin: '0 auto', padding: '0 1rem' }}>
      <div className="page-header">
        <h1 className="page-title">
          <Radio size={32} style={{ marginRight: '0.5rem' }} />
          New Kafka topic
        </h1>
        <p className="page-subtitle">
          Register a Kafka topic as a catalog dataset so others can
          discover the stream and how to connect to it. Find it (and
          remove it) from the Search page once created.
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
            <label className="form-label">Dataset name *</label>
            <input
              type="text"
              name="dataset_name"
              value={formData.dataset_name}
              onChange={handleInputChange}
              className="form-input"
              placeholder="my-kafka-topic"
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
              name="dataset_title"
              value={formData.dataset_title}
              onChange={handleInputChange}
              className="form-input"
              placeholder="My Kafka Topic"
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
                No organizations available. Create one from &quot;+ New →
                Organization&quot; first.
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
              name="dataset_description"
              value={formData.dataset_description}
              onChange={handleInputChange}
              className="form-input form-textarea"
              placeholder="What does this stream contain?"
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '0.75rem' }}>
            <div className="form-group">
              <label className="form-label">Kafka host *</label>
              <input
                type="text"
                name="kafka_host"
                value={formData.kafka_host}
                onChange={handleInputChange}
                className="form-input"
                placeholder="kafka.example.com"
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">Kafka port *</label>
              <input
                type="number"
                name="kafka_port"
                value={formData.kafka_port}
                onChange={handleInputChange}
                className="form-input"
                placeholder="9092"
                min={1}
                max={65535}
                required
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Kafka topic *</label>
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
            <label className="form-label">Additional metadata</label>
            <small style={{ color: '#64748b', display: 'block', marginBottom: '0.5rem' }}>
              Optional key/value pairs stored on the dataset.
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
                'Register Kafka topic'
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

export default KafkaTopics;
