"""
Route data service for querying and processing Samsara routes.
"""
import json
import logging
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from ..models.route import Route, RoutePoint, RouteStop
from .client import SamsaraClient

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Add console handler if not already present
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class RouteService:
    """Service for querying and processing route data from Samsara API."""
    
    def __init__(self, api_token: str, **kwargs):
        """Initialize the route service with a Samsara client."""
        self.client = SamsaraClient(api_token, **kwargs)
        self.output_dir = Path('data/routes')
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def query_routes(self, start_time: datetime, end_time: datetime,
                    vehicle_id: Optional[str] = None, driver_id: Optional[str] = None,
                    include_points: bool = False, stops_only: bool = False) -> List[Route]:
        """Query routes within a time range and optionally filter by vehicle/driver.
        
        Args:
            start_time: Start of time range
            end_time: End of time range  
            vehicle_id: Optional vehicle ID filter
            driver_id: Optional driver ID filter
            include_points: Fetch detailed GPS points and timing data (may fail for some routes)
            stops_only: Skip fetching detailed path data, only use basic stops from route data
        """
        logger.info(f"Querying routes from {start_time} to {end_time}")
        
        # Get all routes in the time range
        raw_routes = self.client.get_all_routes(
            start_time=start_time,
            end_time=end_time,
            vehicle_id=vehicle_id,
            driver_id=driver_id
        )
        
        routes = []
        for raw_route in raw_routes:
            route = self._convert_to_route_model(raw_route)
            
            # Optionally fetch detailed path data
            if include_points and route.id and not stops_only:
                path_data = self.client.get_route_path(route.id, include_stops=True)
                if path_data:
                    route = self._add_path_data_to_route(route, path_data)
                else:
                    logger.debug(f"Path data not available for route {route.id}, using basic route data")
            
            routes.append(route)
        
        logger.info(f"Found {len(routes)} routes")
        return routes
    
    def get_route_by_id(self, route_id: str, include_points: bool = True, stops_only: bool = False) -> Optional[Route]:
        """Get a specific route by ID."""
        raw_route = self.client.get_route_details(route_id)
        if not raw_route:
            return None
        
        route = self._convert_to_route_model(raw_route)
        
        if include_points and not stops_only:
            path_data = self.client.get_route_path(route_id, include_stops=True)
            if path_data:
                route = self._add_path_data_to_route(route, path_data)
        
        return route
    
    def _convert_to_route_model(self, raw_route: Dict) -> Route:
        """Convert raw API response to Route model."""
        # Debug: Log the available keys (disabled)
        # logger.debug(f"Route keys: {list(raw_route.keys())}")
        
        # Parse times - handle the actual API response format
        start_time = None
        if raw_route.get('scheduledRouteStartTime'):
            start_time = datetime.fromisoformat(raw_route['scheduledRouteStartTime'].replace('Z', '+00:00'))
        elif raw_route.get('startTime'):
            start_time = datetime.fromisoformat(raw_route['startTime'].replace('Z', '+00:00'))
        
        end_time = None
        if raw_route.get('scheduledRouteEndTime'):
            end_time = datetime.fromisoformat(raw_route['scheduledRouteEndTime'].replace('Z', '+00:00'))
        elif raw_route.get('endTime'):
            end_time = datetime.fromisoformat(raw_route['endTime'].replace('Z', '+00:00'))
        
        # Extract location data from first/last stops if available
        start_location = None
        end_location = None
        stops = raw_route.get('stops', [])
        if stops:
            first_stop = stops[0]
            last_stop = stops[-1]
            
            if first_stop.get('address') and 'latitude' in first_stop['address'] and 'longitude' in first_stop['address']:
                start_location = {
                    "lat": first_stop['address']['latitude'],
                    "lng": first_stop['address']['longitude']
                }
            
            if last_stop.get('address') and 'latitude' in last_stop['address'] and 'longitude' in last_stop['address']:
                end_location = {
                    "lat": last_stop['address']['latitude'],
                    "lng": last_stop['address']['longitude']
                }
        
        # Extract driver data from nested structure
        driver_id = None
        driver_name = None
        if raw_route.get('driver'):
            driver_id = raw_route['driver'].get('id')
            driver_name = raw_route['driver'].get('name')
        
        # Create the route object
        route = Route(
            id=raw_route['id'],
            name=raw_route.get('name'),
            driver_id=driver_id,
            driver_name=driver_name,
            vehicle_id=raw_route.get('vehicleId'),  # May not exist in this API response
            vehicle_name=raw_route.get('vehicleName'),  # May not exist in this API response
            start_time=start_time,
            end_time=end_time,
            start_location=start_location,
            end_location=end_location,
            distance_meters=raw_route.get('distanceMeters'),  # May not exist in this API response
            duration_seconds=raw_route.get('durationSeconds')  # May not exist in this API response
        )
        
        # Process basic stops data from the route (even if detailed path data isn't available)
        for stop in stops:
            if stop.get('id'):
                # Extract coordinates from stop level or use defaults
                latitude = stop.get('latitude', 0.0)
                longitude = stop.get('longitude', 0.0)
                
                # If no coordinates at stop level, check address level
                if latitude == 0.0 and longitude == 0.0 and stop.get('address'):
                    latitude = stop['address'].get('latitude', 0.0)
                    longitude = stop['address'].get('longitude', 0.0)
                
                # Extract timing data if available
                arrival_time = None
                departure_time = None
                if stop.get('actualArrivalTime'):
                    arrival_time = datetime.fromisoformat(stop['actualArrivalTime'].replace('Z', '+00:00'))
                elif stop.get('scheduledArrivalTime'):
                    arrival_time = datetime.fromisoformat(stop['scheduledArrivalTime'].replace('Z', '+00:00'))
                
                if stop.get('actualDepartureTime'):
                    departure_time = datetime.fromisoformat(stop['actualDepartureTime'].replace('Z', '+00:00'))
                elif stop.get('scheduledDepartureTime'):
                    departure_time = datetime.fromisoformat(stop['scheduledDepartureTime'].replace('Z', '+00:00'))
                
                route.stops.append(RouteStop(
                    id=stop['id'],
                    name=stop.get('name'),
                    address=stop.get('address', {}).get('name') if stop.get('address') else None,
                    latitude=latitude,
                    longitude=longitude,
                    arrival_time=arrival_time,
                    departure_time=departure_time,
                    duration_seconds=stop.get('durationSeconds'),
                    notes=stop.get('notes', '')
                ))
        
        return route
    
    def _add_path_data_to_route(self, route: Route, path_data: Dict) -> Route:
        """Add GPS points and stops to a route."""
        # Add GPS points
        if path_data.get('points'):
            for point in path_data['points']:
                route.points.append(RoutePoint(
                    latitude=point['latitude'],
                    longitude=point['longitude'],
                    time=datetime.fromisoformat(point['time'].replace('Z', '+00:00')),
                    speed=point.get('speed'),
                    heading=point.get('heading')
                ))
        
        # Enhance existing stops with detailed timing data or add new ones
        if path_data.get('stops'):
            existing_stop_ids = {stop.id for stop in route.stops}
            
            for stop in path_data['stops']:
                arrival_time = None
                departure_time = None
                if stop.get('arrivalTime'):
                    arrival_time = datetime.fromisoformat(stop['arrivalTime'].replace('Z', '+00:00'))
                if stop.get('departureTime'):
                    departure_time = datetime.fromisoformat(stop['departureTime'].replace('Z', '+00:00'))
                
                stop_id = stop['id']
                
                # Try to find existing stop to update
                existing_stop = None
                for existing in route.stops:
                    if existing.id == stop_id:
                        existing_stop = existing
                        break
                
                if existing_stop:
                    # Update existing stop with timing data
                    existing_stop.arrival_time = arrival_time
                    existing_stop.departure_time = departure_time
                    # Update other fields if they're more detailed in path data
                    if stop.get('address') and not existing_stop.address:
                        existing_stop.address = stop['address']
                else:
                    # Add new stop not found in basic data
                    route.stops.append(RouteStop(
                        id=stop_id,
                        name=stop.get('name'),
                        address=stop.get('address'),
                        latitude=stop['latitude'],
                        longitude=stop['longitude'],
                        arrival_time=arrival_time,
                        departure_time=departure_time,
                        duration_seconds=stop.get('durationSeconds'),
                        notes=stop.get('notes')
                    ))
        
        return route
    
    def save_routes(self, routes: List[Route], format: str = 'json',
                   output_file: Optional[Path] = None) -> Path:
        """Save routes in the specified format."""
        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = self.output_dir / f"routes_{timestamp}.{format}"
        
        if format == 'json':
            return self._save_as_json(routes, output_file)
        elif format == 'csv':
            return self._save_as_csv(routes, output_file)
        elif format == 'gpx':
            return self._save_as_gpx(routes, output_file)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _save_as_json(self, routes: List[Route], output_file: Path) -> Path:
        """Save routes as JSON."""
        with open(output_file, 'w') as f:
            json.dump([route.dict() for route in routes], f, indent=2, default=str)
        logger.info(f"Saved {len(routes)} routes to {output_file}")
        return output_file
    
    def _save_as_csv(self, routes: List[Route], output_file: Path) -> Path:
        """Save routes as CSV (summary data only)."""
        if not routes:
            logger.warning("No routes to save")
            return output_file
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=routes[0].to_csv_dict().keys())
            writer.writeheader()
            for route in routes:
                writer.writerow(route.to_csv_dict())
        
        logger.info(f"Saved {len(routes)} routes to {output_file}")
        return output_file
    
    def _save_as_gpx(self, routes: List[Route], output_file: Path) -> Path:
        """Save routes as GPX (one file per route)."""
        if len(routes) == 1:
            # Single route - save directly
            with open(output_file, 'w') as f:
                f.write(routes[0].to_gpx())
            logger.info(f"Saved route to {output_file}")
            return output_file
        else:
            # Multiple routes - create directory
            output_dir = output_file.parent / output_file.stem
            output_dir.mkdir(exist_ok=True)
            
            for i, route in enumerate(routes):
                route_file = output_dir / f"route_{i+1}_{route.id}.gpx"
                with open(route_file, 'w') as f:
                    f.write(route.to_gpx())
            
            logger.info(f"Saved {len(routes)} routes to {output_dir}")
            return output_dir
    
    def print_route_summary(self, routes: List[Route]):
        """Print a summary of the routes."""
        print(f"\nFound {len(routes)} routes")
        print("-" * 80)
        
        total_distance = 0
        total_duration = 0
        
        for route in routes:
            print(f"\nRoute ID: {route.id}")
            if route.name:
                print(f"Name: {route.name}")
            print(f"Start Time: {route.start_time}")
            print(f"End Time: {route.end_time or 'In Progress'}")
            
            if route.vehicle_name:
                print(f"Vehicle: {route.vehicle_name} (ID: {route.vehicle_id})")
            if route.driver_name:
                print(f"Driver: {route.driver_name} (ID: {route.driver_id})")
            
            if route.distance_meters:
                distance_miles = route.distance_meters / 1609.34
                print(f"Distance: {distance_miles:.1f} miles ({route.distance_meters} meters)")
                total_distance += route.distance_meters
            
            if route.duration_seconds:
                duration_hours = route.duration_seconds / 3600
                print(f"Duration: {duration_hours:.1f} hours ({route.duration_seconds} seconds)")
                total_duration += route.duration_seconds
            
            print(f"Stops: {len(route.stops)}")
            print(f"GPS Points: {len(route.points)}")
        
        if len(routes) > 1:
            print("\n" + "=" * 80)
            print("TOTALS:")
            if total_distance > 0:
                print(f"Total Distance: {total_distance / 1609.34:.1f} miles")
            if total_duration > 0:
                print(f"Total Duration: {total_duration / 3600:.1f} hours")

    def group_routes_by_dairy_and_injection_site(self, routes: List[Route]) -> Dict:
        """Group routes by dairy and injection site.
        
        Extracts dairy and injection site information from route names, stops, 
        and other available data fields.
        """
        grouped_data = {}
        
        for route in routes:
            dairy, injection_site = self._extract_dairy_and_injection_site(route)
            
            # Initialize nested structure if it doesn't exist
            if dairy not in grouped_data:
                grouped_data[dairy] = {}
            if injection_site not in grouped_data[dairy]:
                grouped_data[dairy][injection_site] = []
            
            # Add route to appropriate group
            grouped_data[dairy][injection_site].append(route.dict())
        
        return grouped_data
    
    def _extract_dairy_and_injection_site(self, route: Route) -> Tuple[str, str]:
        """Extract dairy and injection site information from route data.
        
        This method attempts to parse dairy and injection site from:
        1. Route name patterns (e.g., "Dairy A - Site 1", "Farm XYZ Site B")
        2. Stop addresses or names that contain dairy/farm identifiers
        3. Vehicle names if they contain location/facility info
        
        Returns a tuple of (dairy_name, injection_site_name)
        """
        dairy = "Unknown Dairy"
        injection_site = "Unknown Site"
        
        # Try to extract from route name first
        if route.name:
            name = route.name
            
            # Pattern matching for common route naming conventions
            # Examples: "AI Route - Dairy A - Site 1", "Farm B Site 2", etc.
            import re
            
            # Look for patterns like "Dairy X", "Farm Y", etc.
            dairy_match = re.search(r'(dairy|farm)\s+([a-z0-9]+)', name, re.IGNORECASE)
            if dairy_match:
                dairy = f"{dairy_match.group(1).title()} {dairy_match.group(2).upper()}"
            
            # Look for patterns like "Site X", "Location Y", "Injection Site Z"
            site_match = re.search(r'(site|location|injection\s+site)\s+([a-z0-9]+)', name, re.IGNORECASE)
            if site_match:
                injection_site = f"{site_match.group(1).title()} {site_match.group(2).upper()}"
            
            # Alternative pattern: "A - B" where A could be dairy and B could be site
            dash_parts = [part.strip() for part in name.split(' - ')]
            if len(dash_parts) >= 3:  # e.g., "AI Route - Dairy A - Site 1"
                dairy = dash_parts[1] if dash_parts[1] else dairy
                injection_site = dash_parts[2] if dash_parts[2] else injection_site
            elif len(dash_parts) == 2:  # e.g., "Dairy A - Site 1"
                dairy = dash_parts[0]
                injection_site = dash_parts[1]
        
        # Try to extract from stop data if route name didn't provide clear info
        if dairy == "Unknown Dairy" or injection_site == "Unknown Site":
            dairy_from_stops, site_from_stops = self._extract_from_stops(route.stops)
            if dairy == "Unknown Dairy" and dairy_from_stops:
                dairy = dairy_from_stops
            if injection_site == "Unknown Site" and site_from_stops:
                injection_site = site_from_stops
        
        # Try vehicle name as fallback
        if dairy == "Unknown Dairy" and route.vehicle_name:
            dairy = route.vehicle_name
        
        return dairy, injection_site
    
    def _extract_from_stops(self, stops: List[RouteStop]) -> Tuple[Optional[str], Optional[str]]:
        """Extract dairy and injection site info from route stops."""
        dairy = None
        injection_site = None
        
        for stop in stops:
            # Check stop name
            if stop.name:
                import re
                
                dairy_match = re.search(r'(dairy|farm)\s+([a-z0-9]+)', stop.name, re.IGNORECASE)
                if dairy_match and not dairy:
                    dairy = f"{dairy_match.group(1).title()} {dairy_match.group(2).upper()}"
                
                site_match = re.search(r'(injection|site|location)\s+([a-z0-9]+)', stop.name, re.IGNORECASE)
                if site_match and not injection_site:
                    injection_site = f"{site_match.group(1).title()} {site_match.group(2).upper()}"
            
            # Check stop address
            if stop.address:
                import re
                
                dairy_match = re.search(r'(dairy|farm)\s+([a-z0-9]+)', stop.address, re.IGNORECASE)
                if dairy_match and not dairy:
                    dairy = f"{dairy_match.group(1).title()} {dairy_match.group(2).upper()}"
        
        return dairy, injection_site
    
    def save_grouped_routes_json(self, grouped_data: Dict, output_file: Path) -> Path:
        """Save grouped routes data as JSON with metadata."""
        # Add metadata to the output
        output_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_dairies": len(grouped_data),
                "total_routes": sum(len(sites[site]) for sites in grouped_data.values() for site in sites),
                "grouping_method": "dairy_and_injection_site"
            },
            "data": grouped_data
        }
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2, default=str)
        
        logger.info(f"Saved grouped routes data to {output_file}")
        return output_file
