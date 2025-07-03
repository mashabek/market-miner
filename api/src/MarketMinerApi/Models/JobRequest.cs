using System.ComponentModel.DataAnnotations;

namespace MarketMinerApi.Models;

public record JobRequest
{
    [Required]
    public required string Domain { get; init; }

    [Required]
    [MinLength(1)]
    public required List<string> Urls { get; init; }
} 