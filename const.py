"""Constants for the Thermotec AeroFlow integration."""

from datetime import timedelta

DOMAIN = "thermotec_aeroflow"
MANUFACTURER = "Thermotec AG"

# Update intervals for different coordinators
UPDATE_INTERVAL_ZONES = timedelta(seconds=30)
UPDATE_INTERVAL_DEVICE = timedelta(seconds=35)

# Availability and retry configuration
MAX_CONSECUTIVE_FAILURES = 3
MAX_RETRY_BACKOFF = timedelta(minutes=2)
MIN_RETRY_BACKOFF = timedelta(seconds=5)

# Request timeout
REQUEST_TIMEOUT = 20
