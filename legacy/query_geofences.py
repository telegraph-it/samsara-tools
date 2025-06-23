#!/usr/bin/env python3
"""
Samsara API Geofence Query Script
Query geofences that have a specific tag value.
"""

# Standard library imports
import csv
import json
import logging
import os
import sys
from datetime import datetime
from typing import List, Dict, Optional, Union

# Third-party imports
import requests
from dotenv import load_dotenv


class SamsaraGeofenceQuery:
    """Samsara API client for querying geofences by tag."""
    
    # Configuration constants
    DEFAULT_BASE_URL = "https://api.samsara.com"
    REQUEST_TIMEOUT = 30
    DEFAULT_TAG_NAME = "Maas"
    OUTPUT_DIR = "data/output"
    CACHE_DIR = "data/cache"
    CACHE_DURATION = 3600  # 1 hour in seconds
    
    # CSV headers
    CSV_HEADERS = [
        'Address ID', 'Name', 'Formatted Address', 'Latitude', 'Longitude',
        'Geofence Type', 'Geofence Data', 'Address Types', 'Notes', 'Created At'
    ]
    
    def __init__(self, api_token: str, base_url: str = DEFAULT_BASE_URL, use_cache: bool = True):
        """Initialize the Samsara geofence query client.
        
        Args:
            api_token: Samsara API bearer token for authentication
            base_url: Base URL for Samsara API endpoints
            use_cache: Whether to use file-based caching for API responses
        """
        if not api_token or not api_token.strip():
            raise ValueError("API token cannot be empty")
            
        self.api_token = api_token.strip()
        self.base_url = base_url.rstrip('/')
        self.use_cache = use_cache
        self.headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Initialize cache directory if caching is enabled
        if self.use_cache:
            os.makedirs(self.CACHE_DIR, exist_ok=True)
    
    def _get_cache_path(self, cache_key: str) -> str:
        """Get the file path for a cache key."""
        return os.path.join(self.CACHE_DIR, f"{cache_key}.json")
    
    def _load_from_cache(self, cache_key: str) -> Optional[Dict]:
        """Load data from cache if it exists and is not expired."""
        if not self.use_cache:
            return None
            
        cache_path = self._get_cache_path(cache_key)
        if not os.path.exists(cache_path):
            return None
            
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                
            # Check if cache is expired
            cache_time = cache_data.get('timestamp', 0)
            if datetime.now().timestamp() - cache_time > self.CACHE_DURATION:
                logging.debug(f"Cache expired for key: {cache_key}")
                return None
                
            logging.debug(f"Cache hit for key: {cache_key}")
            return cache_data.get('data')
            
        except (json.JSONDecodeError, OSError) as e:
            logging.warning(f"Failed to load cache for key {cache_key}: {e}")
            return None
    
    def _save_to_cache(self, cache_key: str, data: Dict) -> None:
        """Save data to cache."""
        if not self.use_cache:
            return
            
        cache_path = self._get_cache_path(cache_key)
        cache_data = {
            'timestamp': datetime.now().timestamp(),
            'data': data
        }
        
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, default=str, ensure_ascii=False)
            logging.debug(f"Cached data for key: {cache_key}")
        except (OSError, TypeError) as e:
            logging.warning(f"Failed to save cache for key {cache_key}: {e}")
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        if not os.path.exists(self.CACHE_DIR):
            return
            
        try:
            for filename in os.listdir(self.CACHE_DIR):
                if filename.endswith('.json'):
                    os.remove(os.path.join(self.CACHE_DIR, filename))
            logging.info("Cache cleared successfully")
        except OSError as e:
            logging.error(f"Failed to clear cache: {e}")
    
    def get_all_tags(self) -> List[Dict]:
        """Retrieve all tags from Samsara API with pagination support.
        
        Returns:
            List of tag dictionaries from the API
            
        Raises:
            requests.RequestException: If API request fails
            ValueError: If API response is malformed
        """
        cache_key = "all_tags"
        
        # Try to load from cache first
        cached_data = self._load_from_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        url = f"{self.base_url}/tags"
        all_tags = []
        
        try:
            while url:
                response = self.session.get(url, timeout=self.REQUEST_TIMEOUT)
                response.raise_for_status()
                
                try:
                    data = response.json()
                except ValueError as e:
                    raise ValueError(f"Invalid JSON response from API: {e}")
                
                if 'data' not in data:
                    raise ValueError("API response missing 'data' field")
                    
                all_tags.extend(data['data'])
                
                # Check for pagination
                pagination = data.get('pagination', {})
                if pagination.get('hasNextPage', False):
                    cursor = pagination.get('endCursor', '')
                    if not cursor:
                        logging.warning("Pagination indicated but no endCursor provided")
                        break
                    url = f"{self.base_url}/tags?after={cursor}"
                else:
                    url = None
                    
        except requests.Timeout:
            raise requests.RequestException(f"Request timeout after {self.REQUEST_TIMEOUT} seconds")
        except requests.RequestException as e:
            raise requests.RequestException(f"Error fetching tags: {e}")
        
        # Cache the results
        self._save_to_cache(cache_key, all_tags)
        return all_tags
    
    def find_tag_by_name(self, tag_name: str) -> Optional[Dict]:
        """Find a tag by name.
        
        Args:
            tag_name: Name of the tag to search for
            
        Returns:
            Tag dictionary if found, None otherwise
            
        Raises:
            ValueError: If tag_name is empty or invalid
        """
        if not tag_name or not tag_name.strip():
            raise ValueError("Tag name cannot be empty")
            
        tag_name = tag_name.strip()
        tags = self.get_all_tags()
        
        for tag in tags:
            if not isinstance(tag, dict) or 'name' not in tag:
                logging.warning(f"Malformed tag data: {tag}")
                continue
            if tag['name'] == tag_name:
                return tag
                
        return None
    
    def get_tag_details(self, tag_id: str) -> Optional[Dict]:
        """Get detailed information for a specific tag.
        
        Args:
            tag_id: ID of the tag to retrieve details for
            
        Returns:
            Tag details dictionary if successful, None otherwise
            
        Raises:
            ValueError: If tag_id is empty or invalid
        """
        if not tag_id or not tag_id.strip():
            raise ValueError("Tag ID cannot be empty")
            
        tag_id = tag_id.strip()
        url = f"{self.base_url}/tags/{tag_id}"
        
        try:
            response = self.session.get(url, timeout=self.REQUEST_TIMEOUT)
            response.raise_for_status()
            
            try:
                data = response.json()
            except ValueError as e:
                logging.error(f"Invalid JSON response for tag {tag_id}: {e}")
                return None
                
            if 'data' not in data:
                logging.error(f"API response missing 'data' field for tag {tag_id}")
                return None
                
            return data['data']
            
        except requests.Timeout:
            logging.error(f"Request timeout for tag {tag_id} after {self.REQUEST_TIMEOUT} seconds")
            return None
        except requests.RequestException as e:
            logging.error(f"Error fetching tag details for {tag_id}: {e}")
            return None
    
    def get_address_details(self, address_id: str) -> Optional[Dict]:
        """Get detailed information for a specific address including geofence.
        
        Args:
            address_id: ID of the address to retrieve details for
            
        Returns:
            Address details dictionary if successful, None otherwise
            
        Raises:
            ValueError: If address_id is empty or invalid
        """
        if not address_id or not address_id.strip():
            raise ValueError("Address ID cannot be empty")
            
        address_id = address_id.strip()
        url = f"{self.base_url}/addresses/{address_id}"
        
        try:
            response = self.session.get(url, timeout=self.REQUEST_TIMEOUT)
            response.raise_for_status()
            
            try:
                data = response.json()
            except ValueError as e:
                logging.error(f"Invalid JSON response for address {address_id}: {e}")
                return None
                
            if 'data' not in data:
                logging.error(f"API response missing 'data' field for address {address_id}")
                return None
                
            return data['data']
            
        except requests.Timeout:
            logging.error(f"Request timeout for address {address_id} after {self.REQUEST_TIMEOUT} seconds")
            return None
        except requests.RequestException as e:
            logging.error(f"Error fetching address details for {address_id}: {e}")
            return None
    
    def _validate_coordinates(self, latitude: Union[float, str, None], longitude: Union[float, str, None]) -> tuple[Optional[float], Optional[float]]:
        """Validate and convert latitude/longitude coordinates.
        
        Args:
            latitude: Latitude value to validate
            longitude: Longitude value to validate
            
        Returns:
            Tuple of validated (lat, lon) or (None, None) if invalid
        """
        try:
            if latitude is not None and longitude is not None:
                lat = float(latitude)
                lon = float(longitude)
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    return lat, lon
        except (ValueError, TypeError):
            pass
        return None, None
    
    def query_geofences_by_tag(self, tag_name: str) -> List[Dict]:
        """Query all geofences associated with a specific tag.
        
        Args:
            tag_name: Name of the tag to search for
            
        Returns:
            List of geofence data dictionaries
            
        Raises:
            ValueError: If tag_name is invalid
        """
        if not tag_name or not tag_name.strip():
            raise ValueError("Tag name cannot be empty")
            
        tag_name = tag_name.strip()
        logging.info(f"Searching for tag: '{tag_name}'...")
        
        # Step 1: Find the tag
        try:
            tag = self.find_tag_by_name(tag_name)
            if not tag:
                logging.warning(f"Tag '{tag_name}' not found")
                return []
        except Exception as e:
            logging.error(f"Error searching for tag '{tag_name}': {e}")
            return []
        
        if 'id' not in tag:
            logging.error(f"Tag data missing 'id' field: {tag}")
            return []
            
        logging.info(f"Found tag: {tag['name']} (ID: {tag['id']})")
        
        # Step 2: Get tag details with associated addresses
        try:
            tag_details = self.get_tag_details(tag['id'])
            if not tag_details:
                logging.error("Failed to get tag details")
                return []
        except Exception as e:
            logging.error(f"Error fetching tag details: {e}")
            return []
        
        addresses = tag_details.get('addresses', [])
        if not addresses:
            logging.info(f"No addresses found for tag '{tag_name}'")
            return []
            
        logging.info(f"Found {len(addresses)} addresses associated with tag '{tag_name}'")
        
        # Step 3: Get geofence details for each address
        geofences = []
        for i, address in enumerate(addresses, 1):
            if not isinstance(address, dict) or 'id' not in address:
                logging.warning(f"Malformed address data at index {i}: {address}")
                continue
                
            address_name = address.get('name', f'Address {i}')
            logging.info(f"Processing address {i}/{len(addresses)}: {address_name}")
            
            try:
                address_details = self.get_address_details(address['id'])
                if not address_details:
                    logging.warning(f"Failed to get details for address {address['id']}")
                    continue
                    
                # Validate coordinates
                lat, lon = self._validate_coordinates(
                    address_details.get('latitude'),
                    address_details.get('longitude')
                )
                
                geofence_data = {
                    'address_id': address['id'],
                    'name': address_details.get('name', 'Unknown'),
                    'formatted_address': address_details.get('formattedAddress', ''),
                    'geofence': address_details.get('geofence', {}),
                    'latitude': lat,
                    'longitude': lon,
                    'notes': address_details.get('notes', ''),
                    'address_types': address_details.get('addressTypes', []),
                    'created_at': address_details.get('createdAtTime'),
                    'contacts': address_details.get('contacts', []),
                    'tags': address_details.get('tags', [])
                }
                geofences.append(geofence_data)
                
            except Exception as e:
                logging.error(f"Error processing address {address['id']}: {e}")
                continue
        
        logging.info(f"Successfully processed {len(geofences)} geofences")
        return geofences
    
    def _determine_geofence_type(self, geofence_data: Dict) -> str:
        """Determine the type of geofence from geofence data.
        
        Args:
            geofence_data: Dictionary containing geofence information
            
        Returns:
            String indicating geofence type ('circle', 'polygon', or 'unknown')
        """
        if not isinstance(geofence_data, dict):
            return 'unknown'
        if 'circle' in geofence_data:
            return 'circle'
        elif 'polygon' in geofence_data:
            return 'polygon'
        else:
            return 'unknown'
    
    def save_results(self, geofences: List[Dict], tag_name: str) -> tuple[str, Optional[str]]:
        """Save results to JSON and CSV files.
        
        Args:
            geofences: List of geofence data dictionaries
            tag_name: Name of the tag (used in filenames)
            
        Returns:
            Tuple of (json_filename, csv_filename). csv_filename is None if no data to save.
            
        Raises:
            ValueError: If parameters are invalid
            OSError: If file operations fail
        """
        if not isinstance(geofences, list):
            raise ValueError("Geofences must be a list")
        if not tag_name or not tag_name.strip():
            raise ValueError("Tag name cannot be empty")
            
        tag_name = tag_name.strip()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Ensure output directory exists
        try:
            os.makedirs(self.OUTPUT_DIR, exist_ok=True)
        except OSError as e:
            raise OSError(f"Failed to create output directory {self.OUTPUT_DIR}: {e}")
        
        # Save as JSON
        json_filename = f"{self.OUTPUT_DIR}/geofences_{tag_name.lower()}_{timestamp}.json"
        try:
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(geofences, f, indent=2, default=str, ensure_ascii=False)
            logging.info(f"JSON results saved to: {json_filename}")
        except (OSError, TypeError) as e:
            raise OSError(f"Failed to save JSON file {json_filename}: {e}")
        
        csv_filename = None
        # Save as CSV if we have data
        if geofences:
            csv_filename = f"{self.OUTPUT_DIR}/geofences_{tag_name.lower()}_{timestamp}.csv"
            
            try:
                with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    
                    # Header
                    writer.writerow(self.CSV_HEADERS)
                    
                    # Data rows
                    for geofence in geofences:
                        if not isinstance(geofence, dict):
                            logging.warning(f"Skipping malformed geofence data: {geofence}")
                            continue
                            
                        geofence_type = self._determine_geofence_type(geofence.get('geofence', {}))
                        geofence_data = json.dumps(geofence.get('geofence', {}), default=str)
                        address_types = ', '.join(geofence.get('address_types', []))
                        
                        writer.writerow([
                            geofence.get('address_id', ''),
                            geofence.get('name', ''),
                            geofence.get('formatted_address', ''),
                            geofence.get('latitude', ''),
                            geofence.get('longitude', ''),
                            geofence_type,
                            geofence_data,
                            address_types,
                            geofence.get('notes', ''),
                            geofence.get('created_at', '')
                        ])
                
                logging.info(f"CSV results saved to: {csv_filename}")
                
            except (OSError, csv.Error) as e:
                raise OSError(f"Failed to save CSV file {csv_filename}: {e}")
        
        return json_filename, csv_filename
    
    def close(self):
        """Clean up resources, particularly the requests session."""
        if hasattr(self, 'session'):
            self.session.close()


