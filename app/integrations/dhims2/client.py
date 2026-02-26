"""
DHIS2 API Client

A robust HTTP client for interacting with DHIS2/DHIMS2 APIs.
Supports retry with exponential backoff, error handling, and idempotent operations.
"""
import logging
import time
import hashlib
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)


class DHIS2Exception(Exception):
    """Base exception for DHIS2 client errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_data = response_data


class DHIS2ConnectionError(DHIS2Exception):
    """Raised when connection to DHIS2 fails."""
    pass


class DHIS2AuthenticationError(DHIS2Exception):
    """Raised when authentication fails."""
    pass


class DHIS2ValidationError(DHIS2Exception):
    """Raised when data validation fails."""
    pass


class DHIS2RetryError(DHIS2Exception):
    """Raised when all retry attempts are exhausted."""
    pass


class Dhis2Client:
    """
    Robust HTTP client for DHIS2 API.
    
    Features:
    - Basic authentication
    - Exponential backoff retry
    - Request/response logging (redacted)
    - Timeout handling
    - TLS verification control
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: Optional[int] = None,
        verify_tls: Optional[bool] = None,
        max_retries: Optional[int] = None,
        backoff_factor: Optional[int] = None
    ):
        """
        Initialize DHIS2 client.
        
        Args:
            base_url: DHIS2 base URL (defaults to settings.DHIMS2_BASE_URL)
            username: API username (defaults to settings.DHIMS2_USERNAME)
            password: API password (defaults to settings.DHIMS2_PASSWORD)
            timeout: Request timeout in seconds (defaults to settings.DHIMS2_TIMEOUT_SECONDS)
            verify_tls: Whether to verify TLS certificates (defaults to settings.DHIMS2_VERIFY_TLS)
            max_retries: Maximum retry attempts (defaults to settings.DHIMS2_MAX_RETRIES)
            backoff_factor: Exponential backoff factor (defaults to settings.DHIMS2_BACKOFF_SECONDS)
        """
        self.base_url = base_url or settings.DHIMS2_BASE_URL
        self.username = username or settings.DHIMS2_USERNAME
        self.password = password or settings.DHIMS2_PASSWORD
        self.timeout = timeout or settings.DHIMS2_TIMEOUT_SECONDS
        self.verify_tls = verify_tls if verify_tls is not None else settings.DHIMS2_VERIFY_TLS
        self.max_retries = max_retries or settings.DHIMS2_MAX_RETRIES
        self.backoff_factor = backoff_factor or settings.DHIMS2_BACKOFF_SECONDS
        
        # Create session with retry strategy
        self.session = self._create_session()
        
        # Redacted credentials for logging
        self._redacted_auth = "****" if self.password else None
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry strategy."""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=self.backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"],
            raise_on_status=False
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _get_auth(self) -> tuple:
        """Get authentication tuple."""
        return (self.username, self._redacted_auth)
    
    def _log_request(self, method: str, url: str, **kwargs):
        """Log request details (redacted)."""
        # Redact password from logs
        safe_kwargs = kwargs.copy()
        if 'auth' in safe_kwargs:
            safe_kwargs['auth'] = (self.username, '****')
        if 'json' in safe_kwargs and safe_kwargs.get('json'):
            # Don't log sensitive data
            safe_data = safe_kwargs['json'].copy()
            if 'password' in safe_data:
                safe_data['password'] = '****'
            safe_kwargs['json'] = safe_data
        
        logger.debug(f"DHIS2 Request: {method} {url} {safe_kwargs}")
    
    def _log_response(self, status_code: int, response_text: str, elapsed: float):
        """Log response details."""
        # Don't log full response body - just summary
        logger.debug(f"DHIS2 Response: status={status_code}, elapsed={elapsed:.2f}s")
    
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Handle HTTP response and raise appropriate exceptions.
        
        Args:
            response: requests.Response object
            
        Returns:
            Parsed JSON response
            
        Raises:
            DHIS2AuthenticationError: For 401/403 responses
            DHIS2ValidationError: For 400 responses with validation errors
            DHIS2Exception: For other error responses
        """
        try:
            data = response.json() if response.content else {}
        except json.JSONDecodeError:
            data = {"raw_response": response.text[:500]}
        
        if response.status_code == 401:
            raise DHIS2AuthenticationError(
                "Authentication failed. Please check credentials.",
                status_code=401,
                response_data=data
            )
        
        if response.status_code == 403:
            raise DHIS2AuthenticationError(
                "Access forbidden. Insufficient permissions.",
                status_code=403,
                response_data=data
            )
        
        if response.status_code == 400:
            # Check for validation errors in DHIS2 response
            description = data.get('description', '')
            if 'validation' in description.lower():
                raise DHIS2ValidationError(
                    f"Validation error: {description}",
                    status_code=400,
                    response_data=data
                )
            raise DHIS2Exception(
                f"Bad request: {description}",
                status_code=400,
                response_data=data
            )
        
        if response.status_code >= 500:
            raise DHIS2Exception(
                f"DHIS2 server error: {response.status_code}",
                status_code=response.status_code,
                response_data=data
            )
        
        if response.status_code == 409:
            # Conflict - often indicates duplicate data
            raise DHIS2Exception(
                f"Data conflict: {data.get('description', 'Unknown conflict')}",
                status_code=409,
                response_data=data
            )
        
        return data
    
    def test_connection(self) -> bool:
        """
        Test connectivity to DHIS2 API.
        
        Returns:
            True if connection successful
            
        Raises:
            DHIS2ConnectionError: If connection fails
        """
        try:
            url = f"{self.base_url}/api/me"
            response = self.session.get(
                url,
                auth=(self.username, self.password),
                timeout=self.timeout,
                verify=self.verify_tls
            )
            self._handle_response(response)
            logger.info(f"DHIS2 connection test successful to {self.base_url}")
            return True
        except requests.exceptions.Timeout:
            raise DHIS2ConnectionError(f"Connection timeout to {self.base_url}")
        except requests.exceptions.ConnectionError as e:
            raise DHIS2ConnectionError(f"Failed to connect to {self.base_url}: {str(e)}")
        except DHIS2Exception:
            raise
        except Exception as e:
            raise DHIS2ConnectionError(f"Unexpected error testing connection: {str(e)}")
    
    def get_user_info(self) -> Dict[str, Any]:
        """
        Get current user information.
        
        Returns:
            User data from DHIS2
        """
        url = f"{self.base_url}/api/me"
        response = self.session.get(
            url,
            auth=(self.username, self.password),
            timeout=self.timeout,
            verify=self.verify_tls
        )
        return self._handle_response(response)
    
    def get_organisation_units(
        self,
        filters: Optional[List[str]] = None,
        fields: Optional[List[str]] = None,
        page_size: int = 100,
        page: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Get organisation units from DHIS2.
        
        Args:
            filters: List of filter strings (e.g., ["level:eq:2"])
            fields: List of fields to return (e.g., ["id", "name", "level"])
            page_size: Number of results per page
            page: Page number
            
        Returns:
            List of organisation units
        """
        url = f"{self.base_url}/api/organisationUnits"
        
        params = {
            "page": page,
            "pageSize": page_size
        }
        
        if filters:
            params["filter"] = filters
        if fields:
            params["fields"] = ",".join(fields)
        
        response = self.session.get(
            url,
            auth=(self.username, self.password),
            params=params,
            timeout=self.timeout,
            verify=self.verify_tls
        )
        
        data = self._handle_response(response)
        return data.get("organisationUnits", [])
    
    def get_data_elements(
        self,
        filters: Optional[List[str]] = None,
        fields: Optional[List[str]] = None,
        page_size: int = 100,
        page: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Get data elements from DHIS2.
        
        Args:
            filters: List of filter strings
            fields: List of fields to return
            page_size: Number of results per page
            page: Page number
            
        Returns:
            List of data elements
        """
        url = f"{self.base_url}/api/dataElements"
        
        params = {
            "page": page,
            "pageSize": page_size
        }
        
        if filters:
            params["filter"] = filters
        if fields:
            params["fields"] = ",".join(fields)
        
        response = self.session.get(
            url,
            auth=(self.username, self.password),
            params=params,
            timeout=self.timeout,
            verify=self.verify_tls
        )
        
        data = self._handle_response(response)
        return data.get("dataElements", [])
    
    def get_data_sets(
        self,
        filters: Optional[List[str]] = None,
        fields: Optional[List[str]] = None,
        page_size: int = 100,
        page: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Get data sets from DHIS2.
        
        Args:
            filters: List of filter strings
            fields: List of fields to return
            page_size: Number of results per page
            page: Page number
            
        Returns:
            List of data sets
        """
        url = f"{self.base_url}/api/dataSets"
        
        params = {
            "page": page,
            "pageSize": page_size
        }
        
        if filters:
            params["filter"] = filters
        if fields:
            params["fields"] = ",".join(fields)
        
        response = self.session.get(
            url,
            auth=(self.username, self.password),
            params=params,
            timeout=self.timeout,
            verify=self.verify_tls
        )
        
        data = self._handle_response(response)
        return data.get("dataSets", [])
    
    def get_category_option_combos(
        self,
        filters: Optional[List[str]] = None,
        fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get category option combinations from DHIS2.
        
        Args:
            filters: List of filter strings
            fields: List of fields to return
            
        Returns:
            List of category option combos
        """
        url = f"{self.base_url}/api/categoryOptionCombos"
        
        params = {}
        
        if filters:
            params["filter"] = filters
        if fields:
            params["fields"] = ",".join(fields)
        
        response = self.session.get(
            url,
            auth=(self.username, self.password),
            params=params,
            timeout=self.timeout,
            verify=self.verify_tls
        )
        
        data = self._handle_response(response)
        return data.get("categoryOptionCombos", [])
    
    def submit_data_values(
        self,
        data_set: str,
        org_unit: str,
        period: str,
        data_values: List[Dict[str, Any]],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Submit data values to DHIS2.
        
        Args:
            data_set: Data set UID
            org_unit: Organisation unit UID
            period: Period string (e.g., "2026-01")
            data_values: List of data value objects
            dry_run: If True, validate but don't save
            
        Returns:
            DHIS2 import response
        """
        url = f"{self.base_url}/api/dataValueSets"
        
        payload = {
            "dataSet": data_set,
            "orgUnit": org_unit,
            "period": period,
            "dataValues": data_values
        }
        
        params = {}
        if dry_run:
            params["dryRun"] = "true"
        
        self._log_request("POST", url, json=payload, params=params)
        
        start_time = time.time()
        
        try:
            response = self.session.post(
                url,
                auth=(self.username, self.password),
                json=payload,
                params=params,
                timeout=self.timeout,
                verify=self.verify_tls
            )
            
            elapsed = time.time() - start_time
            self._log_response(response.status_code, response.text, elapsed)
            
            result = self._handle_response(response)
            
            logger.info(
                f"DHIS2 submission successful: orgUnit={org_unit}, period={period}, "
                f"dataset={data_set}, values={len(data_values)}, elapsed={elapsed:.2f}s"
            )
            
            return result
            
        except requests.exceptions.Timeout:
            elapsed = time.time() - start_time
            logger.error(
                f"DHIS2 submission timeout: orgUnit={org_unit}, period={period}, "
                f"elapsed={elapsed:.2f}s"
            )
            raise DHIS2ConnectionError(
                f"Request timeout after {elapsed:.2f}s",
                status_code=408
            )
        except requests.exceptions.ConnectionError as e:
            elapsed = time.time() - start_time
            logger.error(
                f"DHIS2 connection error: orgUnit={org_unit}, period={period}, "
                f"error={str(e)}, elapsed={elapsed:.2f}s"
            )
            raise DHIS2ConnectionError(f"Connection failed: {str(e)}")
    
    def get_existing_data_values(
        self,
        data_set: str,
        org_unit: str,
        period: str
    ) -> List[Dict[str, Any]]:
        """
        Get existing data values for a given data set, org unit, and period.
        
        Args:
            data_set: Data set UID
            org_unit: Organisation unit UID
            period: Period string
            
        Returns:
            List of existing data values
        """
        url = f"{self.base_url}/api/dataValueSets"
        
        params = {
            "dataSet": data_set,
            "orgUnit": org_unit,
            "period": period
        }
        
        response = self.session.get(
            url,
            auth=(self.username, self.password),
            params=params,
            timeout=self.timeout,
            verify=self.verify_tls
        )
        
        if response.status_code == 404:
            return []
        
        data = self._handle_response(response)
        return data.get("dataValues", [])


def compute_payload_hash(data: Dict[str, Any]) -> str:
    """
    Compute SHA-256 hash of payload for idempotency.
    
    Args:
        data: Data to hash
        
    Returns:
        Hex string of hash
    """
    # Sort keys for consistent hashing
    json_str = json.dumps(data, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(json_str.encode()).hexdigest()
