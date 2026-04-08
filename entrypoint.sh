#!/bin/sh

# Generate runtime config for the React UI
# This injects ROOT_PATH into the frontend without requiring a rebuild
cat > /app/ui/build/config.js <<EOF
window.__EP_CONFIG__ = { rootPath: "${ROOT_PATH}" };
EOF

# Start supervisord
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
