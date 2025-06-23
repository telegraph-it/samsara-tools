# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based toolkit for interacting with the Samsara API, focused on fleet management operations including gateway tracking, asset management, and geofence querying. The project contains three main scripts that serve different purposes in fleet monitoring and reporting.

## Development Setup

### Dependencies and Environment
- Python 3.8+ required
- Uses `pyproject.toml` for modern Python packaging with uv support
- Install dependencies: `pip install -r requirements.txt` or `uv sync`
- Virtual environment located at `.venv/` (already set up)
- API authentication via `.env` file with `SAMSARA_API_TOKEN`

### Project Structure
```
data/
├── cache/          # API response caching (1 hour TTL)
│   ├── gateways.json
│   └── locations.json
└── output/         # Generated reports and exports
    └── *.csv       # Timestamped output files
```

## Core Architecture

### Main Scripts

**active_gateways.py** - Advanced gateway monitoring with location tracking
- Comprehensive gateway status analysis with geocoding
- Implements sophisticated rate limiting and caching
- Concurrent API calls with ThreadPoolExecutor
- Location history retrieval and reverse geocoding
- Supports filtering by inactivity threshold (days)
- Usage: `python active_gateways.py --days 3 --filename report_name`

**list_assets.py** - Simple gateway listing tool  
- Basic gateway enumeration and connection status
- Lightweight alternative to active_gateways.py
- Usage: `python list_assets.py --output gateway_summary`

**query_geofences.py** - Geofence management by tags
- Tag-based geofence querying with pagination support
- Exports both JSON and CSV formats
- Usage: `python query_geofences.py [tag_name]` (defaults to "Maas")

### Key Classes and Patterns

**RateLimiter Class** (active_gateways.py:26-101)
- Exponential backoff with jitter for API rate limiting
- Configurable retry logic for 429 responses
- Minimum interval enforcement between requests

**CacheManager Class** (active_gateways.py:103-138)
- File-based JSON caching with timestamps
- 1-hour cache duration for API responses
- Automatic cache directory creation

**SamsaraAPIClient/SamsaraClient Classes**
- Standardized API interaction patterns
- Bearer token authentication
- Error handling with detailed logging

## API Integration Patterns

### Authentication
- All scripts use Bearer token authentication via `SAMSARA_API_TOKEN` environment variable
- Fallback to command-line `--token` argument
- Token validation on startup where implemented

### Rate Limiting Strategy
- Base delay of 1 second, max delay of 60 seconds
- Maximum 5 retry attempts for rate-limited requests
- Concurrent request limiting (5 workers for API calls, 5 for geocoding)
- Batch processing with delays between batches

### Data Processing
- Consistent timestamp formatting: `YYYY-MM-DD HH:MM:SS UTC`
- Geocoding via OpenStreetMap/Nominatim with conservative rate limits
- Location history retrieval spanning 5 years (configurable)
- Structured output with consistent column naming

## Common Development Tasks

### Running Scripts
```bash
# Monitor inactive gateways (most common use case)
python active_gateways.py --days 3 --filename weekly_report

# Clear cache and run fresh
python active_gateways.py --clear-cache --days 1

# Query specific geofences
python query_geofences.py "MaaS"

# Simple gateway listing
python list_assets.py --output current_gateways
```

### Cache Management
- Cache files stored in `data/cache/` with 1-hour TTL
- Use `--clear-cache` flag to force fresh API calls
- Manual cache clearing: remove `data/cache/*.json` files

### Output Management
- All outputs timestamped automatically: `filename_YYYYMMDD_HHMMSS.csv`
- Results saved to `data/output/` directory
- Both CSV and JSON formats supported (geofence queries)

## Development Standards

### Error Handling
- Comprehensive try/catch around all API calls
- Rate limit detection and automatic retry
- Graceful degradation when optional data unavailable
- Detailed error logging with context

### Code Patterns
- Docstrings for all public methods and classes
- Snake_case for variables and functions
- Type hints where beneficial (query_geofences.py)
- Configuration constants at module level
- Consistent import organization

### Data Validation
- Coordinate validation before geocoding attempts
- Date parsing with timezone awareness
- API response structure validation
- Fallback values for missing data ("N/A", "Unknown")

## Environment Configuration

Required environment variables:
- `SAMSARA_API_TOKEN`: Samsara API bearer token for authentication

Optional configurations:
- Modify cache duration: `CACHE_DURATION` constant in active_gateways.py
- Adjust worker limits: `MAX_API_WORKERS`, `MAX_GEOCODING_WORKERS` constants
- Location history period: `LOCATION_HISTORY_DAYS` constant (default: 1825 days)