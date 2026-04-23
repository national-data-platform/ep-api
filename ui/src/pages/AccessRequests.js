import React, { useCallback, useEffect, useState } from 'react';
import {
  AlertCircle,
  CheckCircle,
  Clock,
  RefreshCw,
  ShieldAlert,
  XCircle,
} from 'lucide-react';
import { accessRequestsAPI } from '../services/api';

const STATUS_TABS = [
  { key: 'pending', label: 'Pending' },
  { key: 'approved', label: 'Approved' },
  { key: 'rejected', label: 'Rejected' },
];

const STATUS_STYLE = {
  pending: { background: '#fef3c7', border: '#fcd34d', color: '#92400e' },
  approved: { background: '#d1fae5', border: '#6ee7b7', color: '#065f46' },
  rejected: { background: '#fee2e2', border: '#fecaca', color: '#991b1b' },
};

const formatDate = (value) => {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleString();
  } catch {
    return String(value);
  }
};

/**
 * Admin-only page to review and act on access requests.
 */
const AccessRequests = () => {
  const [requests, setRequests] = useState([]);
  const [statusFilter, setStatusFilter] = useState('pending');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [actionSuccess, setActionSuccess] = useState(null);

  // Per-row action state keyed by request id.
  const [approveDraft, setApproveDraft] = useState({}); // { [id]: { grant, notes } }
  const [rejectDraft, setRejectDraft] = useState({}); // { [id]: notes }
  const [busyId, setBusyId] = useState(null);

  const fetchRequests = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await accessRequestsAPI.list(statusFilter);
      setRequests(response.data || []);
    } catch (err) {
      console.error('Failed to load access requests:', err);
      if (err.response?.status === 503) {
        setError(
          'The access-request workflow is disabled on this deployment.'
        );
      } else if (err.response?.status === 403) {
        setError(
          err.response.data?.detail ||
            'Administrator role required to view this page.'
        );
      } else {
        setError(
          err.response?.data?.detail ||
            err.message ||
            'Could not load access requests.'
        );
      }
      setRequests([]);
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    fetchRequests();
  }, [fetchRequests]);

  const openApproveDraft = (id) => {
    setApproveDraft((prev) => ({
      ...prev,
      [id]: prev[id] || { grant: 'member', notes: '' },
    }));
    setRejectDraft((prev) => {
      if (!(id in prev)) return prev;
      const next = { ...prev };
      delete next[id];
      return next;
    });
    setActionError(null);
    setActionSuccess(null);
  };

  const openRejectDraft = (id) => {
    setRejectDraft((prev) => ({ ...prev, [id]: prev[id] || '' }));
    setApproveDraft((prev) => {
      if (!(id in prev)) return prev;
      const next = { ...prev };
      delete next[id];
      return next;
    });
    setActionError(null);
    setActionSuccess(null);
  };

  const closeDrafts = (id) => {
    setApproveDraft((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
    setRejectDraft((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
  };

  const handleApprove = async (id) => {
    const draft = approveDraft[id] || { grant: 'member', notes: '' };
    try {
      setBusyId(id);
      setActionError(null);
      setActionSuccess(null);
      await accessRequestsAPI.approve(id, draft.grant, draft.notes.trim() || null);
      setActionSuccess(`Request approved as ${draft.grant}.`);
      closeDrafts(id);
      await fetchRequests();
    } catch (err) {
      console.error('Approve failed:', err);
      setActionError(
        err.response?.data?.detail ||
          err.message ||
          'Could not approve this request.'
      );
    } finally {
      setBusyId(null);
    }
  };

  const handleReject = async (id) => {
    const notes = (rejectDraft[id] || '').trim();
    try {
      setBusyId(id);
      setActionError(null);
      setActionSuccess(null);
      await accessRequestsAPI.reject(id, notes || null);
      setActionSuccess('Request rejected.');
      closeDrafts(id);
      await fetchRequests();
    } catch (err) {
      console.error('Reject failed:', err);
      setActionError(
        err.response?.data?.detail ||
          err.message ||
          'Could not reject this request.'
      );
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '1100px', margin: '0 auto' }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '1.5rem',
          gap: '1rem',
          flexWrap: 'wrap',
        }}
      >
        <h1 style={{ margin: 0, color: '#1e293b', fontSize: '1.75rem', fontWeight: 700 }}>
          <ShieldAlert size={24} style={{ verticalAlign: 'middle', marginRight: '0.5rem' }} />
          Access Requests
        </h1>
        <button
          type="button"
          onClick={fetchRequests}
          disabled={loading}
          style={{
            padding: '0.55rem 0.9rem',
            backgroundColor: 'white',
            border: '1px solid #cbd5e1',
            borderRadius: '6px',
            cursor: loading ? 'not-allowed' : 'pointer',
            color: '#374151',
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem',
            fontSize: '0.85rem',
            fontWeight: 500,
          }}
        >
          <RefreshCw size={14} />
          Refresh
        </button>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
        {STATUS_TABS.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setStatusFilter(tab.key)}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: statusFilter === tab.key ? '#2563eb' : 'white',
              color: statusFilter === tab.key ? 'white' : '#374151',
              border: '1px solid #cbd5e1',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '0.85rem',
              fontWeight: 500,
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {actionError && (
        <div
          style={{
            backgroundColor: '#fef2f2',
            border: '1px solid #fecaca',
            borderRadius: '6px',
            padding: '0.75rem',
            marginBottom: '1rem',
            display: 'flex',
            gap: '0.5rem',
            alignItems: 'center',
          }}
        >
          <AlertCircle size={18} style={{ color: '#dc2626', flexShrink: 0 }} />
          <span style={{ color: '#991b1b', fontSize: '0.875rem' }}>{actionError}</span>
        </div>
      )}

      {actionSuccess && (
        <div
          style={{
            backgroundColor: '#ecfdf5',
            border: '1px solid #a7f3d0',
            borderRadius: '6px',
            padding: '0.75rem',
            marginBottom: '1rem',
            display: 'flex',
            gap: '0.5rem',
            alignItems: 'center',
          }}
        >
          <CheckCircle size={18} style={{ color: '#059669', flexShrink: 0 }} />
          <span style={{ color: '#065f46', fontSize: '0.875rem' }}>{actionSuccess}</span>
        </div>
      )}

      {error && (
        <div
          style={{
            backgroundColor: '#fef2f2',
            border: '1px solid #fecaca',
            borderRadius: '6px',
            padding: '1rem',
            color: '#991b1b',
            fontSize: '0.9rem',
          }}
        >
          {error}
        </div>
      )}

      {!error && loading && (
        <div style={{ padding: '2rem', color: '#64748b', textAlign: 'center' }}>
          Loading access requests...
        </div>
      )}

      {!error && !loading && requests.length === 0 && (
        <div
          style={{
            padding: '2rem',
            border: '1px dashed #cbd5e1',
            borderRadius: '8px',
            color: '#64748b',
            textAlign: 'center',
            fontSize: '0.95rem',
          }}
        >
          No {statusFilter} access requests.
        </div>
      )}

      {!error && !loading && requests.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {requests.map((req) => {
            const statusStyle = STATUS_STYLE[req.status] || STATUS_STYLE.pending;
            const approveOpen = !!approveDraft[req.id];
            const rejectOpen = Object.prototype.hasOwnProperty.call(rejectDraft, req.id);
            const isBusy = busyId === req.id;

            return (
              <div
                key={req.id}
                style={{
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                  padding: '1rem',
                  backgroundColor: 'white',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.75rem',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                    gap: '1rem',
                    flexWrap: 'wrap',
                  }}
                >
                  <div>
                    <div style={{ fontSize: '1rem', fontWeight: 600, color: '#1e293b' }}>
                      {req.username}
                      {req.email && (
                        <span style={{ color: '#64748b', fontWeight: 400 }}>
                          {' '}· {req.email}
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: '0.8rem', color: '#64748b' }}>
                      <Clock size={12} style={{ verticalAlign: 'middle', marginRight: '0.25rem' }} />
                      Requested {formatDate(req.created_at)}
                    </div>
                  </div>
                  <span
                    style={{
                      padding: '0.25rem 0.6rem',
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      textTransform: 'uppercase',
                      letterSpacing: '0.04em',
                      borderRadius: '999px',
                      backgroundColor: statusStyle.background,
                      border: `1px solid ${statusStyle.border}`,
                      color: statusStyle.color,
                    }}
                  >
                    {req.status}
                  </span>
                </div>

                {req.justification && (
                  <div
                    style={{
                      fontSize: '0.875rem',
                      backgroundColor: '#f8fafc',
                      border: '1px solid #e2e8f0',
                      borderRadius: '6px',
                      padding: '0.6rem 0.75rem',
                      color: '#334155',
                      whiteSpace: 'pre-wrap',
                    }}
                  >
                    {req.justification}
                  </div>
                )}

                {req.status !== 'pending' && (
                  <div style={{ fontSize: '0.8rem', color: '#475569' }}>
                    Decided {formatDate(req.decided_at)}
                    {req.decided_by_username && (
                      <> by <strong>{req.decided_by_username}</strong></>
                    )}
                    {req.grant_type && (
                      <> · granted as <strong>{req.grant_type}</strong></>
                    )}
                    {req.decision_notes && (
                      <div style={{ marginTop: '0.35rem', fontStyle: 'italic' }}>
                        {req.decision_notes}
                      </div>
                    )}
                  </div>
                )}

                {req.status === 'pending' && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {!approveOpen && !rejectOpen && (
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button
                          type="button"
                          onClick={() => openApproveDraft(req.id)}
                          disabled={isBusy}
                          style={{
                            padding: '0.55rem 0.9rem',
                            backgroundColor: '#059669',
                            color: 'white',
                            border: 'none',
                            borderRadius: '6px',
                            cursor: isBusy ? 'not-allowed' : 'pointer',
                            fontSize: '0.85rem',
                            fontWeight: 600,
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.35rem',
                          }}
                        >
                          <CheckCircle size={14} /> Approve
                        </button>
                        <button
                          type="button"
                          onClick={() => openRejectDraft(req.id)}
                          disabled={isBusy}
                          style={{
                            padding: '0.55rem 0.9rem',
                            backgroundColor: 'white',
                            color: '#dc2626',
                            border: '1px solid #fecaca',
                            borderRadius: '6px',
                            cursor: isBusy ? 'not-allowed' : 'pointer',
                            fontSize: '0.85rem',
                            fontWeight: 600,
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.35rem',
                          }}
                        >
                          <XCircle size={14} /> Reject
                        </button>
                      </div>
                    )}

                    {approveOpen && (
                      <div
                        style={{
                          padding: '0.75rem',
                          backgroundColor: '#f8fafc',
                          border: '1px solid #e2e8f0',
                          borderRadius: '6px',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '0.5rem',
                        }}
                      >
                        <div style={{ fontSize: '0.85rem', color: '#374151', fontWeight: 600 }}>
                          Approve request — choose grant
                        </div>
                        <div style={{ display: 'flex', gap: '1rem', fontSize: '0.85rem', color: '#374151' }}>
                          <label style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                            <input
                              type="radio"
                              name={`grant-${req.id}`}
                              value="member"
                              checked={approveDraft[req.id]?.grant === 'member'}
                              onChange={() =>
                                setApproveDraft((prev) => ({
                                  ...prev,
                                  [req.id]: {
                                    ...(prev[req.id] || { notes: '' }),
                                    grant: 'member',
                                  },
                                }))
                              }
                            />
                            Member (access to the Endpoint)
                          </label>
                          <label style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                            <input
                              type="radio"
                              name={`grant-${req.id}`}
                              value="admin"
                              checked={approveDraft[req.id]?.grant === 'admin'}
                              onChange={() =>
                                setApproveDraft((prev) => ({
                                  ...prev,
                                  [req.id]: {
                                    ...(prev[req.id] || { notes: '' }),
                                    grant: 'admin',
                                  },
                                }))
                              }
                            />
                            Admin (access + manage future requests)
                          </label>
                        </div>
                        <textarea
                          value={approveDraft[req.id]?.notes || ''}
                          onChange={(e) =>
                            setApproveDraft((prev) => ({
                              ...prev,
                              [req.id]: {
                                ...(prev[req.id] || { grant: 'member' }),
                                notes: e.target.value,
                              },
                            }))
                          }
                          placeholder="Optional note (shown on the request record)"
                          maxLength={2000}
                          style={{
                            width: '100%',
                            minHeight: '60px',
                            padding: '0.5rem',
                            border: '1px solid #cbd5e1',
                            borderRadius: '6px',
                            fontSize: '0.85rem',
                            boxSizing: 'border-box',
                            resize: 'vertical',
                          }}
                        />
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                          <button
                            type="button"
                            onClick={() => handleApprove(req.id)}
                            disabled={isBusy}
                            style={{
                              padding: '0.5rem 0.8rem',
                              backgroundColor: '#059669',
                              color: 'white',
                              border: 'none',
                              borderRadius: '6px',
                              fontSize: '0.85rem',
                              fontWeight: 600,
                              cursor: isBusy ? 'not-allowed' : 'pointer',
                            }}
                          >
                            {isBusy ? 'Working...' : 'Confirm approval'}
                          </button>
                          <button
                            type="button"
                            onClick={() => closeDrafts(req.id)}
                            disabled={isBusy}
                            style={{
                              padding: '0.5rem 0.8rem',
                              backgroundColor: 'white',
                              color: '#64748b',
                              border: '1px solid #cbd5e1',
                              borderRadius: '6px',
                              fontSize: '0.85rem',
                              cursor: isBusy ? 'not-allowed' : 'pointer',
                            }}
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    )}

                    {rejectOpen && (
                      <div
                        style={{
                          padding: '0.75rem',
                          backgroundColor: '#fff7ed',
                          border: '1px solid #fed7aa',
                          borderRadius: '6px',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '0.5rem',
                        }}
                      >
                        <div style={{ fontSize: '0.85rem', color: '#9a3412', fontWeight: 600 }}>
                          Reject request
                        </div>
                        <textarea
                          value={rejectDraft[req.id] || ''}
                          onChange={(e) =>
                            setRejectDraft((prev) => ({
                              ...prev,
                              [req.id]: e.target.value,
                            }))
                          }
                          placeholder="Optional note for the record"
                          maxLength={2000}
                          style={{
                            width: '100%',
                            minHeight: '60px',
                            padding: '0.5rem',
                            border: '1px solid #fdba74',
                            borderRadius: '6px',
                            fontSize: '0.85rem',
                            boxSizing: 'border-box',
                            resize: 'vertical',
                          }}
                        />
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                          <button
                            type="button"
                            onClick={() => handleReject(req.id)}
                            disabled={isBusy}
                            style={{
                              padding: '0.5rem 0.8rem',
                              backgroundColor: '#dc2626',
                              color: 'white',
                              border: 'none',
                              borderRadius: '6px',
                              fontSize: '0.85rem',
                              fontWeight: 600,
                              cursor: isBusy ? 'not-allowed' : 'pointer',
                            }}
                          >
                            {isBusy ? 'Working...' : 'Confirm rejection'}
                          </button>
                          <button
                            type="button"
                            onClick={() => closeDrafts(req.id)}
                            disabled={isBusy}
                            style={{
                              padding: '0.5rem 0.8rem',
                              backgroundColor: 'white',
                              color: '#64748b',
                              border: '1px solid #cbd5e1',
                              borderRadius: '6px',
                              fontSize: '0.85rem',
                              cursor: isBusy ? 'not-allowed' : 'pointer',
                            }}
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default AccessRequests;
