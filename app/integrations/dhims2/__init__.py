"""
DHIMS2 Integration Module

This module provides integration with Ghana's DHIMS2 (DHIS2-based) health reporting system.

Components:
- client: DHIS2 API client with retry logic
- services: Business logic for submission, validation, approval
- validators: Data quality validation
- providers: Data extraction from LHIMS
- schemas: Pydantic schemas for API
"""

__version__ = "1.0.0"
