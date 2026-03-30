# National Data Platform - EndPoint Admin Console (NDP-EP Frontend)

A React-based **administrative web interface** for managing and monitoring [NDP-EP API](https://github.com/national-data-platform/ep-api) instances. This console provides system administrators with comprehensive tools to manage datasets, organizations, services, and system health across multiple CKAN environments.

## 🌐 About the NDP-EP Admin Console

The NDP-EP Admin Console is designed specifically for **system administrators** who need to:

- **🔧 Manage API Instances**: Configure and monitor NDP-EP API deployments
- **📊 Administer Catalogs**: Control datasets across Local CKAN, Pre-CKAN, and NDP Central environments  
- **🏢 Organization Management**: Create and manage organizational structures within CKAN instances
- **🔍 System Monitoring**: Monitor API health, connectivity, and service status
- **⚙️ Service Registry**: Register and manage microservices, APIs, and applications
- **🚀 Resource Administration**: Bulk manage Kafka topics, S3 resources, and URL resources
- **☁️ S3 Management**: Direct S3 bucket and object management with presigned URLs (API v0.2.0+)

## ⚡ Quick Start for Administrators

Deploy the admin console for your NDP-EP API instance in under 5 minutes:

### Prerequisites
- Docker (for production deployment)
- Running [NDP-EP API](https://hub.docker.com/r/rbardaji/ndp-ep-api) instance

### Option 1: Docker Hub (Production Ready)

```bash
# Deploy latest version with S3 management features (v0.2.0+)
docker run -p 3000:80 \
  -e NDP_EP_API="https://your-ndp-api.company.com" \
  rbardaji/ndp-ep-frontend:latest

# Or deploy specific version
docker run -p 3000:80 \
  -e NDP_EP_API="https://your-ndp-api.company.com" \
  rbardaji/ndp-ep-frontend:0.2.0
```

**Access the admin console**: http://localhost:3000

### Option 2: Local Development

```bash
# Clone the repository
git clone https://github.com/your-username/ndp-ep-frontend.git
cd ndp-ep-frontend

# Install dependencies
npm install

# Configure API endpoint (optional)
echo "REACT_APP_API_BASE_URL=http://localhost:8003" > .env.local

# Start development server
npm start
```
**Access the admin console**: http://localhost:3000

#### Option 3: Docker Compose (Recommended)
Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  frontend:
    image: rbardaji/ndp-ep-frontend:0.2.0  # Use specific version for S3 features
    ports:
      - "80:80"
    environment:
      - NDP_EP_API=https://api.your-domain.com
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:80/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

Run with:
```bash
docker-compose up -d
```

#### Option 4: Full Stack with Backend
```yaml
version: '3.8'

services:
  frontend:
    image: rbardaji/ndp-ep-frontend:0.2.0  # S3 management features
    ports:
      - "3000:80"
    environment:
      - NDP_EP_API=http://backend:8000
    depends_on:
      - backend
    restart: unless-stopped

  backend:
    image: rbardaji/ndp-ep-api:0.2.0  # Compatible API version for S3 features
    ports:
      - "8001:8000"
    environment:
      - ORGANIZATION=Your Organization
      - CKAN_LOCAL_ENABLED=False
      - PRE_CKAN_ENABLED=True
      - PRE_CKAN_URL=https://preckan.nationaldataplatform.org
      - PRE_CKAN_API_KEY=your-api-key
    restart: unless-stopped
```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `NDP_EP_API` | Backend API URL | `http://localhost:8003` | `https://api.example.com` |

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

For more information about the National Data Platform, visit [nationaldataplatform.org](https://nationaldataplatform.org)