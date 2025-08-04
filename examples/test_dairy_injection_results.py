#!/usr/bin/env python3
"""
Example: Test dairy-to-injection filtering and create sample results.

This example demonstrates the complete dairy-to-injection workflow by:
1. Using the tag-based geofence querying
2. Filtering trips for the specific pattern
3. Saving results in the same format as the CLI command
"""

import os
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from samsara_tools import TripService
from samsara_tools.core.geofence_query import SamsaraGeofenceQuery

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

    # Test with the specific trailer we know has dairy-to-injection trips
    trailer_id = "281474992485382"  # QU 0003
    start_time = datetime(2025, 7, 1)
    end_time = datetime(2025, 7, 31)

    print("Creating dairy-to-injection results using the tag-based method...")
    print("=" * 60)

    # Use the new tag-based query method for just this one trailer
    # (simulating what would happen for all trailers)
    results = {}

    # Get trips for this trailer
    print(f"Getting trips for trailer {trailer_id}...")
    trips = service.get_trips(trailer_id, start_time, end_time)
    print(f"Found {len(trips)} total trips")

    # Get geofence names from tags (same as what the full method does)
    print("\nFetching geofences by tags...")
    geofence_client = SamsaraGeofenceQuery(api_token)

    start_geofences = geofence_client.query_geofences_by_tag("Maas")
    start_names = [gf['name'] for gf in start_geofences if gf.get('name')]

    end_geofences = geofence_client.query_geofences_by_tag("Maas Injection")
    end_names = [gf['name'] for gf in end_geofences if gf.get('name')]

    print(f"Found {len(start_names)} dairy geofences and {len(end_names)} injection site geofences")

    # Filter trips
    print("\nFiltering for dairy-to-injection pattern (including trips with no start geofence)...")
    filtered_trips = service.filter_trips_by_start_end_geofences(
        trips, start_names, end_names,
        allow_no_start_geofence=True  # Allow trips that start at intermediary stops
    )

    if filtered_trips:
        results[trailer_id] = filtered_trips

    print(f"Found {len(filtered_trips)} dairy-to-injection trips")

    # Save using the service's save method
    output_dir = Path('data/output/trips_query')
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / f'dairy_to_injection_test_results_{timestamp}.json'

    if results:
        saved_path = service.save_geofence_trips(results, format='json', output_file=output_file)
        print(f"\nResults saved to: {saved_path}")

        # Also print summary
        print("\nSummary of results:")
        service.print_geofence_trips_summary(results, "Maas ➜ Maas Injection")
    else:
        print("\nNo dairy-to-injection trips found")

    print("\n" + "=" * 60)
    print("CLI Command Equivalent:")
    print("samsara-tools trips query-dairy-to-injection --start 2025-07-01 --end 2025-07-31")
    print("\n✓ Test completed successfully!")

if __name__ == "__main__":
    main()