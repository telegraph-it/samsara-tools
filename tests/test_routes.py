"""
Tests for route functionality.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from samsara_tools.models.route import Route, RoutePoint, RouteStop
from samsara_tools.core.route_service import RouteService


class TestRouteModels:
    """Test the route data models."""
    
    def test_route_point_creation(self):
        """Test creating a RoutePoint."""
        point = RoutePoint(
            latitude=37.7749,
            longitude=-122.4194,
            time=datetime.now(),
            speed=45.5,
            heading=180
        )
        assert point.latitude == 37.7749
        assert point.longitude == -122.4194
        assert point.speed == 45.5
        assert point.heading == 180
    
    def test_route_stop_creation(self):
        """Test creating a RouteStop."""
        stop = RouteStop(
            id="stop123",
            name="Warehouse A",
            address="123 Main St",
            latitude=37.7749,
            longitude=-122.4194,
            arrival_time=datetime.now(),
            duration_seconds=300
        )
        assert stop.id == "stop123"
        assert stop.name == "Warehouse A"
        assert stop.duration_seconds == 300
    
    def test_route_creation(self):
        """Test creating a Route."""
        route = Route(
            id="route123",
            name="Morning Delivery Route",
            driver_id="driver456",
            driver_name="John Doe",
            vehicle_id="vehicle789",
            vehicle_name="Truck 1",
            start_time=datetime.now(),
            distance_meters=50000,
            duration_seconds=3600
        )
        assert route.id == "route123"
        assert route.name == "Morning Delivery Route"
        assert route.distance_meters == 50000
    
    def test_route_to_csv_dict(self):
        """Test converting route to CSV dictionary."""
        route = Route(
            id="route123",
            name="Test Route",
            start_time=datetime.now(),
            distance_meters=10000,
            duration_seconds=1800
        )
        csv_dict = route.to_csv_dict()
        assert csv_dict["route_id"] == "route123"
        assert csv_dict["route_name"] == "Test Route"
        assert csv_dict["distance_meters"] == 10000
        assert csv_dict["duration_seconds"] == 1800
    
    def test_route_to_gpx(self):
        """Test converting route to GPX format."""
        route = Route(
            id="route123",
            name="Test Route",
            start_time=datetime.now(),
            points=[
                RoutePoint(
                    latitude=37.7749,
                    longitude=-122.4194,
                    time=datetime.now()
                )
            ],
            stops=[
                RouteStop(
                    id="stop1",
                    name="Stop 1",
                    latitude=37.7749,
                    longitude=-122.4194
                )
            ]
        )
        gpx = route.to_gpx()
        assert "<?xml version" in gpx
        assert "<gpx" in gpx
        assert "37.7749" in gpx
        assert "-122.4194" in gpx


class TestRouteService:
    """Test the RouteService class."""
    
    @patch('samsara_tools.core.route_service.SamsaraClient')
    def test_query_routes(self, mock_client_class):
        """Test querying routes."""
        # Setup mock
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock API response
        mock_client.get_all_routes.return_value = [
            {
                'id': 'route123',
                'name': 'Test Route',
                'startTime': '2024-01-01T10:00:00Z',
                'endTime': '2024-01-01T12:00:00Z',
                'distanceMeters': 50000,
                'durationSeconds': 7200
            }
        ]
        
        # Create service and query routes
        service = RouteService("test_token")
        start_time = datetime(2024, 1, 1)
        end_time = datetime(2024, 1, 31)
        
        routes = service.query_routes(start_time, end_time)
        
        # Verify
        assert len(routes) == 1
        assert routes[0].id == 'route123'
        assert routes[0].name == 'Test Route'
        assert routes[0].distance_meters == 50000
        
        # Verify API was called correctly
        mock_client.get_all_routes.assert_called_once_with(
            start_time=start_time,
            end_time=end_time,
            vehicle_id=None,
            driver_id=None
        )
    
    @patch('samsara_tools.core.route_service.SamsaraClient')
    def test_get_route_by_id(self, mock_client_class):
        """Test getting a specific route by ID."""
        # Setup mock
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock API responses
        mock_client.get_route_details.return_value = {
            'id': 'route123',
            'name': 'Test Route',
            'startTime': '2024-01-01T10:00:00Z',
            'distanceMeters': 25000
        }
        
        mock_client.get_route_path.return_value = {
            'points': [
                {
                    'latitude': 37.7749,
                    'longitude': -122.4194,
                    'time': '2024-01-01T10:00:00Z'
                }
            ],
            'stops': []
        }
        
        # Create service and get route
        service = RouteService("test_token")
        route = service.get_route_by_id('route123', include_points=True)
        
        # Verify
        assert route is not None
        assert route.id == 'route123'
        assert route.name == 'Test Route'
        assert len(route.points) == 1
        assert route.points[0].latitude == 37.7749
        
        # Verify API calls
        mock_client.get_route_details.assert_called_once_with('route123')
        mock_client.get_route_path.assert_called_once_with('route123', include_stops=True)


if __name__ == "__main__":
    pytest.main([__file__])
