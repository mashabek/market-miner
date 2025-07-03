# Build stage
FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build
WORKDIR /src

# Copy project file and restore dependencies
COPY src/MarketMinerApi/MarketMinerApi.csproj src/MarketMinerApi/
RUN dotnet restore src/MarketMinerApi/MarketMinerApi.csproj

# Copy source code and build
COPY src/MarketMinerApi/ src/MarketMinerApi/
RUN dotnet publish src/MarketMinerApi/MarketMinerApi.csproj -c Release -o /app --no-restore

# Runtime stage
FROM mcr.microsoft.com/dotnet/aspnet:9.0
WORKDIR /app

# Copy built application
COPY --from=build /app .

# Configure environment
ENV ASPNETCORE_URLS=http://0.0.0.0:8080
ENV ASPNETCORE_ENVIRONMENT=Production

# Expose port
EXPOSE 8080

# Start application
ENTRYPOINT ["dotnet", "MarketMinerApi.dll"] 