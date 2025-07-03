using Google.Cloud.Firestore;
using Google.Cloud.Tasks.V2;
using MarketMinerApi.Models;
using MarketMinerApi.Services;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using Moq;
using Xunit;

namespace MarketMinerApi.Tests.Services;

public class JobServiceTests
{
    private readonly Mock<FirestoreDb> _mockFirestoreDb;
    private readonly Mock<CloudTasksClient> _mockTasksClient;
    private readonly Mock<IConfiguration> _mockConfiguration;
    private readonly Mock<ILogger<JobService>> _mockLogger;
    private readonly JobService _jobService;

    public JobServiceTests()
    {
        _mockFirestoreDb = new Mock<FirestoreDb>();
        _mockTasksClient = new Mock<CloudTasksClient>();
        _mockConfiguration = new Mock<IConfiguration>();
        _mockLogger = new Mock<ILogger<JobService>>();

        // Setup configuration defaults
        _mockConfiguration.Setup(c => c["GCP_PROJECT"]).Returns("test-project");
        _mockConfiguration.Setup(c => c["REGION"]).Returns("us-central1");
        _mockConfiguration.Setup(c => c["SPIDER_JOB"]).Returns("test-spider-job");
        _mockConfiguration.Setup(c => c["TASK_INVOKER_SA"]).Returns("test-sa@test-project.iam.gserviceaccount.com");

        _jobService = new JobService(
            _mockFirestoreDb.Object,
            _mockTasksClient.Object,
            _mockConfiguration.Object,
            _mockLogger.Object);
    }

    [Fact]
    public async Task CreateJobAsync_ValidRequest_ReturnsJobId()
    {
        // Arrange
        var request = new JobRequest
        {
            Domain = "example.com",
            Urls = new List<string> { "https://example.com/product1", "https://example.com/product2" }
        };

        var mockDocRef = new Mock<DocumentReference>();
        var mockCollection = new Mock<CollectionReference>();
        
        _mockFirestoreDb.Setup(db => db.Collection("jobs"))
            .Returns(mockCollection.Object);
        
        mockCollection.Setup(c => c.Document(It.IsAny<string>()))
            .Returns(mockDocRef.Object);

        mockDocRef.Setup(d => d.SetAsync(It.IsAny<Job>(), null, default))
            .Returns(Task.FromResult(new WriteResult()));

        // Mock queue operations
        var mockQueue = new Mock<Queue>();
        _mockTasksClient.Setup(c => c.GetQueueAsync(It.IsAny<string>(), default))
            .ReturnsAsync(mockQueue.Object);

        _mockTasksClient.Setup(c => c.CreateTaskAsync(It.IsAny<CreateTaskRequest>(), default))
            .ReturnsAsync(new Google.Cloud.Tasks.V2.Task());

        // Act
        var result = await _jobService.CreateJobAsync(request);

        // Assert
        Assert.NotNull(result);
        Assert.True(Guid.TryParse(result, out _));

        // Verify Firestore operations
        mockDocRef.Verify(d => d.SetAsync(
            It.Is<Job>(j => j.Domain == request.Domain && 
                           j.Urls.SequenceEqual(request.Urls) && 
                           j.Status == JobStatus.Queued),
            null, default), Times.Once);

        // Verify task creation
        _mockTasksClient.Verify(c => c.CreateTaskAsync(
            It.IsAny<CreateTaskRequest>(), default), Times.Once);
    }

    [Fact]
    public async Task CreateJobAsync_TaskEnqueueFails_ThrowsAndCleansUp()
    {
        // Arrange
        var request = new JobRequest
        {
            Domain = "example.com",
            Urls = new List<string> { "https://example.com/product1" }
        };

        var mockDocRef = new Mock<DocumentReference>();
        var mockCollection = new Mock<CollectionReference>();
        
        _mockFirestoreDb.Setup(db => db.Collection("jobs"))
            .Returns(mockCollection.Object);
        
        mockCollection.Setup(c => c.Document(It.IsAny<string>()))
            .Returns(mockDocRef.Object);

        mockDocRef.Setup(d => d.SetAsync(It.IsAny<Job>(), null, default))
            .Returns(Task.FromResult(new WriteResult()));

        mockDocRef.Setup(d => d.DeleteAsync(null, default))
            .Returns(Task.FromResult(new WriteResult()));

        // Mock queue operations to fail
        _mockTasksClient.Setup(c => c.GetQueueAsync(It.IsAny<string>(), default))
            .ThrowsAsync(new Exception("Task enqueue failed"));

        // Act & Assert
        var exception = await Assert.ThrowsAsync<InvalidOperationException>(
            () => _jobService.CreateJobAsync(request));

        Assert.Contains("Failed to create job", exception.Message);

        // Verify cleanup was attempted
        mockDocRef.Verify(d => d.DeleteAsync(null, default), Times.Once);
    }

