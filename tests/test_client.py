"""Tests for the SamsaraClient class."""

import pytest
from unittest.mock import Mock, patch
from samsara_tools.core.client import SamsaraClient


class TestSamsaraClient:
    """Test cases for SamsaraClient."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.api_token = "test_token"
        self.client = SamsaraClient(self.api_token)
    
    def test_init(self):
        """Test client initialization."""
        assert self.client.api_token == self.api_token
        assert self.client.base_url == "https://api.samsara.com"
        assert "Bearer test_token" in self.client.headers["Authorization"]
    
    def test_init_with_custom_base_url(self):
        """Test client initialization with custom base URL."""
        custom_url = "https://custom.api.com"
        client = SamsaraClient(self.api_token, base_url=custom_url)
        assert client.base_url == custom_url
    
    @patch('samsara_tools.core.client.requests.get')
    def test_verify_api_access_success(self, mock_get):
        """Test successful API access verification."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response
        
        success, message = self.client.verify_api_access()
        
        assert success is True
        assert "successfully" in message
        mock_get.assert_called_once()
    
    @patch('samsara_tools.core.client.requests.get')
    def test_verify_api_access_failure(self, mock_get):
        """Test failed API access verification."""
        mock_get.side_effect = Exception("API Error")
        
        success, message = self.client.verify_api_access()
        
        assert success is False
        assert "failed" in message
    
    @patch('samsara_tools.core.client.requests.get')
    def test_get_gateways_success(self, mock_get):
        """Test successful gateway retrieval."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"data": [{"serial": "TEST123"}]}
        mock_get.return_value = mock_response
        
        gateways = self.client.get_gateways(use_cache=False)
        
        assert len(gateways) == 1
        assert gateways[0]["serial"] == "TEST123"
    
    @patch('samsara_tools.core.client.requests.get')
    def test_get_gateways_failure(self, mock_get):
        """Test failed gateway retrieval."""
        mock_get.side_effect = Exception("API Error")
        
        gateways = self.client.get_gateways(use_cache=False)
        
        assert gateways == []
    
    def test_find_tag_by_name(self):
        """Test finding tag by name."""
        with patch.object(self.client, 'get_all_tags') as mock_get_tags:
            mock_get_tags.return_value = [
                {"name": "Tag1", "id": "1"},
                {"name": "Tag2", "id": "2"}
            ]
            
            result = self.client.find_tag_by_name("Tag1")
            assert result["id"] == "1"
            
            result = self.client.find_tag_by_name("NonExistent")
            assert result is None


if __name__ == "__main__":
    pytest.main([__file__]) 