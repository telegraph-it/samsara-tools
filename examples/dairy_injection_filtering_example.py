#!/usr/bin/env python3
"""
Example: Filter trips that start at dairies and end at injection sites.

This example demonstrates the new dairy-to-injection filtering functionality
that matches trips starting at any dairy (tagged 'Maas') and ending at any
injection site (tagged 'Maas Injection').
"""

import os
from datetime import datetime
from dotenv import load_dotenv
from samsara_tools import TripService

def main():
    # Load environment
    load_dotenv()
    api_token = os.getenv('SAMSARA_API_TOKEN')

    if not api_token:
        print("Error: SAMSARA_API_TOKEN not found in environment")
        print("Create a .env file with your API token")
        return

    # Initialize service
    service = TripService(api_token)

    # Test with a specific trailer that has dairy-to-injection trips
    trailer_id = "281474992485382"  # QU 0003
    start_time = datetime(2025, 7, 1)
    end_time = datetime(2025, 7, 31)

    print(f"Testing dairy-to-injection filtering for trailer {trailer_id}")
    print("=" * 60)

    # Example 1: Manual filtering with specific lists
    print("\nExample 1: Manual filtering with geofence name lists")
    print("-" * 50)

    # Get all trips for this trailer
    print("Getting all trips...")
    trips = service.get_trips(trailer_id, start_time, end_time)
    print(f"Found {len(trips)} total trips")

    # Define the geofence lists (these would normally come from tag queries)
    dairy_names = [
        "Maas-Channel Island Dairy [MAA-PAC-20]",
        "Maas-Stillwater Dairy [MAA-STI-20]", 
        "Maas-FM Jersey Dairy [MAA-FMJ-20]",
        "Maas-Lone Oak Dairy [MAA-LO2-20]",
        "Maas-Avalon Dairy [DGE-AVA-23]",
        "Maas-JDS Dairy [MAA-MER-24]",
        "Maas-Alhem Dairy [MAA-DEN-24]",
        "Maas-Blue Sky Dairy [MAA-ATW-24]",
        "Maas-Diesel Doctor [Laydown Yard]"
    ]

    injection_names = [
        "Maas-Calgren Injection Site",
        "Maas-Five Points Injection Site", 
        "Maas-Helm Injection Site"
    ]

    print("\nFiltering for dairy-to-injection trips (including trips with no start geofence)...")
    filtered_trips = service.filter_trips_by_start_end_geofences(
        trips, dairy_names, injection_names,
        allow_no_start_geofence=True  # Allow trips that start at intermediary stops
    )

    print(f"Found {len(filtered_trips)} dairy-to-injection trips:")
    for i, trip in enumerate(filtered_trips, 1):
        # Extract geofence names
        start_geofence = "Unknown"
        end_geofence = "Unknown"
        
        for geofence_entry in trip.enter_geofences:
            if geofence_entry.startswith("start:"):
                start_geofence = geofence_entry[6:]
            elif geofence_entry.startswith("end:"):
                end_geofence = geofence_entry[4:]
        
        # Format times
        start_str = trip.start_time.strftime('%Y-%m-%d %H:%M')
        end_str = trip.end_time.strftime('%Y-%m-%d %H:%M') if trip.end_time else 'In Progress'
        
        # Calculate distance in miles
        distance_mi = trip.distance_meters / 1609.34 if trip.distance_meters else 0
        
        print(f"\n{i}. Trip {trip.id}")
        print(f"   Start: {start_str} at {start_geofence}")
        print(f"   End:   {end_str} at {end_geofence}")
        print(f"   Distance: {distance_mi:.1f} miles")

    # Example 2: Using tag-based querying (for a single asset - faster demo)
    print("\n\nExample 2: Tag-based querying for single asset")
    print("-" * 50)
    
    # This would query all assets, but for demo purposes let's show how it would work
    print("The new query_trips_by_geofence_tags method can query all assets automatically:")
    print("It fetches geofences by tags 'Maas' and 'Maas Injection', then filters all asset trips.")
    
    # Example CLI commands
    print("\n\nExample 3: Equivalent CLI commands")
    print("-" * 50)
    
    print("\n# Query all assets for dairy-to-injection trips (includes no-start trips by default):")
    print("samsara-tools trips query-dairy-to-injection --start 2025-07-01 --end 2025-07-31")
    
    print("\n# Exclude trips with no start geofence (strict dairy-to-injection only):")
    print("samsara-tools trips query-dairy-to-injection --start 2025-07-01 --end 2025-07-31 --no-allow-no-start-geofence")
    
    print("\n# With custom tags:")
    print("samsara-tools trips query-dairy-to-injection --start-tag 'Maas' --end-tag 'Maas Injection' --start 2025-07-01")
    
    print("\n# Save to specific file:")
    print("samsara-tools trips query-dairy-to-injection --start 2025-07-01 --output dairy_trips.json")
    
    print("\n# Include GPS track data:")
    print("samsara-tools trips query-dairy-to-injection --start 2025-07-01 --include-points")

    print("\n✓ Example completed successfully!")

if __name__ == "__main__":
    main()