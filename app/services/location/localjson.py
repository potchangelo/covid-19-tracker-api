"""app.services.location.localjson.py"""
import csv
import logging
import os
from datetime import datetime
from pprint import pformat as pf

from asyncache import cached
from cachetools import TTLCache

import app.io
from ...caches import check_cache, load_cache
from ...coordinates import Coordinates
from ...location import TimelinedLocation
from ...models import Timeline
from ...utils import countries
from ...utils import date as date_util
from ...utils import httputils
from . import LocationService

LOGGER = logging.getLogger("services.location.localjson")
PID = os.getpid()

class LocalJsonLocationService(LocationService):
    """
    Service for retrieving locations from local JSON file.
    """

    async def get_all(self):
        # Get the locations.
        locations = await get_locations()
        return locations

    async def get(self, loc_id):  # pylint: disable=arguments-differ
        # Get location at the index equal to provided id.
        locations = await self.get_all()

        return locations[loc_id]


# ---------------------------------------------------------------


LOCATIONS_PATH = "locations.json"


@cached(cache=TTLCache(maxsize=1, ttl=1800))
async def get_locations():
    """
    Retrieves the locations from the categories. The locations are cached for 1 hour.

    :returns: The locations.
    :rtype: List[Location]
    """

    data_id = "localjson.locations"
    LOGGER.info(f"pid:{PID}: {data_id} Requesting data...")

    # Transform JSON to list of object
    raw_locations: list[dict] = app.io.load(LOCATIONS_PATH)
    locations: list[TimelinedLocation] = []

    for _, raw_location in enumerate(raw_locations):
        coordinates = raw_location.get("coordinates", {})
        timelines = raw_location.get("timelines", {})
        confirmed_timelines = timelines.get("confirmed", {}).get("timeline", {})
        deaths_timelines = timelines.get("deaths", {}).get("timeline", {})
        recovered_timelines = timelines.get("recovered", {}).get("timeline", {})

        locations.append(
            TimelinedLocation(
                id=raw_location.get("id"),
                country=raw_location.get("country"),
                province=raw_location.get("province"),
                coordinates=Coordinates(
                    latitude=coordinates.get("latitude"), 
                    longitude=coordinates.get("longitude")
                ),
                last_updated=datetime.utcnow().isoformat() + "Z",
                timelines={
                    "confirmed": Timeline(
                        timeline={
                            date: amount
                            for date, amount in confirmed_timelines.items()
                        }
                    ),
                    "deaths": Timeline(
                        timeline={
                            date: amount
                            for date, amount in deaths_timelines.items()
                        }
                    ),
                    "recovered": Timeline(
                        timeline={
                            date: amount
                            for date, amount in recovered_timelines.items()
                        }
                    ),
                },
            )
        )        

    LOGGER.info(f"{data_id} Data normalized")

    return locations