    [Fact]
    public async Task GetJobAsync_ExistingJob_ReturnsJob()
    {
        // Arrange
        var jobId = Guid.NewGuid().ToString();
        var expectedJob = new Job
        {
            Id = jobId,
            Domain = "example.com",
            Urls = new List<string> { "https://example.com/product1" },
            Status = JobStatus.Queued,
            CreatedAt = Timestamp.GetCurrentTimestamp(),
            UpdatedAt = Timestamp.GetCurrentTimestamp()
        };

        var mockDocRef = new Mock<DocumentReference>();
        var mockCollection = new Mock<CollectionReference>();
        var mockSnapshot = new Mock<DocumentSnapshot>();

        _mockFirestoreDb.Setup(db => db.Collection("jobs"))
            .Returns(mockCollection.Object);
        
        mockCollection.Setup(c => c.Document(jobId))
            .Returns(mockDocRef.Object);

        mockDocRef.Setup(d => d.GetSnapshotAsync(default))
            .ReturnsAsync(mockSnapshot.Object);

        mockSnapshot.Setup(s => s.Exists).Returns(true);
        mockSnapshot.Setup(s => s.ConvertTo<Job>()).Returns(expectedJob);

        // Act
        var result = await _jobService.GetJobAsync(jobId);

        // Assert
        Assert.NotNull(result);
        Assert.Equal(expectedJob.Id, result.Id);
        Assert.Equal(expectedJob.Domain, result.Domain);
        Assert.Equal(expectedJob.Status, result.Status);
    }

    [Fact]
    public async Task GetJobAsync_NonExistentJob_ReturnsNull()
    {
        // Arrange
        var jobId = Guid.NewGuid().ToString();

        var mockDocRef = new Mock<DocumentReference>();
        var mockCollection = new Mock<CollectionReference>();
        var mockSnapshot = new Mock<DocumentSnapshot>();

        _mockFirestoreDb.Setup(db => db.Collection("jobs"))
            .Returns(mockCollection.Object);
        
        mockCollection.Setup(c => c.Document(jobId))
            .Returns(mockDocRef.Object);

        mockDocRef.Setup(d => d.GetSnapshotAsync(default))
            .ReturnsAsync(mockSnapshot.Object);

        mockSnapshot.Setup(s => s.Exists).Returns(false);

        // Act
        var result = await _jobService.GetJobAsync(jobId);

        // Assert
        Assert.Null(result);
    }

    [Fact]
    public async Task GetJobAsync_FirestoreException_ThrowsInvalidOperationException()
    {
        // Arrange
        var jobId = Guid.NewGuid().ToString();

        var mockDocRef = new Mock<DocumentReference>();
        var mockCollection = new Mock<CollectionReference>();

        _mockFirestoreDb.Setup(db => db.Collection("jobs"))
            .Returns(mockCollection.Object);
        
        mockCollection.Setup(c => c.Document(jobId))
            .Returns(mockDocRef.Object);

        mockDocRef.Setup(d => d.GetSnapshotAsync(default))
            .ThrowsAsync(new Exception("Firestore error"));

        // Act & Assert
        var exception = await Assert.ThrowsAsync<InvalidOperationException>(
            () => _jobService.GetJobAsync(jobId));

        Assert.Contains("Failed to retrieve job", exception.Message);
    }

    [Theory]
    [InlineData("")]
    [InlineData(null)]
    public async Task CreateJobAsync_MissingConfiguration_ThrowsInvalidOperationException(string? configValue)
    {
        // Arrange
        var request = new JobRequest
        {
            Domain = "example.com",
            Urls = new List<string> { "https://example.com/product1" }
        };

        _mockConfiguration.Setup(c => c["GCP_PROJECT"]).Returns(configValue);

        // Act & Assert
        var exception = await Assert.ThrowsAsync<InvalidOperationException>(
            () => _jobService.CreateJobAsync(request));

        Assert.Contains("GCP_PROJECT environment variable is required", exception.Message);
    }
} 