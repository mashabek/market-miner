using Google.Api.Gax.ResourceNames;
using Google.Cloud.Firestore;
using Google.Cloud.Tasks.V2;
using MarketMinerApi.Models;
using System.Text;
using System.Text.Json;

namespace MarketMinerApi.Services;

public class JobService : IJobService
{
    private readonly FirestoreDb _firestoreDb;
    private readonly CloudTasksClient _tasksClient;
    private readonly IConfiguration _configuration;
    private readonly ILogger<JobService> _logger;

    private const string JobsCollection = "jobs";

    public JobService(
        FirestoreDb firestoreDb,
        CloudTasksClient tasksClient,
        IConfiguration configuration,
        ILogger<JobService> logger)
    {
        _firestoreDb = firestoreDb;
        _tasksClient = tasksClient;
        _configuration = configuration;
        _logger = logger;
    }

    public async Task<string> CreateJobAsync(JobRequest request)
    {
        var jobId = Guid.NewGuid().ToString();
        var now = Timestamp.GetCurrentTimestamp();

        var job = new Job
        {
            Id = jobId,
            Domain = request.Domain,
            Urls = request.Urls,
            Status = JobStatus.Queued,
            CreatedAt = now,
            UpdatedAt = now
        };

        try
        {
            // Save to Firestore
            var docRef = _firestoreDb.Collection(JobsCollection).Document(jobId);
            await docRef.SetAsync(job);

            // Enqueue Cloud Task
            await EnqueueSpiderTaskAsync(jobId, request.Domain, request.Urls);

            _logger.LogInformation("Successfully created job {JobId} for domain {Domain}", jobId, request.Domain);
            return jobId;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to create job for domain {Domain}", request.Domain);

            // Attempt to clean up the document if task enqueueing failed
            try
            {
                var docRef = _firestoreDb.Collection(JobsCollection).Document(jobId);
                await docRef.DeleteAsync();
            }
            catch (Exception cleanupEx)
            {
                _logger.LogWarning(cleanupEx, "Failed to clean up job document {JobId} after task enqueueing failed", jobId);
            }

            throw new InvalidOperationException("Failed to create job. Service temporarily unavailable.", ex);
        }
    }

    public async Task<Job?> GetJobAsync(string jobId)
    {
        try
        {
            var docRef = _firestoreDb.Collection(JobsCollection).Document(jobId);
            var snapshot = await docRef.GetSnapshotAsync();

            if (!snapshot.Exists)
            {
                return null;
            }

            return snapshot.ConvertTo<Job>();
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to retrieve job {JobId}", jobId);
            throw new InvalidOperationException("Failed to retrieve job.", ex);
        }
    }

    private async System.Threading.Tasks.Task EnqueueSpiderTaskAsync(string jobId, string domain, List<string> urls)
    {
        var gcpProject = _configuration["GCP_PROJECT"] ?? throw new InvalidOperationException("GCP_PROJECT environment variable is required");
        var region = _configuration["REGION"] ?? throw new InvalidOperationException("REGION environment variable is required");
        var spiderJob = _configuration["SPIDER_JOB"] ?? throw new InvalidOperationException("SPIDER_JOB environment variable is required");
        var taskInvokerSa = _configuration["TASK_INVOKER_SA"] ?? throw new InvalidOperationException("TASK_INVOKER_SA environment variable is required");

        var queueName = $"prices-{domain}";
        var fullQueueName = new QueueName(gcpProject, region, queueName).ToString();

        // Create queue if it doesn't exist
        await EnsureQueueExistsAsync(fullQueueName, gcpProject, region, queueName);
        
        // Prepare arguments for the Cloud Run job in the correct overrides structure
        var urlsArg = JsonSerializer.Serialize(urls); // Pass as JSON array string
        var args = new List<string>
        {
            domain,
            "-a",
            $"urls={urlsArg}"
        };
        var runJobBody = new
        {
            overrides = new
            {
                containerOverrides = new[]
                {
                    new {
                        args = args,
                        // env = new[] { new { name = "KEY", value = "VALUE" } } // Uncomment and edit if you want to set env vars
                    }
                },
                taskCount = 1, // Set as needed
                timeout = "3600s" // Set as needed
            }
        };
        var jsonBody = JsonSerializer.Serialize(runJobBody);

        var task = new Google.Cloud.Tasks.V2.Task
        {
            HttpRequest = new Google.Cloud.Tasks.V2.HttpRequest
            {
                HttpMethod = Google.Cloud.Tasks.V2.HttpMethod.Post,
                Url = $"https://run.googleapis.com/v2/projects/{gcpProject}/locations/{region}/jobs/{spiderJob}:run",
                Headers = { { "Content-Type", "application/json" } },
                Body = Google.Protobuf.ByteString.CopyFromUtf8(jsonBody),
                OauthToken = new OAuthToken
                {
                    ServiceAccountEmail = taskInvokerSa
                }
            }
        };

        var request = new CreateTaskRequest
        {
            Parent = fullQueueName,
            Task = task
        };

        await _tasksClient.CreateTaskAsync(request);
        _logger.LogInformation("Successfully enqueued task for job {JobId} in queue {QueueName}", jobId, queueName);
    }

    private async System.Threading.Tasks.Task EnsureQueueExistsAsync(string fullQueueName, string gcpProject, string region, string queueName)
    {
        try
        {
            await _tasksClient.GetQueueAsync(fullQueueName);
        }
        catch (Grpc.Core.RpcException ex) when (ex.StatusCode == Grpc.Core.StatusCode.NotFound)
        {
            _logger.LogInformation("Queue {QueueName} does not exist, creating it", queueName);

            var queue = new Google.Cloud.Tasks.V2.Queue
            {
                Name = fullQueueName,
                RetryConfig = new Google.Cloud.Tasks.V2.RetryConfig
                {
                    MaxAttempts = 7,
                    MaxBackoff = Google.Protobuf.WellKnownTypes.Duration.FromTimeSpan(TimeSpan.FromMinutes(10)),
                    MinBackoff = Google.Protobuf.WellKnownTypes.Duration.FromTimeSpan(TimeSpan.FromSeconds(1)),
                    MaxRetryDuration = Google.Protobuf.WellKnownTypes.Duration.FromTimeSpan(TimeSpan.FromHours(1))
                }
            };

            var locationName = new LocationName(gcpProject, region).ToString();
            var request = new Google.Cloud.Tasks.V2.CreateQueueRequest
            {
                Parent = locationName,
                Queue = queue
            };

            await _tasksClient.CreateQueueAsync(request);
            _logger.LogInformation("Successfully created queue {QueueName}", queueName);
        }
    }
}