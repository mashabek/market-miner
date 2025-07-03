# MarketMiner API

A container-ready .NET 9 Minimal API for managing price-scraping jobs. This API accepts job requests, persists them in Google Cloud Firestore, and enqueues Cloud Tasks to trigger Cloud Run Spider Jobs.

## Features

- ✅ **Minimal API** built with .NET 9
- ✅ **Google Cloud Firestore** integration for job persistence
- ✅ **Cloud Tasks** integration for job queuing
- ✅ **Container-ready** with multi-stage Dockerfile
- ✅ **Health checks** and comprehensive error handling
- ✅ **Unit tests** with good coverage
- ✅ **Swagger/OpenAPI** documentation
- ✅ **Infrastructure as Code** (Terraform + gcloud scripts)

## API Endpoints

| Method | Endpoint      | Description              | Request Body                                           | Response              |
|--------|---------------|--------------------------|-------------------------------------------------------|-----------------------|
| POST   | `/jobs`       | Create a new scraping job| `{"domain": "example.com", "urls": ["https://..."]}`  | `{"jobId": "<guid>"}` |
| GET    | `/jobs/{id}`  | Get job details          | -                                                     | Job JSON or 404       |
| GET    | `/health`     | Health check             | -                                                     | `{"status": "healthy"}` |

## Data Model

### Job Document (Firestore)
```json
{
  "id": "<GUID>",
  "domain": "example.com",
  "urls": ["https://example.com/product1"],
  "status": "QUEUED",
  "createdAt": "<timestamp>",
  "updatedAt": "<timestamp>"
}
```

**Status Values:** `QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`

## Prerequisites

- .NET 9 SDK
- Docker (for containerization)
- Google Cloud SDK (gcloud CLI)
- Google Cloud Project with billing enabled

## Environment Variables

Set these environment variables when running the application:

| Variable           | Description                              | Example                                            |
|-------------------|------------------------------------------|----------------------------------------------------|
| `GCP_PROJECT`     | Google Cloud Project ID                  | `my-scraper-project`                               |
| `REGION`          | Google Cloud region                      | `europe-west4`                                     |
| `SPIDER_JOB`      | Cloud Run Job name for spider execution  | `spider-runner`                                    |
| `TASK_INVOKER_SA` | Service Account email for task invocation| `tasks-invoker@my-project.iam.gserviceaccount.com` |

## Local Development

### 1. Clone and Build

```bash
# Navigate to the project directory
cd MarketMinerApi

# Restore dependencies
dotnet restore

# Build the solution
dotnet build

# Run tests
dotnet test
```

### 2. Run Locally

```bash
# Set environment variables (adjust values for your project)
export GCP_PROJECT="your-project-id"
export REGION="europe-west4"
export SPIDER_JOB="spider-runner"
export TASK_INVOKER_SA="tasks-invoker@your-project-id.iam.gserviceaccount.com"

# Run the API
dotnet run --project src/MarketMinerApi

# API will be available at: http://localhost:5000
# Swagger UI at: http://localhost:5000/swagger
```

### 3. Test the API

```bash
# Health check
curl http://localhost:5000/health

# Create a job
curl -X POST http://localhost:5000/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "example.com",
    "urls": ["https://example.com/product1", "https://example.com/product2"]
  }'

# Get job details (replace {job-id} with actual ID)
curl http://localhost:5000/jobs/{job-id}
```

## Docker Build

```bash
# Build Docker image
docker build -t market-miner-api .

# Run container
docker run -p 8080:8080 \
  -e GCP_PROJECT="your-project-id" \
  -e REGION="europe-west4" \
  -e SPIDER_JOB="spider-runner" \
  -e TASK_INVOKER_SA="tasks-invoker@your-project-id.iam.gserviceaccount.com" \
  market-miner-api
```

## Deployment

### Option 1: Using Terraform

1. **Setup Terraform variables:**
   ```bash
   cd deploy/terraform
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your values
   ```

2. **Deploy infrastructure:**
   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

3. **Build and deploy the application:**
   ```bash
   # Build and push container
   gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/market-miner-api
   
   # Update Cloud Run service with new image
   gcloud run services update market-miner-api \
     --image gcr.io/YOUR_PROJECT_ID/market-miner-api \
     --region YOUR_REGION
   ```

### Option 2: Using gcloud Scripts

**For Bash/Linux/macOS:**
```bash
cd deploy/scripts
export PROJECT_ID="your-project-id"
export REGION="europe-west4"
export SPIDER_JOB_NAME="spider-runner"
./deploy.sh
```

**For PowerShell/Windows:**
```powershell
cd deploy/scripts
.\deploy.ps1 -ProjectId "your-project-id" -Region "europe-west4" -SpiderJobName "spider-runner"
```

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client App    │───▶│ MarketMiner API │───▶│   Firestore     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │  Cloud Tasks    │───▶│  Spider Job     │
                       │     Queue       │    │  (Cloud Run)    │
                       └─────────────────┘    └─────────────────┘
```

### Cloud Tasks Payload

The API creates Cloud Tasks with the following payload structure:

```json
{
  "httpRequest": {
    "httpMethod": "POST",
    "url": "https://run.googleapis.com/v2/projects/$PROJECT/locations/$REGION/jobs/$SPIDER_JOB:run",
    "headers": { "Content-Type": "application/json" },
    "body": "{ \"jobId\": \"<docId>\" }",
    "oauthToken": {
      "serviceAccountEmail": "$TASK_INVOKER_SA",
      "scope": "https://www.googleapis.com/auth/cloud-platform"
    }
  }
}
```

## Security & IAM

The deployment scripts set up the following IAM permissions:

### Service Accounts Created:
- **`tasks-invoker@PROJECT.iam.gserviceaccount.com`** - Used by Cloud Tasks to invoke Spider Jobs
- **`market-miner-api@PROJECT.iam.gserviceaccount.com`** - Runtime SA for the API service

### Permissions:
- `tasks-invoker` → `roles/run.invoker` on Spider Job
- Cloud Tasks Service Agent → `roles/iam.serviceAccountTokenCreator` on `tasks-invoker`
- `market-miner-api` → `roles/datastore.user`, `roles/cloudtasks.enqueuer`

## Monitoring & Logging

- **Health Endpoint:** `/health` - Returns service status
- **Structured Logging:** All operations are logged with correlation IDs
- **Error Handling:** Comprehensive error handling with proper HTTP status codes
- **Cloud Run Metrics:** Automatic request metrics and logging in Google Cloud Console

## Testing

```bash
# Run all tests
dotnet test

# Run with coverage
dotnet test --collect:"XPlat Code Coverage"

# Run specific test class
dotnet test --filter "JobServiceTests"
```

## Project Structure

```
MarketMinerApi/
├── src/
│   └── MarketMinerApi/
│       ├── Models/           # Data models and DTOs
│       ├── Services/         # Business logic services
│       ├── Program.cs        # Application entry point
│       └── MarketMinerApi.csproj
├── tests/
│   └── MarketMinerApi.Tests/
│       └── Services/         # Unit tests
├── deploy/
│   ├── terraform/           # Infrastructure as Code
│   └── scripts/             # Deployment scripts
├── Dockerfile              # Container definition
├── MarketMinerApi.sln      # Solution file
└── README.md
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add/update tests
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 