#!/bin/sh

# Generate runtime config for the React UI. AFFINITIES_EP_UUID lets the
# UI highlight the user's group that ties them to this endpoint without
# having to look the value up against the deployment env manually.
# OIDC_ENABLED gates the "sign in through the identity provider" button; it
# defaults to False so a deployment that says nothing keeps the login screen
# it had before. The realm URL, client and wording all come from the
# environment so nothing about a particular identity provider is baked in.
cat > /app/ui/build/config.js <<EOF
window.__EP_CONFIG__ = {
  rootPath: "${ROOT_PATH}",
  affinitiesEpUuid: "${AFFINITIES_EP_UUID}",
  oidcEnabled: "${OIDC_ENABLED:-False}",
  oidcIssuer: "${OIDC_ISSUER}",
  oidcClientId: "${OIDC_CLIENT_ID}",
  oidcScope: "${OIDC_SCOPE}",
  oidcButtonLabel: "${OIDC_BUTTON_LABEL}",
  oidcHelpText: "${OIDC_HELP_TEXT}"
};
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
    # Use a relative redirect so the non-standard port (e.g. :8002) is
    # preserved — \$host drops it, sending the browser to port 80.
    location = ${ROOT_PATH}/ui {
        absolute_redirect off;
        return 301 ${ROOT_PATH}/ui/;
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
