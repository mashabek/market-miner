using Google.Cloud.Firestore;
using Google.Cloud.Tasks.V2;
using MarketMinerApi.Models;
using MarketMinerApi.Services;
using Microsoft.AspNetCore.Mvc;
using System.ComponentModel.DataAnnotations;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

// Configure Firestore
var gcpProject = builder.Configuration["GCP_PROJECT"] ?? Environment.GetEnvironmentVariable("GCP_PROJECT");
if (string.IsNullOrEmpty(gcpProject))
{
    throw new InvalidOperationException("GCP_PROJECT environment variable is required");
}

builder.Services.AddSingleton(provider => FirestoreDb.Create(gcpProject));
builder.Services.AddSingleton(provider => CloudTasksClient.Create());
builder.Services.AddScoped<IJobService, JobService>();

// Configure JSON options for better API responses
builder.Services.ConfigureHttpJsonOptions(options =>
{
    options.SerializerOptions.PropertyNamingPolicy = System.Text.Json.JsonNamingPolicy.CamelCase;
});

var app = builder.Build();

// Configure the HTTP request pipeline
if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

// Minimal API endpoints
app.MapPost("/jobs", async (
    [FromBody] JobRequest request,
    IJobService jobService,
    ILogger<Program> logger) =>
{
    try
    {
        // Validate request
        var validationResults = new List<ValidationResult>();
        var validationContext = new ValidationContext(request);
        
        if (!Validator.TryValidateObject(request, validationContext, validationResults, true))
        {
            var errors = validationResults.Select(v => v.ErrorMessage).ToArray();
            logger.LogWarning("Invalid job request: {Errors}", string.Join(", ", errors));
            return Results.BadRequest(new { errors });
        }

        // Validate URLs
        foreach (var url in request.Urls)
        {
            if (!Uri.TryCreate(url, UriKind.Absolute, out _))
            {
                logger.LogWarning("Invalid URL in request: {Url}", url);
                return Results.BadRequest(new { errors = new[] { $"Invalid URL: {url}" } });
            }
        }

        var jobId = await jobService.CreateJobAsync(request);
        logger.LogInformation("Created job {JobId} for domain {Domain}", jobId, request.Domain);
        
        return Results.Created($"/jobs/{jobId}", new JobResponse { JobId = jobId });
    }
    catch (InvalidOperationException ex)
    {
        logger.LogError(ex, "Service unavailable while creating job");
        return Results.Problem(
            title: "Service Unavailable",
            detail: ex.Message,
            statusCode: 503);
    }
    catch (Exception ex)
    {
        logger.LogError(ex, "Unexpected error while creating job");
        return Results.Problem(
            title: "Internal Server Error", 
            detail: "An unexpected error occurred",
            statusCode: 500);
    }
})
.WithName("CreateJob")
.WithSummary("Create a new scraping job")
.WithDescription("Creates a new job for scraping the specified URLs from a domain")
.WithOpenApi();

app.MapGet("/jobs/{id}", async (
    string id,
    IJobService jobService,
    ILogger<Program> logger) =>
{
    try
    {
        if (!Guid.TryParse(id, out _))
        {
            logger.LogWarning("Invalid job ID format: {JobId}", id);
            return Results.BadRequest(new { error = "Invalid job ID format" });
        }

        var job = await jobService.GetJobAsync(id);
        
        if (job == null)
        {
            logger.LogWarning("Job not found: {JobId}", id);
            return Results.NotFound(new { error = "Job not found" });
        }

        logger.LogInformation("Retrieved job {JobId}", id);
        return Results.Ok(job);
    }
    catch (InvalidOperationException ex)
    {
        logger.LogError(ex, "Service unavailable while retrieving job {JobId}", id);
        return Results.Problem(
            title: "Service Unavailable",
            detail: ex.Message,
            statusCode: 503);
    }
    catch (Exception ex)
    {
        logger.LogError(ex, "Unexpected error while retrieving job {JobId}", id);
        return Results.Problem(
            title: "Internal Server Error",
            detail: "An unexpected error occurred",
            statusCode: 500);
    }
})
.WithName("GetJob")
.WithSummary("Get a job by ID")
.WithDescription("Retrieves the details of a specific job by its ID")
.WithOpenApi();

// Health check endpoint
app.MapGet("/health", () => Results.Ok(new { status = "healthy", timestamp = DateTime.UtcNow }))
    .WithName("HealthCheck")
    .WithSummary("Health check endpoint")
    .WithOpenApi();

app.Run();