def main():
    """Main function to run the geofence query application."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    try:
        # Load environment variables from .env file
        load_dotenv()
        
        # Get API token from environment variable
        api_token = os.getenv('SAMSARA_API_TOKEN')
        if not api_token:
            print("Error: SAMSARA_API_TOKEN environment variable not set")
            print("Please create a .env file in this directory with:")
            print("SAMSARA_API_TOKEN=your_token_here")
            print("Or set the environment variable:")
            print("export SAMSARA_API_TOKEN='your_token_here'")
            sys.exit(1)
        
        # Get tag name from command line argument or use default
        tag_name = sys.argv[1] if len(sys.argv) > 1 else SamsaraGeofenceQuery.DEFAULT_TAG_NAME
        
        # Initialize the query client  
        client = None
        try:
            client = SamsaraGeofenceQuery(api_token)
            
            print(f"Querying Samsara API for geofences with tag: '{tag_name}'")
            print("=" * 50)
            
            # Query geofences
            geofences = client.query_geofences_by_tag(tag_name)
            
            if geofences:
                print(f"\nFound {len(geofences)} geofences with tag '{tag_name}':")
                print("=" * 50)
                
                for i, geofence in enumerate(geofences, 1):
                    name = geofence.get('name', 'Unknown')
                    address = geofence.get('formatted_address', 'N/A')
                    lat = geofence.get('latitude', 'N/A')
                    lon = geofence.get('longitude', 'N/A')
                    
                    print(f"\n{i}. {name}")
                    print(f"   Address: {address}")
                    print(f"   Coordinates: ({lat}, {lon})")
                    
                    geofence_info = geofence.get('geofence', {})
                    if 'circle' in geofence_info:
                        circle = geofence_info['circle']
                        radius = circle.get('radius', 'N/A')
                        print(f"   Geofence: Circle (radius: {radius}m)")
                    elif 'polygon' in geofence_info:
                        polygon = geofence_info['polygon']
                        vertices = polygon.get('vertices', [])
                        print(f"   Geofence: Polygon ({len(vertices)} vertices)")
                    else:
                        print("   Geofence: Unknown type")
                
                # Save results
                try:
                    json_file, csv_file = client.save_results(geofences, tag_name)
                    print(f"\nResults saved:")
                    print(f"  JSON: {json_file}")
                    if csv_file:
                        print(f"  CSV: {csv_file}")
                except Exception as e:
                    logging.error(f"Failed to save results: {e}")
                    print(f"Error: Failed to save results - {e}")
                    
            else:
                print(f"\nNo geofences found with tag '{tag_name}'")
                
        except ValueError as e:
            logging.error(f"Invalid input: {e}")
            print(f"Error: {e}")
            sys.exit(1)
        except Exception as e:
            logging.error(f"Unexpected error during execution: {e}")
            print(f"Error: An unexpected error occurred - {e}")
            sys.exit(1)
        finally:
            # Clean up resources
            if client:
                client.close()
                
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Fatal error in main: {e}")
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 