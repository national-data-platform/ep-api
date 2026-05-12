import React, { useEffect, useRef, useState } from 'react';
import {
  Search as SearchIcon,
  AlertCircle,
  Settings,
  FileText,
  X,
  ExternalLink,
  Database
} from 'lucide-react';
import { searchAPI } from '../services/api';

const MODES = [
  { id: 'both', label: 'All' },
  { id: 'datasets', label: 'Datasets' },
  { id: 'services', label: 'Services' }
];

const SERVERS = [
  { id: 'global', label: 'Global' },
  { id: 'local', label: 'Local' }
];

const Search = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [mode, setMode] = useState('both');
  const [server, setServer] = useState('global');
  const [hasSearched, setHasSearched] = useState(false);
  const [datasetResults, setDatasetResults] = useState([]);
  const [serviceResults, setServiceResults] = useState([]);
  const inputRef = useRef(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const fetchDatasets = async (term, selectedServer) => {
    const response = await searchAPI.searchByTerms([term], null, selectedServer);
    return (response.data || []).filter((item) => item.owner_org !== 'services');
  };

  const fetchServices = async (term, selectedServer) => {
    const response = await searchAPI.searchAdvanced({
      owner_org: 'services',
      search_term: term,
      server: selectedServer
    });
    return (response.data || []).filter((item) => item.owner_org === 'services');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const term = searchTerm.trim();
    if (!term) {
      setError('Please enter a search term');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const wantDatasets = mode === 'datasets' || mode === 'both';
      const wantServices = mode === 'services' || mode === 'both';

      const safe = (p) => p.then((data) => ({ ok: true, data })).catch((err) => ({ ok: false, err }));
      const [datasetsRes, servicesRes] = await Promise.all([
        wantDatasets ? safe(fetchDatasets(term, server)) : Promise.resolve({ ok: true, data: [] }),
        wantServices ? safe(fetchServices(term, server)) : Promise.resolve({ ok: true, data: [] })
      ]);

      // Fail only when every requested search failed.
      const requested = [wantDatasets && datasetsRes, wantServices && servicesRes].filter(Boolean);
      const allFailed = requested.every((r) => !r.ok);
      if (allFailed) throw requested[0].err;

      setDatasetResults(datasetsRes.ok ? datasetsRes.data : []);
      setServiceResults(servicesRes.ok ? servicesRes.data : []);
      setHasSearched(true);
    } catch (err) {
      const status = err.response?.status;
      let message = 'Search failed';
      if (status === 422) message += ': validation error — check your search parameters';
      else if (status === 401) message += ': authentication required — please log in';
      else if (err.response?.data?.detail) message += `: ${err.response.data.detail}`;
      else if (err.message) message += `: ${err.message}`;
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const clearTerm = () => {
    setSearchTerm('');
    inputRef.current?.focus();
  };

  const totalResults = datasetResults.length + serviceResults.length;
  const compact = hasSearched || loading;

  return (
    <div style={{ maxWidth: '960px', margin: '0 auto', padding: '0 1rem' }}>
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          textAlign: 'center',
          paddingTop: compact ? '1.5rem' : '4rem',
          paddingBottom: compact ? '1rem' : '2rem',
          transition: 'padding 0.3s ease'
        }}
      >
        {!compact && (
          <>
            <h1
              style={{
                fontSize: '2.25rem',
                fontWeight: 700,
                color: '#1e293b',
                margin: 0,
                marginBottom: '0.5rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem'
              }}
            >
              <SearchIcon size={32} />
              Find datasets and services
            </h1>
            <p style={{ color: '#64748b', margin: 0, marginBottom: '2rem' }}>
              Search across the National Data Platform
            </p>
          </>
        )}

        <form onSubmit={handleSubmit} style={{ width: '100%', maxWidth: '680px' }}>
          <SearchBar
            inputRef={inputRef}
            value={searchTerm}
            onChange={setSearchTerm}
            onClear={clearTerm}
            loading={loading}
          />

          <FilterRow mode={mode} setMode={setMode} server={server} setServer={setServer} />
        </form>
      </div>

      {error && (
        <div className="alert alert-error" style={{ marginBottom: '1rem' }}>
          <AlertCircle size={20} />
          {error}
        </div>
      )}

      {hasSearched && !loading && !error && (
        <ResultsSummary total={totalResults} mode={mode} term={searchTerm} />
      )}

      {hasSearched && !loading && !error && (mode === 'datasets' || mode === 'both') && (
        <ResultsSection
          title="Datasets"
          icon={<FileText size={20} />}
          items={datasetResults}
          emptyMessage="No datasets matched your search."
          isService={false}
        />
      )}

      {hasSearched && !loading && !error && (mode === 'services' || mode === 'both') && (
        <ResultsSection
          title="Services"
          icon={<Settings size={20} />}
          items={serviceResults}
          emptyMessage="No services matched your search."
          isService
        />
      )}
    </div>
  );
};

