import React, { useState } from 'react';
import { Building2, AlertCircle, CheckCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { organizationsAPI } from '../services/api';

/**
 * Single-purpose page reached from the "+ New > Organization" menu.
 * Listing and deletion live on the Search page now — this page only
 * exposes the create form.
 */
const Organizations = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({ name: '', title: '', description: '' });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setSubmitting(true);
    try {
      await organizationsAPI.create(formData, 'local');
      setSuccess(
        `Organization "${formData.name}" created. You can keep creating more or go back to Search.`
      );
      setFormData({ name: '', title: '', description: '' });
    } catch (err) {
      const detail = err.response?.data?.detail;
      const raw = typeof detail === 'string' ? detail : err.message;
      setError(
        raw && /already exists/i.test(raw)
          ? `An organization called "${formData.name}" already exists. Pick a different name.`
          : raw && /name/i.test(raw) && /invalid/i.test(raw)
            ? 'The name is invalid. Use lowercase letters, numbers and hyphens (no spaces).'
            : `Could not create the organization: ${raw || 'unknown error'}.`
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ maxWidth: '640px', margin: '0 auto', padding: '0 1rem' }}>
      <div className="page-header">
        <h1 className="page-title">
          <Building2 size={32} style={{ marginRight: '0.5rem' }} />
          New organization
        </h1>
        <p className="page-subtitle">
          Register a new organization on the local catalog. Once created,
          you can find it (and remove it if you change your mind) from the
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
            <label className="form-label">Name *</label>
            <input
              type="text"
              name="name"
              value={formData.name}
              onChange={handleInputChange}
              className="form-input"
              placeholder="my-organization"
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
              name="title"
              value={formData.title}
              onChange={handleInputChange}
              className="form-input"
              placeholder="My Organization"
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
              placeholder="What is this organization for?"
            />
          </div>

          <div style={{ display: 'flex', gap: '1rem' }}>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? (
                <>
                  <div className="loading-spinner" />
                  Creating
                </>
              ) : (
                'Create organization'
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

export default Organizations;
