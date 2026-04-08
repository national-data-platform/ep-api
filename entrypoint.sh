#!/bin/sh

# Generate runtime config for the React UI
cat > /app/ui/build/config.js <<EOF
window.__EP_CONFIG__ = { rootPath: "${ROOT_PATH}" };
EOF

# Rewrite all /ui/ asset references in the built index.html to include ROOT_PATH
sed -i "s|\"/ui/|\"${ROOT_PATH}/ui/|g" /app/ui/build/index.html

# Generate nginx config with ROOT_PATH-prefixed locations
cat > /etc/nginx/sites-available/default <<NGINX
server {
    listen 80;
    server_name _;

    # UI - static files served from ${ROOT_PATH}/ui/
    location ${ROOT_PATH}/ui/ {
        alias /app/ui/build/;
        try_files \$uri \$uri/ ${ROOT_PATH}/ui/index.html;
    }

    # Redirect ${ROOT_PATH}/ui to ${ROOT_PATH}/ui/
    location = ${ROOT_PATH}/ui {
        return 301 \$scheme://\$host\$request_uri/;
    }

    # Alternative API path (also works via ${ROOT_PATH}/api/)
    location ${ROOT_PATH}/api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Root = API
    location ${ROOT_PATH}/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
NGINX

# Start supervisord
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