const SearchBar = ({ inputRef, value, onChange, onClear, loading }) => (
  <div
    style={{
      display: 'flex',
      alignItems: 'center',
      background: 'white',
      border: '1px solid #e2e8f0',
      borderRadius: '999px',
      padding: '0.25rem 0.25rem 0.25rem 1.25rem',
      boxShadow: '0 1px 3px rgba(15, 23, 42, 0.06)'
    }}
  >
    <SearchIcon size={20} color="#94a3b8" />
    <input
      ref={inputRef}
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder="Search by name, description, keyword..."
      aria-label="Search term"
      style={{
        flex: 1,
        border: 'none',
        outline: 'none',
        fontSize: '1rem',
        padding: '0.75rem 0.75rem',
        background: 'transparent',
        color: '#1e293b'
      }}
    />
    {value && !loading && (
      <button
        type="button"
        onClick={onClear}
        aria-label="Clear search"
        style={{
          background: 'transparent',
          border: 'none',
          padding: '0.5rem',
          cursor: 'pointer',
          color: '#94a3b8',
          display: 'flex',
          alignItems: 'center'
        }}
      >
        <X size={18} />
      </button>
    )}
    <button
      type="submit"
      disabled={loading}
      style={{
        background: '#2563eb',
        color: 'white',
        border: 'none',
        borderRadius: '999px',
        padding: '0.65rem 1.25rem',
        fontSize: '0.95rem',
        fontWeight: 600,
        cursor: loading ? 'not-allowed' : 'pointer',
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        opacity: loading ? 0.7 : 1
      }}
    >
      {loading ? (
        <>
          <div className="loading-spinner" />
          Searching
        </>
      ) : (
        <>
          <SearchIcon size={16} />
          Search
        </>
      )}
    </button>
  </div>
);

const FilterRow = ({ mode, setMode, server, setServer }) => (
  <div
    style={{
      marginTop: '1rem',
      display: 'flex',
      flexWrap: 'wrap',
      justifyContent: 'center',
      gap: '0.75rem',
      alignItems: 'center'
    }}
  >
    <SegmentedControl options={MODES} value={mode} onChange={setMode} />
    <span style={{ color: '#cbd5e1' }}>·</span>
    <SegmentedControl options={SERVERS} value={server} onChange={setServer} subtle />
  </div>
);

const SegmentedControl = ({ options, value, onChange, subtle }) => (
  <div
    style={{
      display: 'inline-flex',
      background: subtle ? 'transparent' : '#f1f5f9',
      border: subtle ? '1px solid #e2e8f0' : 'none',
      borderRadius: '999px',
      padding: '0.2rem'
    }}
  >
    {options.map((opt) => {
      const active = opt.id === value;
      return (
        <button
          key={opt.id}
          type="button"
          onClick={() => onChange(opt.id)}
          style={{
            border: 'none',
            background: active ? 'white' : 'transparent',
            color: active ? '#1e293b' : '#64748b',
            borderRadius: '999px',
            padding: '0.4rem 0.9rem',
            fontSize: '0.85rem',
            fontWeight: active ? 600 : 500,
            cursor: 'pointer',
            boxShadow: active ? '0 1px 2px rgba(15, 23, 42, 0.08)' : 'none',
            transition: 'all 0.15s ease'
          }}
        >
          {opt.label}
        </button>
      );
    })}
  </div>
);

const ResultsSummary = ({ total, mode, term }) => (
  <div
    style={{
      color: '#64748b',
      fontSize: '0.9rem',
      marginBottom: '1rem',
      padding: '0 0.25rem'
    }}
  >
    {total > 0 ? (
      <>
        Found <strong style={{ color: '#1e293b' }}>{total}</strong> result{total === 1 ? '' : 's'} for "
        <strong style={{ color: '#1e293b' }}>{term}</strong>"
        {mode !== 'both' && ` in ${mode}`}
      </>
    ) : (
      <>
        No results for "<strong style={{ color: '#1e293b' }}>{term}</strong>"
      </>
    )}
  </div>
);

const ResultsSection = ({ title, icon, items, emptyMessage, isService }) => (
  <div style={{ marginBottom: '2rem' }}>
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        marginBottom: '0.75rem',
        color: '#334155',
        fontWeight: 600,
        fontSize: '0.95rem',
        textTransform: 'uppercase',
        letterSpacing: '0.04em'
      }}
    >
      {icon}
      {title}
      <span
        style={{
          background: '#f1f5f9',
          color: '#475569',
          borderRadius: '999px',
          padding: '0.1rem 0.55rem',
          fontSize: '0.75rem',
          fontWeight: 600
        }}
      >
        {items.length}
      </span>
    </div>

    {items.length === 0 ? (
      <div
        style={{
          background: '#f8fafc',
          border: '1px dashed #e2e8f0',
          borderRadius: '8px',
          padding: '1.25rem',
          color: '#94a3b8',
          fontSize: '0.9rem',
          textAlign: 'center'
        }}
      >
        {emptyMessage}
      </div>
    ) : (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {items.map((item, index) => (
          <ResultCard key={item.id || `${title}-${index}`} item={item} isService={isService} />
        ))}
      </div>
    )}
  </div>
);

