"""Test data fixtures for Canary MCP Server.

This module contains sample data structures used across unit and integration tests.
Data is organized by MCP tool and includes realistic Maceira plant examples.
"""

# Sample Namespaces (Story 1.3 - list_namespaces)
SAMPLE_NAMESPACES = [
    "Maceira",
    "Maceira.Cement",
    "Maceira.Cement.Kiln6",
]

# Sample Tags (Story 1.4 - search_tags)
SAMPLE_TAGS = [
    {
        "name": "Temperature.Outlet",
        "path": "Maceira.Cement.Kiln6.Temperature.Outlet",
        "dataType": "float",
        "description": "Kiln outlet temperature sensor",
    },
    {
        "name": "Temperature.Inlet",
        "path": "Maceira.Cement.Kiln6.Temperature.Inlet",
        "dataType": "float",
        "description": "Kiln inlet temperature sensor",
    },
    {
        "name": "Pressure.Main",
        "path": "Maceira.Cement.Kiln6.Pressure.Main",
        "dataType": "float",
        "description": "Main pressure sensor",
    },
    {
        "name": "Flow.FuelGas",
        "path": "Maceira.Cement.Kiln6.Flow.FuelGas",
        "dataType": "float",
        "description": "Fuel gas flow meter",
    },
    {
        "name": "Speed.RotaryKiln",
        "path": "Maceira.Cement.Kiln6.Speed.RotaryKiln",
        "dataType": "float",
        "description": "Rotary kiln rotation speed",
    },
]

# Sample Tag Metadata (Story 1.5 - get_tag_metadata)
SAMPLE_TAG_METADATA = {
    "Maceira.Cement.Kiln6.Temperature.Outlet": {
        "name": "Temperature.Outlet",
        "path": "Maceira.Cement.Kiln6.Temperature.Outlet",
        "dataType": "float",
        "description": "Kiln outlet temperature",
        "units": "celsius",
        "minValue": 0.0,
        "maxValue": 1500.0,
        "updateRate": 1000,
    },
    "Maceira.Cement.Kiln6.Pressure.Main": {
        "name": "Pressure.Main",
        "path": "Maceira.Cement.Kiln6.Pressure.Main",
        "dataType": "float",
        "description": "Main pressure reading",
        "units": "bar",
        "minValue": 0.0,
        "maxValue": 10.0,
        "updateRate": 500,
    },
    "Maceira.Cement.Kiln6.Flow.FuelGas": {
        "name": "Flow.FuelGas",
        "path": "Maceira.Cement.Kiln6.Flow.FuelGas",
        "dataType": "float",
        "description": "Fuel gas flow rate",
        "units": "m3/h",
        "minValue": 0.0,
        "maxValue": 5000.0,
        "updateRate": 1000,
    },
}

# Sample Timeseries Data (Story 1.6 - read_timeseries)
SAMPLE_TIMESERIES_DATA = [
    {
        "timestamp": "2025-10-31T10:00:00Z",
        "value": 850.5,
        "quality": "Good",
        "tagName": "Maceira.Cement.Kiln6.Temperature.Outlet",
    },
    {
        "timestamp": "2025-10-31T10:01:00Z",
        "value": 851.2,
        "quality": "Good",
        "tagName": "Maceira.Cement.Kiln6.Temperature.Outlet",
    },
    {
        "timestamp": "2025-10-31T10:02:00Z",
        "value": 852.0,
        "quality": "Good",
        "tagName": "Maceira.Cement.Kiln6.Temperature.Outlet",
    },
    {
        "timestamp": "2025-10-31T10:03:00Z",
        "value": 853.1,
        "quality": "Good",
        "tagName": "Maceira.Cement.Kiln6.Temperature.Outlet",
    },
    {
        "timestamp": "2025-10-31T10:04:00Z",
        "value": 854.5,
        "quality": "Good",
        "tagName": "Maceira.Cement.Kiln6.Temperature.Outlet",
    },
]

# Sample Timeseries Data with Quality Issues
SAMPLE_TIMESERIES_WITH_QUALITY_ISSUES = [
    {
        "timestamp": "2025-10-31T10:00:00Z",
        "value": 850.5,
        "quality": "Good",
        "tagName": "Maceira.Cement.Kiln6.Temperature.Outlet",
    },
    {
        "timestamp": "2025-10-31T10:01:00Z",
        "value": 851.2,
        "quality": "Bad",
        "tagName": "Maceira.Cement.Kiln6.Temperature.Outlet",
    },
    {
        "timestamp": "2025-10-31T10:02:00Z",
        "value": 0.0,
        "quality": "Uncertain",
        "tagName": "Maceira.Cement.Kiln6.Temperature.Outlet",
    },
]

# Sample Server Info (Story 1.7 - get_server_info)
SAMPLE_SERVER_INFO = {
    "canary_server_url": "https://scunscanary.secil.pt:55236",
    "api_version": "v2",
    "connected": True,
    "supported_timezones": [
        "UTC",
        "America/New_York",
        "Europe/London",
        "Asia/Tokyo",
        "America/Los_Angeles",
    ],
    "total_timezones": 5,
    "supported_aggregates": [
        "TimeAverage2",
        "TimeSum",
        "Min",
        "Max",
        "Count",
        "StdDev",
        "Range",
    ],
    "total_aggregates": 7,
}

SAMPLE_MCP_INFO = {
    "server_name": "Canary MCP Server",
    "version": "1.0.0",
    "configuration": {
        "saf_base_url": "https://scunscanary.secil.pt:55236/api/v2",
        "views_base_url": "https://scunscanary.secil.pt:55236",
    },
}

# Alternative Response Formats (Read API v2 supports both dict and list)
# Some endpoints return lists directly instead of wrapped in dicts
SAMPLE_TIMEZONES_LIST = [
    "UTC",
    "America/New_York",
    "Europe/London",
    "Asia/Tokyo",
]

SAMPLE_AGGREGATES_LIST = [
    "TimeAverage2",
    "Min",
    "Max",
    "Count",
]
