#!/bin/sh

# Docker entrypoint script for NDP EndPoint Frontend
# Allows runtime configuration of API URL through environment variables

set -e

echo "🚀 Starting NDP EndPoint Frontend..."

# Default API URL if not provided
DEFAULT_API_URL="http://localhost:8003"
API_URL="${NDP_EP_API:-$DEFAULT_API_URL}"

echo "📡 Configuring API URL: $API_URL"

# Find all JavaScript files in the build directory
JS_FILES=$(find /usr/share/nginx/html/static/js -name "*.js" 2>/dev/null || echo "")

if [ -n "$JS_FILES" ]; then
    echo "🔧 Updating JavaScript files with runtime API URL..."
    
    # Replace the placeholder or default URL in all JavaScript files
    # This replaces any occurrence of the build-time URL with the runtime URL
    for file in $JS_FILES; do
        if [ -f "$file" ]; then
            # Replace the build-time API URL with the runtime API URL
            # We use a unique placeholder or the default URL
            sed -i "s|http://localhost:8003|$API_URL|g" "$file"
            sed -i "s|__NDP_EP_API_URL__|$API_URL|g" "$file"
            echo "  ✅ Updated: $(basename $file)"
        fi
    done
    
    echo "✅ JavaScript files updated successfully"
else
    echo "⚠️  No JavaScript files found, skipping URL replacement"
fi

# Also update any config files if they exist
CONFIG_FILES="/usr/share/nginx/html/config.js /usr/share/nginx/html/env-config.js"
for config_file in $CONFIG_FILES; do
    if [ -f "$config_file" ]; then
        echo "🔧 Updating config file: $(basename $config_file)"
        sed -i "s|__NDP_EP_API_URL__|$API_URL|g" "$config_file"
        echo "  ✅ Updated: $(basename $config_file)"
    fi
done

echo "🌐 Frontend configured with API URL: $API_URL"
echo "🏃 Starting nginx..."

# Execute the original nginx entrypoint
exec /docker-entrypoint.sh "$@"