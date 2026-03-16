import React from 'react';
import Navigation from './Navigation';
import Footer from './Footer';

/**
 * Layout component that wraps all pages with consistent structure
 * Includes navigation header, main content area, and NDP footer
 * 
 * @param {Object} props - Component props
 * @param {React.ReactNode} props.children - Child components to render
 */
const Layout = ({ children }) => {
  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column'
    }}>
      {/* Navigation header */}
      <Navigation />
      
      {/* Main content area */}
      <main style={{
        flex: 1,
        padding: '2rem 0'
      }}>
        <div style={{
          maxWidth: '1200px',
          margin: '0 auto',
          padding: '0 1rem'
        }}>
          {children}
        </div>
      </main>
      
      {/* NDP Footer */}
      <Footer />
    </div>
  );
};

export default Layout;