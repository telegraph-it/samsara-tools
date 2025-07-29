"""Geofence name resolution for trip locations."""

import json
import logging
import pickle
from datetime import datetime, timedelta
from math import radians, sin, cos, sqrt, atan2
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from .client import SamsaraClient

logger = logging.getLogger(__name__)


class GeofenceResolver:
    """Resolves geographic coordinates to geofence names using spatial indexing."""
    
    def __init__(self, client: SamsaraClient, cache_ttl: timedelta = timedelta(hours=6)):
        """Initialize geofence resolver.
        
        Args:
            client: SamsaraClient instance for API calls
            cache_ttl: Time to live for spatial index cache
        """
        self.client = client
        self.cache_ttl = cache_ttl
        self.cache_dir = client.cache_manager.cache_dir
        self.index_cache_file = self.cache_dir / 'geofence_index.pkl'
        self.manifest_file = self.cache_dir / 'geofence_manifest.json'
        
        # Spatial index data
        self.addresses: List[Dict] = []
        self.spatial_index: Dict[str, List[int]] = {}  # Grid-based index
        self.id_to_address: Dict[str, Dict] = {}
        
        # Grid parameters for spatial indexing (roughly 0.01 degree cells ≈ 1km)
        self.grid_size = 0.01
        
        self._initialize_index()
    
    def _initialize_index(self):
        """Initialize or load the spatial index."""
        if self._should_rebuild_index():
            logger.info("Building new geofence spatial index...")
            self._build_index()
        else:
            logger.info("Loading cached geofence spatial index...")
            self._load_cached_index()
    
    def _should_rebuild_index(self) -> bool:
        """Check if the spatial index needs to be rebuilt."""
        if not self.index_cache_file.exists() or not self.manifest_file.exists():
            return True
        
        try:
            with open(self.manifest_file, 'r') as f:
                manifest = json.load(f)
            
            cache_time = datetime.fromisoformat(manifest['generated_at'])
            return datetime.now() - cache_time > self.cache_ttl
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Invalid manifest file: {e}")
            return True
    
    def _build_index(self):
        """Build the spatial index from fresh address data."""
        # Fetch all addresses
        self.addresses = self.client.get_all_addresses(use_cache=True)
        logger.info(f"Building index for {len(self.addresses)} addresses")
        
        # Clear existing data
        self.spatial_index = {}
        self.id_to_address = {}
        
        # Build spatial index and address lookup
        for address in self.addresses:
            address_id = address.get('id')
            if not address_id:
                continue
                
            # Store address lookup
            self.id_to_address[address_id] = address
            
            # Get coordinates from address
            lat = address.get('latitude')
            lon = address.get('longitude')
            
            if lat is None or lon is None:
                continue
            
            # Add to spatial grid
            grid_key = self._get_grid_key(lat, lon)
            if grid_key not in self.spatial_index:
                self.spatial_index[grid_key] = []
            self.spatial_index[grid_key].append(address_id)
            
            # Also add to neighboring cells for geofences with radius
            geofence = address.get('geofence', {})
            if 'circle' in geofence:
                radius_m = geofence['circle'].get('radius', 0)
                if radius_m > 0:
                    # Add to neighboring grid cells based on radius
                    self._add_to_neighboring_cells(lat, lon, radius_m, address_id)
        
        # Save the built index
        self._save_cached_index()
        logger.info(f"Spatial index built with {len(self.spatial_index)} grid cells")
    
    def _get_grid_key(self, lat: float, lon: float) -> str:
        """Get grid cell key for coordinates."""
        grid_lat = int(lat / self.grid_size)
        grid_lon = int(lon / self.grid_size)
        return f"{grid_lat},{grid_lon}"
    
    def _add_to_neighboring_cells(self, lat: float, lon: float, radius_m: float, address_id: str):
        """Add address to neighboring grid cells based on geofence radius."""
        # Approximate degrees per meter (rough calculation)
        lat_deg_per_m = 1 / 111320  # roughly 111km per degree latitude
        lon_deg_per_m = 1 / (111320 * cos(radians(lat)))  # varies by latitude
        
        # Calculate grid cell range to cover
        lat_range = int((radius_m * lat_deg_per_m) / self.grid_size) + 1
        lon_range = int((radius_m * lon_deg_per_m) / self.grid_size) + 1
        
        center_lat_grid = int(lat / self.grid_size)
        center_lon_grid = int(lon / self.grid_size)
        
        # Add to neighboring cells
        for dlat in range(-lat_range, lat_range + 1):
            for dlon in range(-lon_range, lon_range + 1):
                if dlat == 0 and dlon == 0:
                    continue  # Already added to center cell
                
                grid_key = f"{center_lat_grid + dlat},{center_lon_grid + dlon}"
                if grid_key not in self.spatial_index:
                    self.spatial_index[grid_key] = []
                if address_id not in self.spatial_index[grid_key]:
                    self.spatial_index[grid_key].append(address_id)
    
    def _save_cached_index(self):
        """Save the spatial index to cache."""
        try:
            # Save the index data
            cache_data = {
                'spatial_index': self.spatial_index,
                'id_to_address': self.id_to_address,
                'addresses': self.addresses
            }
            
            with open(self.index_cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
            
            # Save manifest
            manifest = {
                'generated_at': datetime.now().isoformat(),
                'address_count': len(self.addresses),
                'grid_cells': len(self.spatial_index)
            }
            
            with open(self.manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save spatial index cache: {e}")
    
    def _load_cached_index(self):
        """Load the spatial index from cache."""
        try:
            with open(self.index_cache_file, 'rb') as f:
                cache_data = pickle.load(f)
            
            self.spatial_index = cache_data['spatial_index']
            self.id_to_address = cache_data['id_to_address']
            self.addresses = cache_data['addresses']
            
            logger.info(f"Loaded cached index with {len(self.addresses)} addresses, "
                       f"{len(self.spatial_index)} grid cells")
                       
        except Exception as e:
            logger.error(f"Failed to load cached spatial index: {e}")
            # Fall back to rebuilding
            self._build_index()
    
    def resolve(self, latitude: float, longitude: float) -> Optional[str]:
        """Resolve coordinates to geofence name.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            
        Returns:
            Geofence name if found, None otherwise
        """
        if latitude is None or longitude is None:
            return None
        
        # Get candidate addresses from spatial index
        grid_key = self._get_grid_key(latitude, longitude)
        candidate_ids = self.spatial_index.get(grid_key, [])
        
        if not candidate_ids:
            return None
        
        # Check each candidate for precise match
        for address_id in candidate_ids:
            address = self.id_to_address.get(address_id)
            if not address:
                continue
            
            if self._point_in_geofence(latitude, longitude, address):
                return address.get('name', 'Unknown')
        
        return None
    
    def _point_in_geofence(self, lat: float, lon: float, address: Dict) -> bool:
        """Check if point is within the address geofence."""
        geofence = address.get('geofence', {})
        
        if 'circle' in geofence:
            return self._point_in_circle(lat, lon, address, geofence['circle'])
        elif 'polygon' in geofence:
            return self._point_in_polygon(lat, lon, geofence['polygon'])
        
        return False
    
    def _point_in_circle(self, lat: float, lon: float, address: Dict, circle: Dict) -> bool:
        """Check if point is within circular geofence."""
        center_lat = address.get('latitude')
        center_lon = address.get('longitude')
        radius_m = circle.get('radius', 0)
        
        if center_lat is None or center_lon is None or radius_m <= 0:
            return False
        
        distance_m = self._haversine_distance(lat, lon, center_lat, center_lon)
        return distance_m <= radius_m
    
    def _point_in_polygon(self, lat: float, lon: float, polygon: Dict) -> bool:
        """Check if point is within polygon geofence using ray casting."""
        vertices = polygon.get('vertices', [])
        if len(vertices) < 3:
            return False
        
        # Ray casting algorithm
        inside = False
        j = len(vertices) - 1
        
        for i in range(len(vertices)):
            vertex_i = vertices[i]
            vertex_j = vertices[j]
            
            lat_i = vertex_i.get('latitude')
            lon_i = vertex_i.get('longitude')
            lat_j = vertex_j.get('latitude')
            lon_j = vertex_j.get('longitude')
            
            if (lat_i is None or lon_i is None or 
                lat_j is None or lon_j is None):
                continue
            
            if ((lat_i > lat) != (lat_j > lat)) and \
               (lon < (lon_j - lon_i) * (lat - lat_i) / (lat_j - lat_i) + lon_i):
                inside = not inside
            
            j = i
        
        return inside
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate haversine distance between two points in meters."""
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        # Earth radius in meters
        r = 6371000
        return r * c