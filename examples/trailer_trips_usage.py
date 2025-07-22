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
            trip_id = trip.get('id', 'Unknown')
            trip_start = trip.get('startTime', 'Unknown')
            trip_end = trip.get('endTime', 'Unknown')
            distance_m = trip.get('distanceMeters', 0)
            distance_mi = distance_m / 1609.34 if distance_m else 0
            
            print(f"  {i}. Trip {trip_id}")
            print(f"     Start: {trip_start}")
            print(f"     End: {trip_end}")
            print(f"     Distance: {distance_mi:.1f} miles")
        
        # Example 3: Get detailed path for a trip
        if trips:
            print("\n3. Getting detailed path for first trip...")
            first_trip = trips[0]
            trip_id = first_trip['id']
            
            path_data = client.get_trip_path(trip_id)
            if path_data:
                points = path_data.get('points', [])
                stops = path_data.get('stops', [])
                print(f"Trip {trip_id} has {len(points)} GPS points and {len(stops)} stops")
                
                if stops:
                    print("Stops:")
                    for stop in stops[:3]:  # Show first 3 stops
                        name = stop.get('name', 'Unknown')
                        arrival = stop.get('arrivalTime', 'Unknown')
                        print(f"  - {name} (Arrival: {arrival})")
            else:
                print("Could not retrieve trip path data")
    
    print("\n✓ Example completed successfully!")
    print("\nNext steps:")
    print("- Implement Phase 2: Create data models for Trailer and Trip")
    print("- Implement Phase 3: Create TripService for geofence analysis")
    print("- Implement Phase 4: Add CLI commands")

if __name__ == "__main__":
    main()
