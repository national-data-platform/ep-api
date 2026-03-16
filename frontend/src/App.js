import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import AuthGuard from './components/AuthGuard';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Organizations from './pages/Organizations';
import KafkaTopics from './pages/KafkaTopics';
import UrlResources from './pages/UrlResources';
import S3Resources from './pages/S3Resources';
import Services from './pages/Services';
import Search from './pages/Search';
import DatasetManagement from './pages/DatasetManagement';
import './styles/global.css';

/**
 * Main App component with mandatory authentication
 * Users must provide a valid JWT token to access any part of the application
 */
function App() {
  return (
    <div className="App">
      <AuthGuard>
        <Router>
          <Layout>
            <Routes>
              {/* Dashboard route - main overview page */}
              <Route path="/" element={<Dashboard />} />
              
              {/* Organizations management routes */}
              <Route path="/organizations" element={<Organizations />} />
              
              {/* Data sources management routes */}
              <Route path="/kafka-topics" element={<KafkaTopics />} />
              <Route path="/url-resources" element={<UrlResources />} />
              <Route path="/s3-resources" element={<S3Resources />} />
              
              {/* Services management route */}
              <Route path="/services" element={<Services />} />
              
              {/* Dataset management routes */}
              <Route path="/datasets" element={<DatasetManagement />} />
              
              {/* Search functionality route */}
              <Route path="/search" element={<Search />} />
            </Routes>
          </Layout>
        </Router>
      </AuthGuard>
    </div>
  );
}

export default App;