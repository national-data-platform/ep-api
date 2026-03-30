import React from 'react';
import { Instagram, X, Linkedin } from 'lucide-react';

/**
 * Enhanced Footer component - More similar to nationaldataplatform.org
 * Larger layout with better spacing and typography
 * Now includes application version display
 * UPDATED: Frontend version upgraded from 0.0.0 to 0.1.0
 */
const Footer = () => {
  // Application version - update this when releasing new versions
  const APP_VERSION = '1.3.0-alpha.2';

  return (
    <footer style={{
      backgroundColor: '#001642',
      color: 'white',
      padding: '1.5rem 0 1rem 0', // Reduced padding
      marginTop: 'auto'
    }}>
      <div style={{
        maxWidth: '1200px',
        margin: '0 auto',
        padding: '0 1rem'
      }}>
        {/* Main Content Row */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '2rem',
          marginBottom: '1rem' // Added margin bottom
        }}>
          
          {/* Left: Logo Section */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem', // Reduced gap
            flex: '0 0 auto'
          }}>
            <img 
              src="https://nationaldataplatform.org/National_Data_Platform_horiz_stacked_wt.svg"
              alt="National Data Platform"
              style={{
                height: '40px', // Reduced from 50px
                width: 'auto'
              }}
              onError={(e) => {
                e.target.style.display = 'none';
              }}
            />
            <img 
              src="https://nationaldataplatform.org/nsf-logo.png"
              alt="NSF Logo"
              style={{
                height: '40px', // Reduced from 50px
                width: 'auto'
              }}
              onError={(e) => {
                e.target.style.display = 'none';
              }}
            />
          </div>

          {/* Center: Contact and Funding Information */}
          <div style={{
            flex: '1',
            fontSize: '0.8rem', // Reduced from 0.875rem
            lineHeight: '1.4', // Reduced line height
            paddingLeft: '1rem',
            paddingRight: '1rem'
          }}>
            <div style={{
              fontWeight: '600',
              marginBottom: '0.3rem', // Reduced spacing
              fontSize: '0.9rem' // Reduced font size
            }}>
              Contact - ndp@sdsc.edu
            </div>
            <div style={{
              fontSize: '0.8rem' // Reduced font size
            }}>
              The National Data Platform was funded by{' '}
              <a 
                href="https://www.nsf.gov/awardsearch/showAward?AWD_ID=2333609"
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  color: '#60a5fa',
                  textDecoration: 'underline'
                }}
              >
                NSF 2333609
              </a>
              {' '}under CI, CISE Research Resources programs. Any opinions, findings,
              conclusions, or recommendations expressed in this material are those of the author(s)
              and do not necessarily reflect the views of the funders.
            </div>
          </div>

          {/* Right: Social Media Icons */}
          <div style={{
            display: 'flex',
            gap: '0.6rem', // Reduced gap
            flex: '0 0 auto'
          }}>
            {/* Instagram */}
            <a
              href="https://www.instagram.com/nationaldataplatform/"
              target="_blank"
              rel="noopener noreferrer"
              style={{
                color: 'white',
                textDecoration: 'none',
                padding: '0.5rem', // Increased padding
                borderRadius: '6px',
                transition: 'all 0.3s ease',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
              onMouseOver={(e) => {
                e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.1)';
                e.target.style.transform = 'translateY(-2px)';
              }}
              onMouseOut={(e) => {
                e.target.style.backgroundColor = 'transparent';
                e.target.style.transform = 'translateY(0)';
              }}
              title="Follow us on Instagram"
            >
              <Instagram size={24} /> {/* Increased from 16 */}
            </a>

            {/* Twitter/X */}
            <a
              href="https://x.com/natldataplat"
              target="_blank"
              rel="noopener noreferrer"
              style={{
                color: 'white',
                textDecoration: 'none',
                padding: '0.5rem',
                borderRadius: '6px',
                transition: 'all 0.3s ease',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
              onMouseOver={(e) => {
                e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.1)';
                e.target.style.transform = 'translateY(-2px)';
              }}
              onMouseOut={(e) => {
                e.target.style.backgroundColor = 'transparent';
                e.target.style.transform = 'translateY(0)';
              }}
              title="Follow us on X (Twitter)"
            >
              <X size={24} />
            </a>

            {/* LinkedIn */}
            <a
              href="https://www.linkedin.com/company/national-data-platform/"
              target="_blank"
              rel="noopener noreferrer"
              style={{
                color: 'white',
                textDecoration: 'none',
                padding: '0.5rem',
                borderRadius: '6px',
                transition: 'all 0.3s ease',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
              onMouseOver={(e) => {
                e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.1)';
                e.target.style.transform = 'translateY(-2px)';
              }}
              onMouseOut={(e) => {
                e.target.style.backgroundColor = 'transparent';
                e.target.style.transform = 'translateY(0)';
              }}
              title="Connect with us on LinkedIn"
            >
              <Linkedin size={24} />
            </a>
          </div>
        </div>

        {/* Version Information Row */}
        <div style={{
          borderTop: '1px solid rgba(255, 255, 255, 0.1)',
          paddingTop: '0.75rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: '0.75rem',
          color: 'rgba(255, 255, 255, 0.7)'
        }}>
          <div>
            © {new Date().getFullYear()} National Data Platform. All rights reserved.
          </div>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}>
            <span>NDP EndPoint</span>
            <span style={{
              backgroundColor: 'rgba(255, 255, 255, 0.1)',
              padding: '0.25rem 0.5rem',
              borderRadius: '4px',
              fontSize: '0.7rem',
              fontFamily: 'monospace',
              color: 'rgba(255, 255, 255, 0.9)'
            }}>
              v{APP_VERSION}
            </span>
          </div>
        </div>
      </div>

      {/* Responsive Styles */}
      <style jsx>{`
        @media (max-width: 1400px) {
          footer div[style*="flex: 1"] {
            font-size: 0.8rem;
          }
          
          footer div[style*="fontSize: 1rem"] {
            font-size: 0.9rem;
          }
        }
        
        @media (max-width: 1200px) {
          footer div[style*="flex: 1"] {
            font-size: 0.75rem;
            line-height: 1.4;
          }
          
          footer div[style*="fontSize: 1rem"] {
            font-size: 0.85rem;
          }
          
          footer img {
            max-height: 40px;
          }
          
          footer svg {
            width: 20px;
            height: 20px;
          }
        }
        
        @media (max-width: 968px) {
          footer > div > div:first-child {
            flex-direction: column;
            justify-content: center;
            text-align: center;
            gap: 1.5rem;
            align-items: center;
          }
          
          footer div[style*="flex: 1"] {
            font-size: 0.8rem;
            flex-basis: auto;
            order: 2;
            padding-left: 0;
            padding-right: 0;
            max-width: 600px;
          }
          
          footer div[style*="flex: 0 0 auto"]:first-child {
            order: 1;
          }
          
          footer div[style*="flex: 0 0 auto"]:last-child {
            order: 3;
          }
          
          footer img {
            max-height: 35px;
          }
          
          footer svg {
            width: 22px;
            height: 22px;
          }

          /* Version row responsive */
          footer div[style*="borderTop"] {
            flex-direction: column;
            gap: 0.5rem;
            text-align: center;
          }
        }

        @media (max-width: 640px) {
          footer {
            padding: 1.5rem 0 1rem 0 !important;
          }
          
          footer > div > div:first-child {
            gap: 1rem;
          }
          
          footer div[style*="flex: 1"] {
            font-size: 0.75rem;
            line-height: 1.3;
          }
          
          footer div[style*="fontSize: 1rem"] {
            font-size: 0.8rem;
          }
          
          footer img {
            max-height: 30px;
          }
          
          footer svg {
            width: 20px;
            height: 20px;
          }

          /* Version row mobile */
          footer div[style*="borderTop"] {
            font-size: 0.7rem;
          }

          footer div[style*="borderTop"] span[style*="monospace"] {
            font-size: 0.65rem;
          }
        }
      `}</style>
    </footer>
  );
};

export default Footer;