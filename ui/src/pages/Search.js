import React, { useState } from 'react';
import { Search as SearchIcon, AlertCircle, Settings } from 'lucide-react';
import { searchAPI } from '../services/api';

const Search = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [results, setResults] = useState([]);
  const [searchMode, setSearchMode] = useState('datasets'); // 'datasets' or 'services'
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedServer, setSelectedServer] = useState('global');

  const executeDatasetSearch = async (e) => {
    e.preventDefault();
    
    if (!searchTerm.trim()) {
      setError('Please enter a search term');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      console.log('Dataset search params:', {
        terms: [searchTerm],
        keys: null,
        server: selectedServer
      }); // Debug log

      const response = await searchAPI.searchByTerms([searchTerm], null, selectedServer);
      console.log('Dataset search response:', response.data); // Debug log
      
      setResults(response.data || []);
      
    } catch (err) {
      console.error('Error executing dataset search:', err);
      console.error('Error details:', {
        status: err.response?.status,
        statusText: err.response?.statusText,
        data: err.response?.data,
        config: err.config
      }); // Debug log
      
      let errorMessage = 'Dataset search failed';
      
      if (err.response?.status === 422) {
        errorMessage += ': Validation error - check your search parameters';
      } else if (err.response?.status === 401) {
        errorMessage += ': Authentication required - please login first';
      } else if (err.response?.data?.detail) {
        errorMessage += ': ' + err.response.data.detail;
      } else if (err.message) {
        errorMessage += ': ' + err.message;
      } else {
        errorMessage += ': Unknown error occurred';
      }
      
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const executeServiceSearch = async (e) => {
    e.preventDefault();
    
    if (!searchTerm.trim()) {
      setError('Please enter a search term');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const searchData = {
        owner_org: "services",
        search_term: searchTerm,
        server: selectedServer
      };

      console.log('Service search payload:', searchData); // Debug log

      const response = await searchAPI.searchAdvanced(searchData);
      
      // Filter results to only show services organization
      const filteredResults = (response.data || []).filter(item => 
        item.owner_org === 'services'
      );
      
      setResults(filteredResults);
      
    } catch (err) {
      console.error('Error executing service search:', err);
      let errorMessage = 'Service search failed';
      
      if (err.response?.data?.detail) {
        errorMessage += ': ' + err.response.data.detail;
      } else if (err.message) {
        errorMessage += ': ' + err.message;
      } else {
        errorMessage += ': Unknown error occurred';
      }
      
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const executeSearch = searchMode === 'datasets' ? executeDatasetSearch : executeServiceSearch;

  return (
    <div className="search-page">
      <div className="page-header">
        <h1 className="page-title">
          <SearchIcon size={32} style={{ marginRight: '0.5rem' }} />
          Search
        </h1>
        <p className="page-subtitle">
          Search for datasets and services across your CKAN instances
        </p>
      </div>

      {error && (
        <div className="alert alert-error">
          <AlertCircle size={20} />
          {error}
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Search</h3>
        </div>

        {/* Search Mode Toggle */}
        <div style={{ marginBottom: '1.5rem' }}>
          <div style={{
            display: 'flex',
            backgroundColor: '#f1f5f9',
            borderRadius: '8px',
            padding: '0.25rem'
          }}>
            <button
              onClick={() => setSearchMode('datasets')}
              style={{
                flex: 1,
                padding: '0.75rem 1rem',
                border: 'none',
                borderRadius: '6px',
                backgroundColor: searchMode === 'datasets' ? 'white' : 'transparent',
                color: searchMode === 'datasets' ? '#1e293b' : '#64748b',
                fontSize: '0.875rem',
                fontWeight: '500',
                cursor: 'pointer',
                boxShadow: searchMode === 'datasets' ? '0 1px 3px rgba(0, 0, 0, 0.1)' : 'none',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.5rem'
              }}
            >
              <SearchIcon size={16} />
              Search Datasets
            </button>
            <button
              onClick={() => setSearchMode('services')}
              style={{
                flex: 1,
                padding: '0.75rem 1rem',
                border: 'none',
                borderRadius: '6px',
                backgroundColor: searchMode === 'services' ? 'white' : 'transparent',
                color: searchMode === 'services' ? '#1e293b' : '#64748b',
                fontSize: '0.875rem',
                fontWeight: '500',
                cursor: 'pointer',
                boxShadow: searchMode === 'services' ? '0 1px 3px rgba(0, 0, 0, 0.1)' : 'none',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.5rem'
              }}
            >
              <Settings size={16} />
              Search Services
            </button>
          </div>
        </div>

        <form onSubmit={executeSearch}>
          <div className="form-group">
            <label className="form-label">Server</label>
            <select
              value={selectedServer}
              onChange={(e) => setSelectedServer(e.target.value)}
              className="form-select"
            >
              <option value="global">Global</option>
              <option value="local">Local</option>
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">
              Search Term
              {searchMode === 'services' && (
                <small style={{ fontWeight: 'normal', color: '#64748b', marginLeft: '0.5rem' }}>
                  - searching in services organization
                </small>
              )}
            </label>
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="form-input"
              placeholder={searchMode === 'datasets' ? 'Enter search term...' : 'Enter service name or description...'}
              required
            />
          </div>

          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? (
              <>
                <div className="loading-spinner" />
                Searching...
              </>
            ) : (
              <>
                <SearchIcon size={16} />
                Search {searchMode === 'datasets' ? 'Datasets' : 'Services'}
              </>
            )}
          </button>
        </form>
      </div>

      {results.length > 0 && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">
              {searchMode === 'datasets' ? <SearchIcon size={20} /> : <Settings size={20} />}
              Search Results ({results.length}) - {searchMode === 'datasets' ? 'Datasets' : 'Services'}
            </h3>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {results.map((item, index) => (
              <div 
                key={item.id || index}
                style={{
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                  padding: '1.5rem',
                  backgroundColor: 'white'
                }}
              >
                <h4 style={{ 
                  color: '#1e293b', 
                  marginBottom: '0.5rem',
                  fontSize: '1.25rem',
                  fontWeight: '600',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem'
                }}>
                  {searchMode === 'services' && <Settings size={20} />}
                  {item.title || item.name}
                </h4>
                
                <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '0.5rem' }}>
                  <span className="status-indicator status-success">
                    Organization: {item.owner_org || 'No organization'}
                  </span>
                  
                  {item.id && (
                    <span style={{ fontSize: '0.875rem', color: '#64748b' }}>
                      ID: {item.id}
                    </span>
                  )}

                  {searchMode === 'services' && item.extras?.service_type && (
                    <span className="status-indicator status-info">
                      Type: {item.extras.service_type}
                    </span>
                  )}
                </div>

                {item.notes && (
                  <p style={{ color: '#64748b', margin: '0.5rem 0' }}>
                    {item.notes}
                  </p>
                )}

                {item.resources && item.resources.length > 0 && (
                  <div style={{ marginTop: '1rem' }}>
                    <h5 style={{ 
                      color: '#374151', 
                      marginBottom: '0.5rem',
                      fontSize: '1rem',
                      fontWeight: '500'
                    }}>
                      {searchMode === 'services' ? 'Service Endpoints' : 'Resources'} ({item.resources.length})
                    </h5>
                    
                    {item.resources.map((resource, resourceIndex) => (
                      <div 
                        key={resource.id || resourceIndex}
                        style={{
                          backgroundColor: '#f8fafc',
                          padding: '1rem',
                          borderRadius: '6px',
                          border: '1px solid #e2e8f0',
                          marginBottom: '0.5rem'
                        }}
                      >
                        <div style={{ fontWeight: '500', color: '#1e293b', marginBottom: '0.25rem' }}>
                          {resource.name || 'Unnamed Resource'}
                        </div>
                        
                        {resource.description && (
                          <div style={{ fontSize: '0.875rem', color: '#64748b', marginBottom: '0.5rem' }}>
                            {resource.description}
                          </div>
                        )}

                        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center' }}>
                          {resource.format && (
                            <span className="status-indicator status-info">
                              {resource.format}
                            </span>
                          )}
                          
                          {resource.url && (
                            <a 
                              href={resource.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              style={{
                                color: '#2563eb',
                                textDecoration: 'none',
                                fontSize: '0.875rem',
                                fontWeight: '500'
                              }}
                            >
                              {searchMode === 'services' ? '🔗 Access Service' : '📄 View Resource'} →
                            </a>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {item.extras && Object.keys(item.extras).length > 0 && (
                  <div style={{ marginTop: '1rem' }}>
                    <h5 style={{ 
                      color: '#374151', 
                      marginBottom: '0.5rem',
                      fontSize: '1rem',
                      fontWeight: '500'
                    }}>
                      {searchMode === 'services' ? 'Service Details' : 'Additional Information'}
                    </h5>
                    
                    <div style={{
                      backgroundColor: '#f8fafc',
                      padding: '1rem',
                      borderRadius: '6px',
                      border: '1px solid #e2e8f0'
                    }}>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem' }}>
                        {Object.entries(item.extras).map(([key, value]) => (
                          <div key={key} style={{ minWidth: '200px' }}>
                            <span style={{ fontWeight: '500', color: '#374151' }}>
                              {key}:
                            </span>
                            <span style={{ marginLeft: '0.5rem', color: '#64748b' }}>
                              {typeof value === 'object' ? JSON.stringify(value) : value}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {!loading && results.length === 0 && !error && (
        <div className="card">
          <div style={{ textAlign: 'center', padding: '3rem', color: '#64748b' }}>
            {searchMode === 'datasets' ? 
              <SearchIcon size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} /> : 
              <Settings size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
            }
            <p>No search results yet</p>
            <p>Enter a search term above to find {searchMode === 'datasets' ? 'datasets' : 'services'}</p>
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Search Tips</h3>
        </div>
        <div className="grid grid-2">
          <div>
            <h4 style={{ marginBottom: '0.5rem', color: '#374151' }}>Dataset Search</h4>
            <ul style={{ color: '#64748b', paddingLeft: '1.5rem' }}>
              <li>Search across all dataset fields (title, description, resources)</li>
              <li>Use keywords to find relevant datasets</li>
              <li>Select server to search in specific CKAN instances</li>
            </ul>
          </div>
          
          <div>
            <h4 style={{ marginBottom: '0.5rem', color: '#374151' }}>Service Search</h4>
            <ul style={{ color: '#64748b', paddingLeft: '1.5rem' }}>
              <li>Search specifically in the "services" organization</li>
              <li>Find registered APIs, web services, and microservices</li>
              <li>View service endpoints and access URLs</li>
              <li>See service types and additional metadata</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Search;