const ResultCard = ({ item, isService }) => {
  const [expanded, setExpanded] = useState(false);
  const resources = item.resources || [];
  const hasExtras = item.extras && Object.keys(item.extras).length > 0;
  const showResources = resources.length > 0;
  const canToggle = showResources || hasExtras;

  return (
    <div
      style={{
        background: 'white',
        border: '1px solid #e2e8f0',
        borderRadius: '10px',
        padding: '1.1rem 1.25rem',
        transition: 'border-color 0.15s ease, box-shadow 0.15s ease'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', alignItems: 'flex-start' }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.4rem' }}>
            <Badge
              color={isService ? '#7c3aed' : '#2563eb'}
              background={isService ? '#f5f3ff' : '#eff6ff'}
            >
              {isService ? 'Service' : 'Dataset'}
            </Badge>
            {item.owner_org && (
              <Badge color="#475569" background="#f1f5f9">
                {item.owner_org}
              </Badge>
            )}
            {isService && item.extras?.service_type && (
              <Badge color="#0f766e" background="#ecfdf5">
                {item.extras.service_type}
              </Badge>
            )}
          </div>

          <h3
            style={{
              fontSize: '1.1rem',
              fontWeight: 600,
              color: '#0f172a',
              margin: 0,
              marginBottom: '0.25rem',
              wordBreak: 'break-word'
            }}
          >
            {item.title || item.name || 'Untitled'}
          </h3>

          {item.notes && (
            <p
              style={{
                color: '#475569',
                margin: 0,
                marginTop: '0.25rem',
                fontSize: '0.92rem',
                lineHeight: 1.5,
                display: '-webkit-box',
                WebkitLineClamp: expanded ? 'unset' : 3,
                WebkitBoxOrient: 'vertical',
                overflow: 'hidden'
              }}
            >
              {item.notes}
            </p>
          )}
        </div>
      </div>

      {canToggle && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          style={{
            marginTop: '0.75rem',
            background: 'transparent',
            border: 'none',
            color: '#2563eb',
            padding: 0,
            cursor: 'pointer',
            fontSize: '0.85rem',
            fontWeight: 500
          }}
        >
          {expanded
            ? 'Hide details'
            : `Show ${[
                showResources && `${resources.length} ${isService ? 'endpoint' : 'resource'}${resources.length === 1 ? '' : 's'}`,
                hasExtras && 'metadata'
              ]
                .filter(Boolean)
                .join(' & ')}`}
        </button>
      )}

      {expanded && showResources && (
        <div style={{ marginTop: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {resources.map((resource, idx) => (
            <ResourceRow key={resource.id || idx} resource={resource} isService={isService} />
          ))}
        </div>
      )}

      {expanded && hasExtras && (
        <div
          style={{
            marginTop: '0.75rem',
            padding: '0.75rem',
            background: '#f8fafc',
            borderRadius: '8px',
            border: '1px solid #e2e8f0'
          }}
        >
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0.5rem' }}>
            {Object.entries(item.extras).map(([key, value]) => (
              <div key={key} style={{ fontSize: '0.85rem' }}>
                <span style={{ color: '#64748b', fontWeight: 500 }}>{key}: </span>
                <span style={{ color: '#0f172a', wordBreak: 'break-word' }}>
                  {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const ResourceRow = ({ resource, isService }) => (
  <div
    style={{
      background: '#f8fafc',
      border: '1px solid #e2e8f0',
      borderRadius: '8px',
      padding: '0.75rem 1rem',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      gap: '1rem',
      flexWrap: 'wrap'
    }}
  >
    <div style={{ minWidth: 0, flex: 1 }}>
      <div style={{ fontWeight: 500, color: '#0f172a', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <Database size={14} color="#64748b" />
        {resource.name || 'Unnamed resource'}
      </div>
      {resource.description && (
        <div style={{ color: '#64748b', fontSize: '0.85rem', marginTop: '0.25rem' }}>{resource.description}</div>
      )}
    </div>
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
      {resource.format && (
        <Badge color="#475569" background="#e2e8f0">
          {resource.format}
        </Badge>
      )}
      {resource.url && (
        <a
          href={resource.url}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            color: '#2563eb',
            textDecoration: 'none',
            fontSize: '0.85rem',
            fontWeight: 500,
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.25rem'
          }}
        >
          {isService ? 'Open' : 'View'}
          <ExternalLink size={14} />
        </a>
      )}
    </div>
  </div>
);

const Badge = ({ children, color, background }) => (
  <span
    style={{
      background,
      color,
      fontSize: '0.75rem',
      fontWeight: 600,
      padding: '0.15rem 0.55rem',
      borderRadius: '999px',
      textTransform: 'none',
      letterSpacing: 0
    }}
  >
    {children}
  </span>
);

export default Search;
