#!/usr/bin/env python3
"""
Example usage of the route data features.
"""
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from samsara_tools import RouteService

# Load environment variables
load_dotenv()
api_token = os.getenv('SAMSARA_API_TOKEN')

if not api_token:
    print("Please set SAMSARA_API_TOKEN in your .env file")
    exit(1)

# Create route service
service = RouteService(api_token)

# Example 1: Query routes for the last 7 days
print("Example 1: Querying routes from the last 7 days")
print("=" * 50)

end_time = datetime.now()
start_time = end_time - timedelta(days=7)

routes = service.query_routes(
    start_time=start_time,
    end_time=end_time,
    include_points=False  # Set to True to include GPS track points
)

# Print summary
service.print_route_summary(routes)

# Save to JSON
if routes:
    json_file = service.save_routes(routes, format='json')
    print(f"\nRoutes saved to: {json_file}")

# Example 2: Get a specific route with GPS points
if routes and len(routes) > 0:
    print("\n\nExample 2: Getting detailed info for the first route")
    print("=" * 50)
    
    first_route_id = routes[0].id
    detailed_route = service.get_route_by_id(first_route_id, include_points=True)
    
    if detailed_route:
        print(f"Route: {detailed_route.name or detailed_route.id}")
        print(f"GPS Points: {len(detailed_route.points)}")
        print(f"Stops: {len(detailed_route.stops)}")
        
        # Save as GPX for GPS visualization
        gpx_file = service.save_routes([detailed_route], format='gpx')
        print(f"\nRoute saved as GPX to: {gpx_file}")

# Example 3: Query routes for a specific vehicle
print("\n\nExample 3: Query routes for a specific vehicle")
print("=" * 50)
print("To use this example, replace 'VEHICLE_ID' with an actual vehicle ID")
print("Example: routes = service.query_routes(start_time, end_time, vehicle_id='12345')")

# Example 4: Export routes to CSV
if routes:
    print("\n\nExample 4: Exporting routes to CSV")
    print("=" * 50)
    
    csv_file = service.save_routes(routes, format='csv')
    print(f"Routes exported to CSV: {csv_file}")
    print("Note: CSV format only includes summary data, not GPS points")
