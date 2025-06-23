import requests
from datetime import datetime, timedelta, timezone
import pandas as pd
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import argparse
from dotenv import load_dotenv
import random

# Configuration constants
CACHE_DIR = Path('data/cache')
CACHE_DURATION = timedelta(hours=1)  # Refresh cache after 1 hour
RESULTS_DIR = Path('data/output')
MAX_GEOCODING_WORKERS = 5
MAX_API_WORKERS = 5  # Reduced from 10 to avoid rate limits
GEOCODING_BATCH_SIZE = 5
LOCATION_HISTORY_DAYS = 1825  # 5 years
BATCH_SIZE = 10  # Process assets in batches of 10


class RateLimiter:
    """Handles API rate limiting with exponential backoff and retry logic"""
    
    def __init__(self, base_delay=1, max_delay=60, max_retries=5):
        """Initialize rate limiter with configurable parameters
        
        Args:
            base_delay: Base delay in seconds between retries
            max_delay: Maximum delay in seconds
            max_retries: Maximum number of retry attempts
        """
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.max_retries = max_retries
        self.last_request_time = 0
        self.min_interval = 0.5  # Minimum interval between requests in seconds
    
    def wait(self):
        """Wait for minimum interval between requests"""
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.min_interval:
            sleep_time = self.min_interval - elapsed
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def execute_with_retry(self, func, *args, **kwargs):
        """Execute a function with retry logic and exponential backoff
        
        Args:
            func: Function to execute
            *args, **kwargs: Arguments to pass to the function
            
        Returns:
            Result of the function or raises the last exception
        """
        retries = 0
        last_exception = None
        
        while retries <= self.max_retries:
            try:
                # Wait before making request
                self.wait()
                
                # Execute the function
                return func(*args, **kwargs)
                
            except requests.exceptions.HTTPError as e:
                last_exception = e
                
                # Check if it's a rate limit error (429)
                if e.response.status_code == 429:
                    retries += 1
                    if retries > self.max_retries:
                        break
                        
                    # Calculate delay with exponential backoff and jitter
                    delay = min(self.max_delay, self.base_delay * (2 ** (retries - 1)))
                    jitter = random.uniform(0, 0.1 * delay)  # 10% jitter
                    delay += jitter
                    
                    print(f"Rate limit exceeded. Retrying in {delay:.2f} seconds... (Attempt {retries}/{self.max_retries})")
                    time.sleep(delay)
                else:
                    # For other HTTP errors, raise immediately
                    raise
            except Exception as e:
                # For non-HTTP errors, raise immediately
                last_exception = e
                raise
                
        # If we've exhausted retries, raise the last exception
        if last_exception:
            print(f"Max retries exceeded. Last error: {last_exception}")
            raise last_exception


class CacheManager:
    """Handles caching operations for API data"""
    
    @staticmethod
    def ensure_directories():
        """Ensure cache and results directories exist"""
        CACHE_DIR.mkdir(exist_ok=True)
        RESULTS_DIR.mkdir(exist_ok=True)

    @staticmethod
    def load_cache(cache_file):
        """Load data from cache if it exists and is fresh"""
        if not cache_file.exists():
            return None
            
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
                
            cache_time = datetime.fromisoformat(cache_data['timestamp'])
            if datetime.now(timezone.utc) - cache_time < CACHE_DURATION:
                return cache_data['data']
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Cache error: {e}")
        return None

    @staticmethod
    def save_cache(cache_file, data):
        """Save data to cache with timestamp"""
        cache_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'data': data
        }
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f)


