#!/usr/bin/env python3
"""
Example: Query trips that start or end within a specific geofence.

This example demonstrates how to use the new TripService functionality
to find all trips for a specific asset that start or end within a
particular geofence.
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
from samsara_tools import SamsaraClient, TripService

def main():
    # Load environment variables
    load_dotenv()
    api_token = os.getenv('SAMSARA_API_TOKEN')
    
    if not api_token:
        print("Error: SAMSARA_API_TOKEN not found in environment")
        print("Create a .env file with your API token")
        return
    
    # Initialize service
    print("Initializing Trip Service...")
    trip_service = TripService(api_token)
    
    # Example 1: Query all trips for an asset
    print("\n" + "="*60)
    print("Example 1: Query all trips for a specific asset")
    print("="*60)
    
    # First, let's get available trailers to select from
    client = SamsaraClient(api_token)
    trailers = client.get_all_trailers()
    
    if not trailers:
        print("No trailers found in your Samsara account")
        return
    
    # Use the first trailer as an example
    trailer = trailers[0]
    trailer_id = trailer['id']
    trailer_name = trailer.get('name', 'Unnamed')
    
    print(f"\nUsing trailer: {trailer_name} (ID: {trailer_id})")
    
    # Query last 7 days of trips
    end_time = datetime.now()
    start_time = end_time - timedelta(days=7)
    
    print(f"Querying trips from {start_time.date()} to {end_time.date()}")
    trips = trip_service.get_trips(trailer_id, start_time, end_time)
    
    print(f"Found {len(trips)} total trips")
    
    # Example 2: Filter trips by geofence
    print("\n" + "="*60)
    print("Example 2: Filter trips by specific geofence")
    print("="*60)
    
    # You would replace this with your actual geofence name
    target_geofence = "Distribution Center"  # Example geofence name
    
    print(f"\nFiltering for trips that start or end at '{target_geofence}'...")
    
    # Filter trips that start OR end in the geofence
    filtered_trips = trip_service.filter_trips_by_geofence(
        trips, 
        target_geofence,
        match_start=True,
        match_end=True
    )
    
    if filtered_trips:
        print(f"Found {len(filtered_trips)} trips involving '{target_geofence}':")
        trip_service.print_trips_summary(filtered_trips)
    else:
        print(f"No trips found involving '{target_geofence}'")
        print("\nShowing all geofences found in trips:")
        
        # Extract unique geofences from all trips
        geofences = set()
        for trip in trips:
            for entry in trip.enter_geofences:
                if entry.startswith("start:"):
                    geofences.add(entry[6:])
                elif entry.startswith("end:"):
                    geofences.add(entry[4:])
        
        for geofence in sorted(geofences):
            print(f"  - {geofence}")
    
    # Example 3: Using query_trips for combined operation
    print("\n" + "="*60)
    print("Example 3: Direct query with geofence filter")
    print("="*60)
    
    # This combines get_trips and filter_trips_by_geofence in one call
    filtered_trips = trip_service.query_trips(
        trailer_id,
        start_time,
        end_time,
        geofence=target_geofence,
        include_path=False,  # Set to True to get GPS data
        match_start=True,
        match_end=True
    )
    
    print(f"Direct query found {len(filtered_trips)} trips")
    
    # Example 4: Export filtered trips
    print("\n" + "="*60)
    print("Example 4: Export filtered trips to files")
    print("="*60)
    
    if filtered_trips:
        # Save as JSON
        json_path = trip_service.save_trips(filtered_trips, format='json')
        print(f"Saved JSON to: {json_path}")
        
        # Save as CSV
        csv_path = trip_service.save_trips(filtered_trips, format='csv')
        print(f"Saved CSV to: {csv_path}")
        
        # Save as GPX (only if GPS data included)
        if any(trip.points for trip in filtered_trips):
            gpx_path = trip_service.save_trips(filtered_trips, format='gpx')
            print(f"Saved GPX to: {gpx_path}")
        else:
            print("No GPS data available for GPX export (use include_path=True)")
    
    # Example 5: CLI command examples
    print("\n" + "="*60)
    print("Example 5: Equivalent CLI commands")
    print("="*60)
    
    print("\nYou can achieve the same results using the CLI:")
    print(f"\n# Query all trips for the asset:")
    print(f"samsara-tools trips query --asset {trailer_id} --start {start_time.date()} --end {end_time.date()}")
    
    print(f"\n# Filter by geofence:")
    print(f"samsara-tools trips query --asset {trailer_id} --start {start_time.date()} " +
          f"--geofence \"{target_geofence}\" --output trips_filtered.json")
    
    print(f"\n# Include GPS data and export as GPX:")
    print(f"samsara-tools trips query --asset {trailer_id} --start {start_time.date()} " +
          f"--geofence \"{target_geofence}\" --include-points --format gpx --output trips.gpx")
    
    print(f"\n# Match only trips that START in the geofence:")
    print(f"samsara-tools trips query --asset {trailer_id} --start {start_time.date()} " +
          f"--geofence \"{target_geofence}\" --match-start")
    
    print(f"\n# Match only trips that END in the geofence:")
    print(f"samsara-tools trips query --asset {trailer_id} --start {start_time.date()} " +
          f"--geofence \"{target_geofence}\" --match-end")
    
    print("\n✓ Example completed successfully!")

if __name__ == "__main__":
    main()