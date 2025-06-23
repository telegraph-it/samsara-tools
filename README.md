# Samsara API Tools

A comprehensive Python toolkit for interacting with the Samsara API. Query gateways, geofences, tags, and more with a clean, professional interface.

## Features

- **Gateway Management**: List and monitor gateway connection status
- **Geofence Queries**: Find geofences by tag with detailed location data
- **Tag Management**: List and search through all available tags
- **Rate Limiting**: Built-in API rate limiting with exponential backoff
- **Caching**: Smart caching to reduce API calls and improve performance
- **Multiple Output Formats**: Export data to JSON and CSV formats
- **CLI Interface**: Easy-to-use command-line interface
- **Python API**: Use as a library in your own Python projects

## Installation

### Using uv (recommended)

```bash
git clone https://github.com/yourusername/samsara-api-tools.git
cd samsara-api-tools
uv sync
```

### Using pip

```bash
git clone https://github.com/yourusername/samsara-api-tools.git
cd samsara-api-tools
pip install -e .
```

## Configuration

Create a `.env` file in the project root with your Samsara API token:

```env
SAMSARA_API_TOKEN=your_api_token_here
```

## Usage

### Command Line Interface

The package provides a unified CLI with multiple commands:

#### List all tags
```bash
# Basic list
uv run samsara-tools list-tags

# With creation details
uv run samsara-tools list-tags --show-details
```

#### Query geofences by tag
```bash
# View geofences for a tag
uv run samsara-tools query-geofences "Maas"

# Save results to files
uv run samsara-tools query-geofences "Maas" --save
```

#### List gateways
```bash
# List all gateways with cached data
uv run samsara-tools list-gateways

# Force fresh data (skip cache)
uv run samsara-tools list-gateways --no-cache
```

### Python API

Use the package as a library in your Python code:

```python
from samsara_tools import SamsaraClient, SamsaraGeofenceQuery
import os

# Initialize client
api_token = os.getenv('SAMSARA_API_TOKEN')
client = SamsaraClient(api_token)

# List all tags
tags = client.get_all_tags()
print(f"Found {len(tags)} tags")

# Query geofences
geo_client = SamsaraGeofenceQuery(api_token)
geofences = geo_client.query_geofences_by_tag("Maas")

# Save results
if geofences:
    saved_files = geo_client.save_results(geofences, "Maas")
    print(f"Saved to: {saved_files}")
```

## Project Structure

```
samsara-api-tools/
├── src/samsara_tools/           # Main package
│   ├── __init__.py             # Package exports
│   ├── cli/                    # Command-line interface
│   │   ├── __init__.py
│   │   └── main.py            # CLI entry point
│   └── core/                   # Core functionality
│       ├── __init__.py
│       ├── client.py          # Base API client
│       └── geofence_query.py  # Geofence querying
├── legacy/                     # Original scripts (for reference)
├── tests/                      # Test suite
├── docs/                       # Documentation
├── examples/                   # Usage examples
├── data/                       # Data storage
│   ├── cache/                 # API response cache
│   └── output/                # Generated files
├── pyproject.toml             # Project configuration
├── README.md                  # This file
├── LICENSE                    # MIT License
└── .env                       # API configuration (create this)
```

## API Documentation

### SamsaraClient

Base client for Samsara API interactions.

```python
client = SamsaraClient(api_token, base_url="https://api.samsara.com")

# Verify API access
success, message = client.verify_api_access()

# Get all gateways
gateways = client.get_gateways()

# Get all tags
tags = client.get_all_tags()

# Find specific tag
tag = client.find_tag_by_name("Maas")
```

### SamsaraGeofenceQuery

Specialized client for geofence operations.

```python
geo_client = SamsaraGeofenceQuery(api_token)

# Query geofences by tag
geofences = geo_client.query_geofences_by_tag("Maas")

# Print summary to console
geo_client.print_geofence_summary(geofences, "Maas")

# Save results
saved_files = geo_client.save_results(geofences, "Maas")
```

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/yourusername/samsara-api-tools.git
cd samsara-api-tools

# Install with development dependencies
uv sync --group dev

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html
```

### Code Formatting

```bash
# Format code
uv run black src tests

# Sort imports
uv run isort src tests

# Type checking
uv run mypy src
```

## Legacy Scripts

The original standalone scripts are preserved in the `legacy/` folder:
- `active_gateways.py` - Original gateway analysis script
- `list_assets.py` - Original asset listing script  
- `query_geofences.py` - Original geofence query script
- `list_tags.py` - Original tag listing script

These can still be run directly if needed, but the new CLI interface is recommended.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- Create an issue on GitHub for bugs or feature requests
- Check the `examples/` directory for usage examples
- Review the `legacy/` scripts for reference implementations