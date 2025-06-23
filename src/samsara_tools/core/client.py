"""Base Samsara API client with rate limiting and caching."""

import requests
import time
import random
import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RateLimiter:
    """Handles API rate limiting with exponential backoff and retry logic."""
    
    def __init__(self, base_delay=1, max_delay=60, max_retries=5):
        """Initialize rate limiter with configurable parameters.
        
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
        """Wait for minimum interval between requests."""
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.min_interval:
            sleep_time = self.min_interval - elapsed
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def execute_with_retry(self, func, *args, **kwargs):
        """Execute a function with retry logic and exponential backoff.
        
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
                self.wait()
                return func(*args, **kwargs)
                
            except requests.exceptions.HTTPError as e:
                last_exception = e
                
                if e.response.status_code == 429:
                    retries += 1
                    if retries > self.max_retries:
                        break
                        
                    delay = min(self.max_delay, self.base_delay * (2 ** (retries - 1)))
                    jitter = random.uniform(0, 0.1 * delay)
                    delay += jitter
                    
                    logger.warning(f"Rate limit exceeded. Retrying in {delay:.2f} seconds... (Attempt {retries}/{self.max_retries})")
                    time.sleep(delay)
                else:
                    raise
            except Exception as e:
                last_exception = e
                raise
                
        if last_exception:
            logger.error(f"Max retries exceeded. Last error: {last_exception}")
            raise last_exception


class CacheManager:
    """Handles caching operations for API data."""
    
    def __init__(self, cache_dir: Path = Path('data/cache'), cache_duration: timedelta = timedelta(hours=1)):
        self.cache_dir = cache_dir
        self.cache_duration = cache_duration
        self.ensure_directories()

    def ensure_directories(self):
        """Ensure cache directory exists."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def load_cache(self, cache_file: Path) -> Optional[Any]:
        """Load data from cache if it exists and is fresh."""
        if not cache_file.exists():
            return None
            
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
                
            cache_time = datetime.fromisoformat(cache_data['timestamp'])
            if datetime.now(timezone.utc) - cache_time < self.cache_duration:
                return cache_data['data']
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Cache error: {e}")
        return None

    def save_cache(self, cache_file: Path, data: Any):
        """Save data to cache with timestamp."""
        cache_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'data': data
        }
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)


class SamsaraClient:
    """Base client for interacting with the Samsara API."""
    
    def __init__(self, api_token: str, base_url: str = "https://api.samsara.com", 
                 cache_dir: Path = Path('data/cache')):
        """Initialize with API token and configuration.
        
        Args:
            api_token: Samsara API token
            base_url: Base URL for Samsara API
            cache_dir: Directory for caching API responses
        """
        self.api_token = api_token
        self.base_url = base_url.rstrip('/')
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        self.rate_limiter = RateLimiter()
        self.cache_manager = CacheManager(cache_dir)
        
    def verify_api_access(self) -> Tuple[bool, str]:
        """Verify API access and token validity."""
        try:
            url = f"{self.base_url}/fleet/drivers"
            params = {"limit": 1}
            
            def make_request():
                response = requests.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                return response.json()
                
            self.rate_limiter.execute_with_retry(make_request)
            return True, "API access verified successfully"
        except requests.exceptions.RequestException as e:
            return False, f"API access verification failed: {e}"

    def get_gateways(self, use_cache: bool = True) -> List[Dict]:
        """Fetch all gateways from the Samsara API.
        
        Args:
            use_cache: Whether to use cached data if available
            
        Returns:
            List of gateway dictionaries
        """
        cache_file = self.cache_manager.cache_dir / 'gateways.json'
        
        if use_cache:
            cached_data = self.cache_manager.load_cache(cache_file)
            if cached_data:
                logger.info("Using cached gateway data...")
                return cached_data

        url = f"{self.base_url}/gateways"
        
        try:
            def make_request():
                response = requests.get(url, headers=self.headers)
                response.raise_for_status()
                return response.json().get('data', [])
                
            data = self.rate_limiter.execute_with_retry(make_request)
            
            if use_cache:
                self.cache_manager.save_cache(cache_file, data)
            
            logger.info(f"Fetched {len(data)} gateways from API")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching gateway data: {e}")
            return []

    def get_all_tags(self) -> List[Dict]:
        """Retrieve all tags from Samsara API with pagination support."""
        url = f"{self.base_url}/tags"
        all_tags = []
        
        try:
            while url:
                def make_request():
                    response = requests.get(url, headers=self.headers)
                    response.raise_for_status()
                    return response.json()
                
                data = self.rate_limiter.execute_with_retry(make_request)
                all_tags.extend(data['data'])
                
                # Check for pagination
                pagination = data.get('pagination', {})
                if pagination.get('hasNextPage', False):
                    cursor = pagination.get('endCursor', '')
                    url = f"{self.base_url}/tags?after={cursor}"
                else:
                    url = None
                    
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching tags: {e}")
            return []
        
        logger.info(f"Fetched {len(all_tags)} tags from API")
        return all_tags

    def find_tag_by_name(self, tag_name: str) -> Optional[Dict]:
        """Find a tag by name."""
        tags = self.get_all_tags()
        return next((tag for tag in tags if tag['name'] == tag_name), None)

    def get_tag_details(self, tag_id: str) -> Optional[Dict]:
        """Get detailed information for a specific tag."""
        url = f"{self.base_url}/tags/{tag_id}"
        
        try:
            def make_request():
                response = requests.get(url, headers=self.headers)
                response.raise_for_status()
                return response.json()['data']
            
            return self.rate_limiter.execute_with_retry(make_request)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching tag details: {e}")
            return None

    def get_address_details(self, address_id: str) -> Optional[Dict]:
        """Get detailed information for a specific address including geofence."""
        url = f"{self.base_url}/addresses/{address_id}"
        
        try:
            def make_request():
                response = requests.get(url, headers=self.headers)
                response.raise_for_status()
                return response.json()['data']
            
            return self.rate_limiter.execute_with_retry(make_request)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching address details for {address_id}: {e}")
            return None 