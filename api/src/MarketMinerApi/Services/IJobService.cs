using MarketMinerApi.Models;

namespace MarketMinerApi.Services;

public interface IJobService
{
    Task<string> CreateJobAsync(JobRequest request);
    Task<Job?> GetJobAsync(string jobId);
} 