class SamsaraAPIClient:
    """Client for interacting with the Samsara API"""
    
    def __init__(self, api_token):
        """Initialize with API token"""
        self.api_token = api_token
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Accept": "application/json"
        }
        self.rate_limiter = RateLimiter()
        
    def verify_api_access(self):
        """Verify API access and token validity"""
        try:
            # Try to access a simple endpoint to verify API access
            url = "https://api.samsara.com/fleet/drivers"
            params = {"limit": 1}
            
            def make_request():
                response = requests.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                return response.json()
                
            data = self.rate_limiter.execute_with_retry(make_request)
            return True, "API access verified successfully"
        except requests.exceptions.RequestException as e:
            return False, f"API access verification failed: {e}"

    def get_gateways(self):
        """Fetches all gateways and their basic info from Samsara API"""
        cache_file = CACHE_DIR / 'gateways.json'
        cached_data = CacheManager.load_cache(cache_file)
        if cached_data:
            print("Using cached gateway data...")
            return cached_data

        url = "https://api.samsara.com/gateways"
        
        try:
            # Use rate limiter for API request
            def make_request():
                response = requests.get(url, headers=self.headers)
                response.raise_for_status()
                return response.json().get('data', [])
                
            data = self.rate_limiter.execute_with_retry(make_request)
            CacheManager.save_cache(cache_file, data)
            return data
        except requests.exceptions.RequestException as e:
            print(f"Error fetching gateway data: {e}")
            return []

    def _fetch_single_location(self, args):
        """Helper function to fetch location data for a single asset"""
        asset_id, start_time_str, end_time_str = args
        base_url = "https://api.samsara.com/assets/location-and-speed/stream"
        
        params = {
            'limit': 512,
            'startTime': start_time_str,
            'endTime': end_time_str,
            'ids': asset_id
        }
        
        try:
            # Use rate limiter for API request
            def make_request():
                response = requests.get(base_url, headers=self.headers, params=params)
                response.raise_for_status()
                return response.json()
                
            data = self.rate_limiter.execute_with_retry(make_request)
            
            # Process location data for this asset
            location_info = None
            latest_time = None
            
            # Check if we have data
            if not data.get('data'):
                # Try alternative endpoint immediately for this asset
                alt_location = self._try_alternative_location_endpoint(asset_id)
                if alt_location:
                    return asset_id, alt_location
                return asset_id, None
            
            for item in data.get('data', []):
                location = item.get('location', {})
                happened_at = item.get('happenedAtTime')
                
                if not location:
                    continue
                    
                if not location_info or (happened_at and (not latest_time or happened_at > latest_time)):
                    latest_time = happened_at
                    location_info = {
                        'latitude': location.get('latitude'),
                        'longitude': location.get('longitude'),
                        'location_time': happened_at,
                        'accuracy_meters': location.get('accuracyMeters'),
                        'heading': location.get('headingDegrees')
                    }
            
            return asset_id, location_info
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching location data for asset {asset_id}: {e}")
            # Try alternative endpoint as fallback
            try:
                alt_location = self._try_alternative_location_endpoint(asset_id)
                if alt_location:
                    print(f"Successfully retrieved location for asset {asset_id} using alternative endpoint")
                    return asset_id, alt_location
            except Exception as alt_e:
                print(f"Alternative endpoint also failed for asset {asset_id}: {alt_e}")
            return asset_id, None

    def _fetch_batch_locations(self, asset_ids_batch, start_time_str, end_time_str):
        """Fetch location data for a batch of assets"""
        base_url = "https://api.samsara.com/assets/location-and-speed/stream"
        
        # Join asset IDs with commas for batch request
        ids_param = ','.join(map(str, asset_ids_batch))
        
        params = {
            'limit': 512,
            'startTime': start_time_str,
            'endTime': end_time_str,
            'ids': ids_param
        }
        
        try:
            # Use rate limiter for API request
            def make_request():
                response = requests.get(base_url, headers=self.headers, params=params)
                response.raise_for_status()
                return response.json()
                
            data = self.rate_limiter.execute_with_retry(make_request)
            
            # Process location data for each asset in the batch
            results = {}
            
            # Debug the API response structure
            if not data.get('data'):
                print(f"Warning: No location data returned for batch with {len(asset_ids_batch)} assets.")
                # Check if there's pagination info that might be useful
                if 'pagination' in data:
                    print(f"Pagination info present. This might indicate more data is available.")
                return {}
                
            for item in data.get('data', []):
                asset_id = item.get('assetId')
                location = item.get('location', {})
                happened_at = item.get('happenedAtTime')
                
                if not asset_id or not location:
                    continue
                
                # Initialize or update asset location info
                if asset_id not in results:
                    results[asset_id] = {
                        'latitude': location.get('latitude'),
                        'longitude': location.get('longitude'),
                        'location_time': happened_at,
                        'accuracy_meters': location.get('accuracyMeters'),
                        'heading': location.get('headingDegrees')
                    }
                else:
                    # Update only if this location is newer
                    current_time = results[asset_id].get('location_time')
                    if happened_at and (not current_time or happened_at > current_time):
                        results[asset_id] = {
                            'latitude': location.get('latitude'),
                            'longitude': location.get('longitude'),
                            'location_time': happened_at,
                            'accuracy_meters': location.get('accuracyMeters'),
                            'heading': location.get('headingDegrees')
                        }
            
            return results
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching location data for batch: {e}")
            return {}

    def _try_alternative_location_endpoint(self, asset_id):
        """Try an alternative endpoint to get location data for a single asset"""
        try:
            # Try the fleet/assets endpoint which might have location data
            url = f"https://api.samsara.com/fleet/assets/{asset_id}"
            
            def make_request():
                response = requests.get(url, headers=self.headers)
                response.raise_for_status()
                return response.json()
                
            data = self.rate_limiter.execute_with_retry(make_request)
            
            # Extract location data if available
            location_data = data.get('location', {})
            if location_data:
                return {
                    'latitude': location_data.get('latitude'),
                    'longitude': location_data.get('longitude'),
                    'location_time': data.get('lastLocationTime'),
                    'accuracy_meters': location_data.get('accuracyMeters', 'N/A'),
                    'heading': location_data.get('heading', 'N/A')
                }
            return None
        except requests.exceptions.RequestException as e:
            print(f"Error fetching alternative location data for asset {asset_id}: {e}")
            return None

    def get_location_data(self, asset_ids, max_workers=MAX_API_WORKERS):
        """Fetches location data for given asset IDs using batched requests with rate limiting"""
        if not asset_ids:
            return {}
            
        cache_file = CACHE_DIR / 'locations.json'
        cached_data = CacheManager.load_cache(cache_file)
        if cached_data:
            print("Using cached location data...")
            return cached_data

        # Get historical data - try with a longer history period
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=LOCATION_HISTORY_DAYS)
        
        # Format times in the correct format
        start_time_str = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        end_time_str = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        print(f"Fetching location data from {start_time_str} to {end_time_str}")
        
        # Create a dict of asset_id to latest location
        locations = {}
        
        # Skip batch processing since it's not working well
        # Go straight to individual processing which seems to work better
        print("Using individual requests for location data...")
        
        # Process all assets with individual requests
        total_assets = len(asset_ids)
        processed_assets = 0
        
        # Use a reasonable number of workers to avoid overwhelming the API
        adjusted_max_workers = min(max_workers, 5)  # Limit to 5 concurrent requests
        
        with ThreadPoolExecutor(max_workers=adjusted_max_workers) as executor:
            args_list = [(asset_id, start_time_str, end_time_str) for asset_id in asset_ids]
            future_to_asset = {
                executor.submit(self._fetch_single_location, args): args[0]
                for args in args_list
            }
            
            for future in as_completed(future_to_asset):
                asset_id = future_to_asset[future]
                try:
                    result_asset_id, location_info = future.result()
                    if location_info:
                        locations[result_asset_id] = location_info
                    
                    # Update progress
                    processed_assets += 1
                    if processed_assets % 10 == 0:
                        print(f"Individual progress: {processed_assets}/{total_assets} assets processed", end='\r')
                except Exception as e:
                    print(f"\nError processing asset {asset_id}: {e}")
        
        print(f"\nCompleted individual processing with {len(locations)}/{total_assets} assets successfully")
        
        # If still no locations, try the alternative endpoint
        if not locations:
            print("No location data found. Trying alternative endpoint...")
            try:
                # Try with a smaller set of assets
                sample_size = min(50, len(asset_ids))
                print(f"Sampling {sample_size} assets for alternative endpoint...")
                sampled_assets = random.sample(asset_ids, sample_size) if len(asset_ids) > sample_size else asset_ids
                
                with ThreadPoolExecutor(max_workers=adjusted_max_workers) as executor:
                    future_to_asset = {
                        executor.submit(self._try_alternative_location_endpoint, asset_id): asset_id
                        for asset_id in sampled_assets
                    }
                    
                    for future in as_completed(future_to_asset):
                        asset_id = future_to_asset[future]
                        try:
                            location_info = future.result()
                            if location_info:
                                locations[asset_id] = location_info
                            
                            # Update progress
                            processed_assets += 1
                            if processed_assets % 5 == 0:
                                print(f"Alternative endpoint progress: {processed_assets}/{len(sampled_assets)} assets processed", end='\r')
                        except Exception as e:
                            print(f"\nError processing asset {asset_id} with alternative endpoint: {e}")
                
                print(f"\nCompleted alternative endpoint processing with {len(locations)}/{len(sampled_assets)} assets successfully")
            except Exception as e:
                print(f"Error during alternative endpoint processing: {e}")
        
        # Cache the results even if empty to avoid repeated API calls
        CacheManager.save_cache(cache_file, locations)
        return locations


