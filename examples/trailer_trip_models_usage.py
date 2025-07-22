#!/usr/bin/env python3
"""
Example usage of the new Trailer and Trip data models created in Phase 2.

This example demonstrates:
1. Creating Trailer and Trip instances
2. Using the export methods (to_csv_dict, to_gpx)
3. Working with the data models in Python code
"""

from datetime import datetime, timedelta
from samsara_tools.models.trailer import Trailer, TrailerLocation
from samsara_tools.models.trip import Trip, TripPoint, TripStop

def main():
    print("Phase 2 Data Models Example")
    print("=" * 40)
    
    # Example 1: Create a Trailer instance
    print("\n1. Creating a Trailer instance...")
    trailer_location = TrailerLocation(
        latitude=40.7128,
        longitude=-74.0060,
        time=datetime.now()
    )
    
    trailer = Trailer(
        id="trailer_123",
        name="Milk Transport Trailer A",
        asset_number="MT-001",
        vin="1HGCM82633A123456",
        tag_ids=["tag1", "tag2", "maas_injection"],
        last_location=trailer_location,
        is_active=True,
        status="idle",
        odometer_miles=125000.5,
        fuel_level_percent=85.0
    )
    
    print(f"Created trailer: {trailer.name} (ID: {trailer.id})")
    print(f"Location: ({trailer.last_location.latitude}, {trailer.last_location.longitude})")
    
    # Example 2: Create a Trip instance with points and stops
    print("\n2. Creating a Trip instance...")
    start_time = datetime.now() - timedelta(hours=2)
    end_time = datetime.now() - timedelta(hours=1)
    
    # Create some sample GPS points
    trip_points = [
        TripPoint(
            latitude=40.7128 + i * 0.001,
            longitude=-74.0060 + i * 0.001,
            time=start_time + timedelta(minutes=i * 5),
            speed=35.0 + i * 2,
            heading=90
        )
        for i in range(5)
    ]
    
    # Create some sample stops
    trip_stops = [
        TripStop(
            id="stop_1",
            name="Dairy Farm A",
            address="123 Farm Road, Rural County",
            latitude=40.7130,
            longitude=-74.0058,
            arrival_time=start_time + timedelta(minutes=10),
            departure_time=start_time + timedelta(minutes=25),
            duration_seconds=900,
            notes="Milk pickup"
        ),
        TripStop(
            id="stop_2", 
            name="Processing Plant",
            address="456 Industrial Blvd, City",
            latitude=40.7135,
            longitude=-74.0055,
            arrival_time=start_time + timedelta(minutes=45),
            departure_time=start_time + timedelta(minutes=60),
            duration_seconds=900,
            notes="Milk delivery"
        )
    ]
    
    trip = Trip(
        id="trip_456",
        trailer_id=trailer.id,
        name="Milk Transport Route",
        start_time=start_time,
        end_time=end_time,
        start_location={"lat": 40.7128, "lng": -74.0060},
        end_location={"lat": 40.7140, "lng": -74.0050},
        distance_meters=5000,
        duration_seconds=3600,
        stops=trip_stops,
        points=trip_points,
        enter_geofences=["geofence_1", "geofence_2"]  # Will be populated by TripService in Phase 3
    )
    
    print(f"Created trip: {trip.name} (ID: {trip.id})")
    print(f"Duration: {trip.duration_seconds / 3600:.1f} hours")
    print(f"Distance: {trip.distance_meters / 1000:.1f} km")
    print(f"GPS Points: {len(trip.points)}")
    print(f"Stops: {len(trip.stops)}")
    
    # Example 3: Export to CSV format
    print("\n3. CSV Export Examples...")
    trailer_csv = trailer.to_csv_dict()
    trip_csv = trip.to_csv_dict()
    
    print("Trailer CSV fields:")
    for key, value in trailer_csv.items():
        print(f"  {key}: {value}")
    
    print("\nTrip CSV fields:")
    for key, value in trip_csv.items():
        print(f"  {key}: {value}")
    
    # Example 4: Export to GPX format
    print("\n4. GPX Export Example...")
    gpx_content = trip.to_gpx()
    print(f"GPX content length: {len(gpx_content)} characters")
    print("GPX preview:")
    print(gpx_content[:300] + "..." if len(gpx_content) > 300 else gpx_content)
    
    # Example 5: JSON serialization
    print("\n5. JSON Serialization Example...")
    import json
    
    trailer_json = trailer.json(indent=2)
    print(f"Trailer JSON preview (first 200 chars):")
    print(trailer_json[:200] + "..." if len(trailer_json) > 200 else trailer_json)
    
    trip_json = trip.json(indent=2)
    print(f"\nTrip JSON length: {len(trip_json)} characters")
    print("Trip JSON preview (first 200 chars):")
    print(trip_json[:200] + "..." if len(trip_json) > 200 else trip_json)
    
    print("\n✓ Phase 2 Data Models working correctly!")
    print("\nNext Steps:")
    print("- Phase 3: Implement TripService for geofence analysis")
    print("- Phase 4: Add CLI commands for trip comparison")
    print("- Integration with existing SamsaraClient trailer/trip API methods")

if __name__ == "__main__":
    main()
