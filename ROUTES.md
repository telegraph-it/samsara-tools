# Route Data Feature Documentation

## Overview

The route data feature allows you to query, analyze, and export route information from the Samsara API. This includes:
- Route metadata (driver, vehicle, times, distance, duration)
- GPS track points along the route
- Stop information with arrival/departure times
- Export capabilities in JSON, CSV, and GPX formats

## Usage

### Command Line Interface

#### Query Routes by Time Range

```bash
# Basic query for last 7 days
uv run samsara-tools routes query --start "2024-01-01"

# Query with specific end date
uv run samsara-tools routes query --start "2024-01-01" --end "2024-01-31"

# Include GPS track points (increases query time)
uv run samsara-tools routes query --start "2024-01-01" --include-points

# Filter by vehicle
uv run samsara-tools routes query --start "2024-01-01" --vehicle "vehicle_id_123"

# Filter by driver
uv run samsara-tools routes query --start "2024-01-01" --driver "driver_id_456"

# Export to different formats
uv run samsara-tools routes query --start "2024-01-01" --format csv --output routes.csv
uv run samsara-tools routes query --start "2024-01-01" --format gpx --output routes.gpx
```

#### Get Specific Route

```bash
# Get route by ID
uv run samsara-tools routes get route_id_123

# Include GPS points
uv run samsara-tools routes get route_id_123 --include-points

# Export as GPX
uv run samsara-tools routes get route_id_123 --format gpx --output route.gpx
```

### Python API

```python
from datetime import datetime, timedelta
from samsara_tools import RouteService

# Initialize service
service = RouteService(api_token)

# Query routes
end_time = datetime.now()
start_time = end_time - timedelta(days=7)

routes = service.query_routes(
    start_time=start_time,
    end_time=end_time,
    vehicle_id="optional_vehicle_id",
    driver_id="optional_driver_id",
    include_points=True  # Include GPS track data
)

# Get specific route
route = service.get_route_by_id("route_id_123", include_points=True)

# Save routes
service.save_routes(routes, format='json', output_file=Path('routes.json'))
service.save_routes(routes, format='csv', output_file=Path('routes.csv'))
service.save_routes(routes, format='gpx', output_file=Path('routes.gpx'))
```

## Export Formats

### JSON
- Complete route data including all metadata, stops, and GPS points
- Suitable for further processing or archival

### CSV
- Summary data only (no GPS points or stop details)
- Includes: route ID, name, driver, vehicle, times, distance, duration
- Suitable for reporting and analysis in spreadsheet applications

### GPX
- GPS Exchange Format for use with mapping software
- Includes GPS track points and stops as waypoints
- Can be imported into Google Earth, GPS devices, and mapping applications
- Multiple routes create separate GPX files in a directory

## Data Models

### Route
- `id`: Unique route identifier
- `name`: Optional route name
- `driver_id` / `driver_name`: Driver information
- `vehicle_id` / `vehicle_name`: Vehicle information
- `start_time` / `end_time`: Route timing
- `distance_meters`: Total distance traveled
- `duration_seconds`: Total route duration
- `stops`: List of RouteStop objects
- `points`: List of RoutePoint objects (GPS track)

### RouteStop
- `id`: Stop identifier
- `name`: Stop name
- `address`: Stop address
- `latitude` / `longitude`: GPS coordinates
- `arrival_time` / `departure_time`: Stop timing
- `duration_seconds`: Time spent at stop

### RoutePoint
- `latitude` / `longitude`: GPS coordinates
- `time`: Timestamp
- `speed`: Vehicle speed (optional)
- `heading`: Vehicle heading/direction (optional)

## Performance Considerations

- Basic route queries are fast and cached
- Including GPS points (`--include-points`) significantly increases query time
- Large time ranges may require pagination
- Results are cached to reduce API calls

## API Endpoints Used

- `GET /fleet/routes` - List routes with filtering
- `GET /fleet/routes/{id}` - Get route details
- `GET /fleet/routes/{id}/path` - Get GPS track and stops

Note: The exact Samsara API endpoints may vary. Refer to the official Samsara API documentation for the most up-to-date information.
