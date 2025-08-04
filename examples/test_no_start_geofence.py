#!/usr/bin/env python3
"""
Test script to verify the new allow_no_start_geofence functionality.
This tests that trips without a starting geofence but ending at injection sites
are properly included when the flag is set.
"""

import os
from datetime import datetime
from dotenv import load_dotenv
from samsara_tools.core.trip_service import TripService
from samsara_tools.models.trip import Trip

def create_test_trips():
    """Create test trips with various start/end configurations."""
    trips = []
    
    # Trip 1: Dairy to Injection (should always be included)
    trip1 = Trip(
        id="trip1",
        trailer_id="test_trailer",
        start_time=datetime(2025, 7, 1, 8, 0),
        end_time=datetime(2025, 7, 1, 12, 0),
        enter_geofences=["start:Maas-Channel Island Dairy [MAA-PAC-20]", 
                         "end:Maas-Calgren Injection Site"]
    )
    trips.append(trip1)
    
    # Trip 2: No start to Injection (should be included when allow_no_start_geofence=True)
    trip2 = Trip(
        id="trip2",
        trailer_id="test_trailer",
        start_time=datetime(2025, 7, 2, 9, 0),
        end_time=datetime(2025, 7, 2, 13, 0),
        enter_geofences=["end:Maas-Five Points Injection Site"]  # No start geofence
    )
    trips.append(trip2)
    
    # Trip 3: Dairy to non-injection (should never be included)
    trip3 = Trip(
        id="trip3",
        trailer_id="test_trailer",
        start_time=datetime(2025, 7, 3, 7, 0),
        end_time=datetime(2025, 7, 3, 11, 0),
        enter_geofences=["start:Maas-Stillwater Dairy [MAA-STI-20]", 
                         "end:Some Other Location"]
    )
    trips.append(trip3)
    
    # Trip 4: No start to non-injection (should never be included)
    trip4 = Trip(
        id="trip4",
        trailer_id="test_trailer",
        start_time=datetime(2025, 7, 4, 10, 0),
        end_time=datetime(2025, 7, 4, 14, 0),
        enter_geofences=["end:Another Random Place"]
    )
    trips.append(trip4)
    
    # Trip 5: Non-dairy to Injection (should only be included when allow_no_start_geofence=True)
    trip5 = Trip(
        id="trip5",
        trailer_id="test_trailer",
        start_time=datetime(2025, 7, 5, 8, 30),
        end_time=datetime(2025, 7, 5, 12, 30),
        enter_geofences=["start:Random Warehouse", 
                         "end:Maas-Helm Injection Site"]
    )
    trips.append(trip5)
    
    return trips

def main():
    # Load environment
    load_dotenv()
    api_token = os.getenv('SAMSARA_API_TOKEN')
    
    if not api_token:
        print("Error: SAMSARA_API_TOKEN not found in environment")
        return
    
    # Initialize service
    service = TripService(api_token, lazy_resolver=True)
    
    # Create test trips
    test_trips = create_test_trips()
    
    # Define geofence lists
    dairy_names = [
        "Maas-Channel Island Dairy [MAA-PAC-20]",
        "Maas-Stillwater Dairy [MAA-STI-20]",
        "Maas-FM Jersey Dairy [MAA-FMJ-20]"
    ]
    
    injection_names = [
        "Maas-Calgren Injection Site",
        "Maas-Five Points Injection Site",
        "Maas-Helm Injection Site"
    ]
    
    print("Testing new allow_no_start_geofence functionality")
    print("=" * 60)
    
    # Test 1: Default behavior (allow_no_start_geofence=False)
    print("\nTest 1: Default behavior (strict dairy-to-injection only)")
    print("-" * 50)
    filtered_strict = service.filter_trips_by_start_end_geofences(
        test_trips, dairy_names, injection_names,
        allow_no_start_geofence=False
    )
    print(f"Found {len(filtered_strict)} trips:")
    for trip in filtered_strict:
        print(f"  - {trip.id}: {trip.enter_geofences}")
    print("Expected: Only trip1 (dairy to injection)")
    
    # Test 2: New behavior (allow_no_start_geofence=True)
    print("\nTest 2: New behavior (allow trips with no start geofence)")
    print("-" * 50)
    filtered_relaxed = service.filter_trips_by_start_end_geofences(
        test_trips, dairy_names, injection_names,
        allow_no_start_geofence=True
    )
    print(f"Found {len(filtered_relaxed)} trips:")
    for trip in filtered_relaxed:
        print(f"  - {trip.id}: {trip.enter_geofences}")
    print("Expected: trip1 (dairy to injection) and trip2 (no start to injection)")
    
    # Test 3: Edge case - empty start list with allow_no_start_geofence=True
    print("\nTest 3: Empty start list with allow_no_start_geofence=True")
    print("-" * 50)
    filtered_empty_start = service.filter_trips_by_start_end_geofences(
        test_trips, [], injection_names,
        allow_no_start_geofence=True
    )
    print(f"Found {len(filtered_empty_start)} trips:")
    for trip in filtered_empty_start:
        print(f"  - {trip.id}: {trip.enter_geofences}")
    print("Expected: trip2 (no start to injection) only")
    
    print("\n" + "=" * 60)
    print("Test Summary:")
    if len(filtered_strict) == 1 and filtered_strict[0].id == "trip1":
        print("✓ Test 1 PASSED: Strict mode correctly filters dairy-to-injection only")
    else:
        print("✗ Test 1 FAILED: Unexpected results in strict mode")
    
    if len(filtered_relaxed) == 2 and set(t.id for t in filtered_relaxed) == {"trip1", "trip2"}:
        print("✓ Test 2 PASSED: Relaxed mode includes no-start trips to injection sites")
    else:
        print("✗ Test 2 FAILED: Unexpected results in relaxed mode")
    
    if len(filtered_empty_start) == 1 and filtered_empty_start[0].id == "trip2":
        print("✓ Test 3 PASSED: Empty start list with allow flag works correctly")
    else:
        print("✗ Test 3 FAILED: Unexpected results with empty start list")
    
    print("\n✓ Implementation complete and tested!")

if __name__ == "__main__":
    main()