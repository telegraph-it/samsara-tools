#!/usr/bin/env python3
"""
Example usage of the new trailer and trips API functionality.

This example shows how to use the new API methods added in Phase 1:
1. List all trailers
2. Get trips for a trailer
3. Get detailed trip path data
"""

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from samsara_tools import SamsaraClient

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
    
    # Example 2: Get trips for a trailer
    if trailers:
        print("\n2. Getting trips for first trailer...")
        first_trailer = trailers[0]
        trailer_id = first_trailer['id']
        trailer_name = first_trailer.get('name', 'Unnamed')
        
        # Query last 7 days of trips
        end_time = datetime.now()
        start_time = end_time - timedelta(days=7)
        
        print(f"Querying trips for '{trailer_name}' from {start_time.date()} to {end_time.date()}")
        trips = client.get_trips(trailer_id, start_time, end_time)
        
        print(f"Found {len(trips)} trips:")
        for i, trip in enumerate(trips[:3], 1):  # Show first 3
            trip_start_ms = trip.get('startMs', 0)
            trip_end_ms = trip.get('endMs', 0)
            trip_start = datetime.fromtimestamp(trip_start_ms / 1000).strftime('%Y-%m-%d %H:%M:%S') if trip_start_ms else 'Unknown'
            trip_end = datetime.fromtimestamp(trip_end_ms / 1000).strftime('%Y-%m-%d %H:%M:%S') if trip_end_ms else 'Unknown'
            distance_m = trip.get('distanceMeters', 0)
            distance_mi = distance_m / 1609.34 if distance_m else 0
            start_location = trip.get('startLocation', 'Unknown')
            end_location = trip.get('endLocation', 'Unknown')
            
            print(f"  {i}. Trip from {start_location}")
            print(f"     Start: {trip_start}")
            print(f"     End: {trip_end}")
            print(f"     Distance: {distance_mi:.1f} miles")
            print(f"     End Location: {end_location}")
        
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
