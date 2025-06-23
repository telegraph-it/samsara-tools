"""Geofence querying functionality for Samsara API."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from .client import SamsaraClient

logger = logging.getLogger(__name__)


class SamsaraGeofenceQuery(SamsaraClient):
    """Specialized client for querying geofences by tags."""
    
    def __init__(self, api_token: str, **kwargs):
        """Initialize geofence query client.
        
        Args:
            api_token: Samsara API token
            **kwargs: Additional arguments passed to SamsaraClient
        """
        super().__init__(api_token, **kwargs)
        self.output_dir = Path('data/output')
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def query_geofences_by_tag(self, tag_name: str) -> List[Dict]:
        """Query all geofences associated with a specific tag.
        
        Args:
            tag_name: Name of the tag to search for
            
        Returns:
            List of geofence data dictionaries
        """
        logger.info(f"Searching for tag: '{tag_name}'...")
        
        # Step 1: Find the tag
        tag = self.find_tag_by_name(tag_name)
        if not tag:
            logger.warning(f"Tag '{tag_name}' not found")
            return []
        
        logger.info(f"Found tag: {tag['name']} (ID: {tag['id']})")
        
        # Step 2: Get tag details with associated addresses
        tag_details = self.get_tag_details(tag['id'])
        if not tag_details:
            logger.error("Failed to get tag details")
            return []
        
        addresses = tag_details.get('addresses', [])
        logger.info(f"Found {len(addresses)} addresses associated with tag '{tag_name}'")
        
        # Step 3: Get geofence details for each address
        geofences = []
        for i, address in enumerate(addresses, 1):
            logger.info(f"Processing address {i}/{len(addresses)}: {address['name']}")
            
            address_details = self.get_address_details(address['id'])
            if address_details:
                geofence_data = self._format_geofence_data(address_details)
                geofences.append(geofence_data)
        
        logger.info(f"Successfully processed {len(geofences)} geofences")
        return geofences
    
    def _format_geofence_data(self, address_details: Dict) -> Dict:
        """Format address details into a standardized geofence data structure.
        
        Args:
            address_details: Raw address data from API
            
        Returns:
            Formatted geofence data dictionary
        """
        return {
            'address_id': address_details['id'],
            'name': address_details['name'],
            'formatted_address': address_details['formattedAddress'],
            'geofence': address_details.get('geofence', {}),
            'latitude': address_details.get('latitude'),
            'longitude': address_details.get('longitude'),
            'notes': address_details.get('notes', ''),
            'address_types': address_details.get('addressTypes', []),
            'created_at': address_details.get('createdAtTime'),
            'contacts': address_details.get('contacts', []),
            'tags': address_details.get('tags', [])
        }
    
    def save_results(self, geofences: List[Dict], tag_name: str) -> Dict[str, Path]:
        """Save geofence results to JSON and CSV files.
        
        Args:
            geofences: List of geofence data
            tag_name: Tag name for filename
            
        Returns:
            Dictionary with paths to saved files
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_tag_name = tag_name.lower().replace(' ', '_')
        
        saved_files = {}
        
        # Save as JSON
        json_filename = self.output_dir / f"geofences_{safe_tag_name}_{timestamp}.json" 
        with open(json_filename, 'w') as f:
            json.dump(geofences, f, indent=2, default=str)
        saved_files['json'] = json_filename
        logger.info(f"JSON results saved to: {json_filename}")
        
        # Save as CSV
        if geofences:
            import csv
            csv_filename = self.output_dir / f"geofences_{safe_tag_name}_{timestamp}.csv"
            
            with open(csv_filename, 'w', newline='') as f:
                writer = csv.writer(f)
                
                # Header
                writer.writerow([
                    'Address ID', 'Name', 'Formatted Address', 'Latitude', 'Longitude',
                    'Geofence Type', 'Geofence Data', 'Address Types', 'Notes', 'Created At'
                ])
                
                # Data rows
                for geofence in geofences:
                    geofence_type = self._get_geofence_type(geofence['geofence'])
                    geofence_data = json.dumps(geofence['geofence'])
                    address_types = ', '.join(geofence['address_types'])
                    
                    writer.writerow([
                        geofence['address_id'],
                        geofence['name'],
                        geofence['formatted_address'],
                        geofence['latitude'],
                        geofence['longitude'],
                        geofence_type,
                        geofence_data,
                        address_types,
                        geofence['notes'],
                        geofence['created_at']
                    ])
            
            saved_files['csv'] = csv_filename
            logger.info(f"CSV results saved to: {csv_filename}")
        
        return saved_files
    
    def _get_geofence_type(self, geofence: Dict) -> str:
        """Determine the type of geofence from the geofence data.
        
        Args:
            geofence: Geofence data dictionary
            
        Returns:
            String describing the geofence type
        """
        if 'circle' in geofence:
            return 'circle'
        elif 'polygon' in geofence:
            return 'polygon'
        else:
            return 'unknown'
    
    def print_geofence_summary(self, geofences: List[Dict], tag_name: str):
        """Print a formatted summary of geofences to console.
        
        Args:
            geofences: List of geofence data
            tag_name: Tag name for display
        """
        if not geofences:
            print(f"\nNo geofences found with tag '{tag_name}'")
            return
        
        print(f"\nFound {len(geofences)} geofences with tag '{tag_name}':")
        print("=" * 50)
        
        for i, geofence in enumerate(geofences, 1):
            print(f"\n{i}. {geofence['name']}")
            print(f"   Address: {geofence['formatted_address']}")
            print(f"   Coordinates: ({geofence['latitude']}, {geofence['longitude']})")
            
            geofence_info = geofence['geofence']
            if 'circle' in geofence_info:
                circle = geofence_info['circle']
                radius = circle.get('radius', 'N/A')
                print(f"   Geofence: Circle (radius: {radius}m)")
            elif 'polygon' in geofence_info:
                polygon = geofence_info['polygon']
                vertices = polygon.get('vertices', [])
                print(f"   Geofence: Polygon ({len(vertices)} vertices)")
            else:
                print(f"   Geofence: Unknown type") 