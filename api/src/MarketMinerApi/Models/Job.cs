using Google.Cloud.Firestore;

namespace MarketMinerApi.Models;

[FirestoreData]
public class Job
{
    [FirestoreProperty("id")]
    public string Id { get; set; } = string.Empty;

    [FirestoreProperty("domain")]
    public string Domain { get; set; } = string.Empty;

    [FirestoreProperty("urls")]
    public List<string> Urls { get; set; } = new();

    [FirestoreProperty("status")]
    public string Status { get; set; } = JobStatus.Queued;

    [FirestoreProperty("createdAt")]
    public Timestamp CreatedAt { get; set; }

    [FirestoreProperty("updatedAt")]
    public Timestamp UpdatedAt { get; set; }
}

public static class JobStatus
{
    public const string Queued = "QUEUED";
    public const string Running = "RUNNING";
    public const string Completed = "COMPLETED";
    public const string Failed = "FAILED";
} 