class GeocodingService:
    """Service for geocoding coordinates to location names"""
    
    def __init__(self):
        """Initialize the geocoding service with a rate limiter"""
        self.rate_limiter = RateLimiter(base_delay=2, max_delay=120)  # More conservative settings for geocoding
        self.geolocator = Nominatim(
            user_agent="samsara_gateway_tracker",
            timeout=10
        )
    
    def get_location_name(self, latitude, longitude):
        """Get location name from coordinates using OpenStreetMap data with rate limiting"""
        if latitude == 'N/A' or longitude == 'N/A':
            return 'N/A'
        
        try:
            def make_request():
                location = self.geolocator.reverse(f"{latitude}, {longitude}", language='en')
                return location
            
            location = self.rate_limiter.execute_with_retry(make_request)
            
            if location:
                address = location.raw.get('address', {})
                city = address.get('city') or address.get('town') or address.get('village') or 'Unknown'
                state = address.get('state', 'Unknown')
                return f"{city}, {state}"
            return 'Unknown Location'
            
        except Exception as e:
            print(f"\nGeocoding failed for ({latitude}, {longitude}): {str(e)}")
            return 'Geocoding Failed'


class GatewayProcessor:
    """Processes gateway and location data"""
    
    @staticmethod
    def process_gateway_data(gateways, locations):
        """Process gateway and location data into a DataFrame"""
        gateway_data = []
        current_time = datetime.now(timezone.utc)
        
        # First pass: collect all gateway info without location names
        for gateway in gateways:
            connection_status = gateway.get('connectionStatus', {})
            health_status = connection_status.get('healthStatus')
            last_connected_str = connection_status.get('lastConnected')
            
            if last_connected_str:
                last_connected = datetime.fromisoformat(last_connected_str.replace('Z', '+00:00'))
                time_diff = current_time - last_connected
                hours_inactive = time_diff.total_seconds() / 3600
                is_inactive = gateway.get('is_inactive', False)
                last_connected_formatted = last_connected.strftime('%Y-%m-%d %H:%M:%S UTC')
            else:
                last_connected = None
                last_connected_formatted = 'Never'
                hours_inactive = float('inf')
                is_inactive = gateway.get('is_inactive', False)
            
            # Get location data if available
            asset_id = gateway.get('asset', {}).get('id')
            location_info = locations.get(asset_id, {})
            
            latitude = location_info.get('latitude', 'N/A') if location_info else 'N/A'
            longitude = location_info.get('longitude', 'N/A') if location_info else 'N/A'
            
            gateway_info = {
                'serial': gateway.get('serial', ''),
                'model': gateway.get('model', ''),
                'health_status': health_status,
                'last_connected_time': last_connected_formatted,
                'hours_since_connected': hours_inactive,
                'is_inactive': is_inactive,
                'vin': gateway.get('asset', {}).get('externalIds', {}).get('samsara.vin', ''),
                'asset_id': asset_id,
                'latitude': latitude,
                'longitude': longitude,
                'accuracy_meters': location_info.get('accuracy_meters', 'N/A') if location_info else 'N/A',
                'heading': location_info.get('heading', 'N/A') if location_info else 'N/A',
                'last_location_time': datetime.fromisoformat(location_info.get('location_time', '').replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S UTC') if location_info and location_info.get('location_time') else 'N/A',
                'location_name': 'N/A'  # Initialize location_name with default value
            }
            gateway_data.append(gateway_info)
        
        # Convert to DataFrame
        df = pd.DataFrame(gateway_data)
        if df.empty:
            return df
            
        # Second pass: Concurrently get location names for valid coordinates
        valid_coords = df[
            (df['latitude'] != 'N/A') & 
            (df['longitude'] != 'N/A')
        ][['latitude', 'longitude']].values
        
        if len(valid_coords) > 0:
            print(f"\nReverse geocoding {len(valid_coords)} locations...")
            
            # Create geocoding service with rate limiter
            geocoding_service = GeocodingService()
            
            # Use fewer workers and add delay between batches to respect rate limits
            max_workers = min(MAX_GEOCODING_WORKERS, len(valid_coords))
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                location_futures = []
                
                # Submit requests in batches
                batch_size = GEOCODING_BATCH_SIZE
                for i in range(0, len(valid_coords), batch_size):
                    batch = valid_coords[i:i + batch_size]
                    for lat, lon in batch:
                        location_futures.append(
                            executor.submit(geocoding_service.get_location_name, lat, lon)
                        )
                    # Add delay between batches
                    if i + batch_size < len(valid_coords):
                        time.sleep(2)  # Increased delay between batches
                
                location_names = []
                completed = 0
                total = len(valid_coords)
                
                for future in as_completed(location_futures):
                    completed += 1
                    if completed % 10 == 0:  # Update progress every 10 locations
                        print(f"Geocoding progress: {completed}/{total}", end='\r')
                    location_names.append(future.result())
                
                print()  # New line after progress
                
                # Update location names in DataFrame where coordinates are valid
                df.loc[
                    (df['latitude'] != 'N/A') & 
                    (df['longitude'] != 'N/A'),
                    'location_name'
                ] = location_names
        
        if not df.empty:
            df = df.sort_values('hours_since_connected', ascending=False)
            
            # Format hours to be more readable
            df['days_since_connected'] = df['hours_since_connected'] / 24
            df['days_since_connected'] = df['days_since_connected'].apply(
                lambda x: f"{x:.1f}" if x != float('inf') else 'Never'
            )
            
        return df

    @staticmethod
    def save_results_to_csv(df, filename_prefix='inactive_gateways'):
        """Save results to CSV with timestamp"""
        if df is None or df.empty:
            return
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = RESULTS_DIR / f'{filename_prefix}_{timestamp}.csv'
        df.to_csv(filename, index=False)
        print(f"\nResults saved to: {filename}")


def get_inactive_gateways(api_token, days_threshold=3):
    """Main function to get inactive gateways with their location data
    
    Args:
        api_token: Samsara API token
        days_threshold: Number of days of inactivity to consider a gateway inactive
        
    Returns:
        DataFrame with gateway data or None if no data available
    """
    CacheManager.ensure_directories()
    
    # Initialize API client
    client = SamsaraAPIClient(api_token)
    
    # Verify API access
    success, message = client.verify_api_access()
    if not success:
        print(f"API access verification failed: {message}")
        print("Continuing with the script, but there might be issues with API access.")
    else:
        print(message)
    
    # First, get all gateways
    print("Fetching gateway data...")
    gateways = client.get_gateways()
    if not gateways:
        return None
    
    # Update the inactivity threshold based on the days parameter
    for gateway in gateways:
        connection_status = gateway.get('connectionStatus', {})
        last_connected_str = connection_status.get('lastConnected')
        
        if last_connected_str:
            last_connected = datetime.fromisoformat(last_connected_str.replace('Z', '+00:00'))
            time_diff = datetime.now(timezone.utc) - last_connected
            gateway['is_inactive'] = time_diff > timedelta(days=days_threshold)
        else:
            gateway['is_inactive'] = True if connection_status.get('healthStatus') != 'Connected' else False
        
    # Collect asset IDs from gateways
    asset_ids = [gateway['asset']['id'] for gateway in gateways if gateway.get('asset', {}).get('id')]
    
    # Then get location data for the assets
    print(f"Fetching location data for {len(asset_ids)} assets...")
    locations = client.get_location_data(asset_ids) if asset_ids else {}
    
    # Process the combined data
    return GatewayProcessor.process_gateway_data(gateways, locations)


def main():
    """Entry point for the script"""
    # Load environment variables from .env file
    load_dotenv()
    
    parser = argparse.ArgumentParser(description='Fetch inactive Samsara gateways and their locations')
    parser.add_argument('--token', '-t', help='Samsara API token')
    parser.add_argument('--filename', '-f', default='inactive_gateways', help='Prefix for output filename')
    parser.add_argument('--days', '-d', type=int, default=3, help='Number of days of inactivity to filter by (default: 3)')
    parser.add_argument('--clear-cache', '-c', action='store_true', help='Clear cached data before running')
    args = parser.parse_args()
    
    # Get API token from args or environment
    api_token = args.token or os.environ.get('SAMSARA_API_TOKEN')
    
    if not api_token:
        print("Error: Samsara API token not provided. Please use --token argument or set SAMSARA_API_TOKEN environment variable.")
        return
    
    # Clear cache if requested
    if args.clear_cache:
        print("Clearing cached data...")
        for cache_file in CACHE_DIR.glob('*.json'):
            try:
                os.remove(cache_file)
                print(f"Deleted {cache_file}")
            except Exception as e:
                print(f"Error deleting {cache_file}: {e}")
    
    # Get inactive gateways
    df = get_inactive_gateways(api_token, args.days)
    
    # Display only inactive gateways with relevant columns
    if df is not None and not df.empty:
        inactive_df = df[df['is_inactive']][['serial', 'model', 'health_status', 'last_connected_time', 
                                             'days_since_connected', 'vin', 'asset_id', 'latitude', 'longitude', 
                                             'location_name', 'accuracy_meters', 'heading', 'last_location_time']]
        
        if inactive_df.empty:
            print(f"\nNo gateways found that have been inactive for more than {args.days} days.")
        else:
            print(f"\nInactive Gateways (>{args.days} days or not connected):")
            print(inactive_df.to_string(index=False))
            
            # Save results to CSV
            GatewayProcessor.save_results_to_csv(inactive_df, args.filename)
    else:
        print("No gateway data available")


if __name__ == "__main__":
    main()