import React from 'react';
import { ArrowUpCircle } from 'lucide-react';

/**
 * Tells an Endpoint admin that a newer ep-api release exists (issue #395).
 *
 * `info` is the answer of GET /status/version. Nothing is shown unless the
 * backend says an update is available; the caller decides who sees it (the
 * Dashboard only passes it to admins).
 */
const UpdateNotice = ({ info }) => {
  if (!info || info.update_available !== true) return null;

  return (
    <div className="alert alert-warning" role="status" style={{ alignItems: 'flex-start' }}>
      <ArrowUpCircle size={20} />
      <div>
        <strong>A newer ep-api release is available: {info.latest_version}</strong>
        <div style={{ marginTop: '0.25rem' }}>
          This Endpoint runs {info.current_version}. Read what changed before
          upgrading, then re-run the installer on the server to upgrade.
        </div>
        <div style={{ marginTop: '0.5rem', display: 'flex', gap: '1rem' }}>
          {info.release_url && (
            <a href={info.release_url} target="_blank" rel="noopener noreferrer">
              Release notes
            </a>
          )}
          {info.changelog_url && (
            <a href={info.changelog_url} target="_blank" rel="noopener noreferrer">
              CHANGELOG
            </a>
          )}
        </div>
      </div>
    </div>
  );
};

export default UpdateNotice;
