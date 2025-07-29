#!/usr/bin/env python3
"""
Example usage of the new trailer and trips API functionality.

This example shows how to use the new API methods added in Phase 1:
1. List all trailers
2. Get trips for a trailer
3. Get detailed trip path data
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
from samsara_tools import SamsaraClient, GeofenceResolver

def select_trailer(trailers):
    """Allow user to select which trailer to analyze."""
    print(f"\nSelect a trailer to analyze (1-{len(trailers)}):")
    
    # Show first 10 trailers by default
    display_count = min(10, len(trailers))
    for i, trailer in enumerate(trailers[:display_count], 1):
        trailer_id = trailer.get('id', 'Unknown')
        name = trailer.get('name', 'Unnamed')
        asset_number = trailer.get('assetNumber', 'N/A')
        print(f"  {i}. {name} (ID: {trailer_id}, Asset#: {asset_number})")
    
    if len(trailers) > display_count:
        print(f"  ... and {len(trailers) - display_count} more")
        print(f"  (Enter a number between 1-{len(trailers)})")
    
    while True:
        try:
            choice = input(f"\nEnter trailer number (1-{len(trailers)}) or 'list' to see all: ").strip()
            
            if choice.lower() == 'list':
                print(f"\nAll {len(trailers)} trailers:")
                for i, trailer in enumerate(trailers, 1):
                    trailer_id = trailer.get('id', 'Unknown')
                    name = trailer.get('name', 'Unnamed')
                    asset_number = trailer.get('assetNumber', 'N/A')
                    print(f"  {i}. {name} (ID: {trailer_id}, Asset#: {asset_number})")
                continue
            
            trailer_num = int(choice)
            if 1 <= trailer_num <= len(trailers):
                return trailers[trailer_num - 1]
            else:
                print(f"Please enter a number between 1 and {len(trailers)}")
        except ValueError:
            print("Please enter a valid number or 'list'")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            sys.exit(0)


def print_trip(trip, idx, resolver=None):
    """Print formatted trip information with geofence name resolution."""
    trip_start_ms = trip.get('startMs', 0)
    trip_end_ms = trip.get('endMs', 0)

    # Helper to safely convert timestamps
    def safe_timestamp_convert(timestamp_ms):
        if not timestamp_ms or timestamp_ms == 0:
            return 'Unknown'
        try:
            if timestamp_ms > 4102444800000 or timestamp_ms < 0:  # sanity (year 2100)
                return f'Invalid timestamp: {timestamp_ms}'
            return datetime.fromtimestamp(timestamp_ms / 1000).strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, OSError):
            return f'Invalid timestamp: {timestamp_ms}'

    trip_start = safe_timestamp_convert(trip_start_ms)
    trip_end = safe_timestamp_convert(trip_end_ms)

    distance_m = trip.get('distanceMeters', 0)
    distance_mi = distance_m / 1609.34 if distance_m else 0

    # Resolve start location
    start_coords = trip.get('startCoordinates', {})
    start_lat = start_coords.get('latitude')
    start_lon = start_coords.get('longitude')
    start_geofence_name = None
    if resolver and start_lat is not None and start_lon is not None:
        start_geofence_name = resolver.resolve(start_lat, start_lon)
    start_location = start_geofence_name or trip.get('startLocation', 'Unknown')

    # Resolve end location
    end_coords = trip.get('endCoordinates', {})
    end_lat = end_coords.get('latitude')
    end_lon = end_coords.get('longitude')
    end_geofence_name = None
    if resolver and end_lat is not None and end_lon is not None:
        end_geofence_name = resolver.resolve(end_lat, end_lon)
    end_location = end_geofence_name or trip.get('endLocation', 'Unknown')

    # Pretty print
    print(f"  {idx}. Trip from {start_location}")
    print(f"     Start: {trip_start}")
    print(f"     End: {trip_end}")
    print(f"     Distance: {distance_mi:.1f} miles")
    print(f"     End Location: {end_location}")
    print()  # readability

def main():
    # Load environment variables
    load_dotenv()
    api_token = os.getenv('SAMSARA_API_TOKEN')
    
    if not api_token:
        print("Error: SAMSARA_API_TOKEN not found in environment")
        print("Create a .env file with your API token")
        return
    
    # Initialize client
    print("Initializing Samsara client...")
    client = SamsaraClient(api_token)
    
    # Verify API access
    success, message = client.verify_api_access()
    if not success:
        print(f"API verification failed: {message}")
        return
    print("✓ API access verified")
    
    # Initialize geofence resolver for location name lookup
    print("Initializing geofence resolver...")
    resolver = GeofenceResolver(client)
    
    # Example 1: List all trailers
    print("\n1. Listing all trailers...")
    trailers = client.get_all_trailers()
    print(f"Found {len(trailers)} trailers:")
    for i, trailer in enumerate(trailers[:5], 1):  # Show first 5
        trailer_id = trailer.get('id', 'Unknown')
        name = trailer.get('name', 'Unnamed')
        asset_number = trailer.get('assetNumber', 'N/A')
        print(f"  {i}. {name} (ID: {trailer_id}, Asset#: {asset_number})")
    if len(trailers) > 5:
        print(f"  ... and {len(trailers) - 5} more")
    
    # Example 2: Let user select a trailer
    if trailers:
        selected_trailer = select_trailer(trailers)
        if not selected_trailer:
            return
        
        print(f"\n2. Getting trips for selected trailer...")
        trailer_id = selected_trailer['id']
        trailer_name = selected_trailer.get('name', 'Unnamed')
        
        # Query last 7 days of trips
        end_time = datetime.now()
        start_time = end_time - timedelta(days=7)
        
        print(f"Querying trips for '{trailer_name}' from {start_time.date()} to {end_time.date()}")
        trips = client.get_trips(trailer_id, start_time, end_time)
        
        print(f"Found {len(trips)} trips:")
        # Show ALL trips instead of just first 3
        for i, trip in enumerate(trips, 1):
            print_trip(trip, i, resolver)
        
        # Example 3: Trip details already available in response
        if trips:
            print("\n3. Trip details from legacy API:")
            first_trip = trips[0]
            start_coords = first_trip.get('startCoordinates', {})
            end_coords = first_trip.get('endCoordinates', {})
            start_addr = first_trip.get('startAddress', {})
            end_addr = first_trip.get('endAddress', {})
            
            print(f"First trip coordinates:")
            print(f"  Start: {start_coords.get('latitude', 'N/A')}, {start_coords.get('longitude', 'N/A')}")
            print(f"  End: {end_coords.get('latitude', 'N/A')}, {end_coords.get('longitude', 'N/A')}")
            
            if start_addr:
                print(f"  Start Address: {start_addr.get('name', 'N/A')} - {start_addr.get('address', 'N/A')}")
            if end_addr:
                print(f"  End Address: {end_addr.get('name', 'N/A')} - {end_addr.get('address', 'N/A')}")
            
            print(f"Note: Legacy API doesn't support separate trip path endpoint")
    
    print("\n✓ Example completed successfully!")
    print("\nNext steps:")
    print("- Implement Phase 2: Create data models for Trailer and Trip")
    print("- Implement Phase 3: Create TripService for geofence analysis")
    print("- Implement Phase 4: Add CLI commands")

if __name__ == "__main__":
    main()
