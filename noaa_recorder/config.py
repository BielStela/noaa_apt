from orbit_predictor.locations import Location

BCN = Location(
    name="Barcelona",
    latitude_deg=41.384740,
    longitude_deg=2.177813,
    elevation_m=0,  # estimation
)
DOWNLINK_FREQS = {"NOAA 15": 137.62, "NOAA 18": 137.9125, "NOAA 19": 137.1}
NOAA_IDS = ["NOAA 15", "NOAA 18", "NOAA 19"]
MAX_ELEV_GT = 20  # min elevation for the sat flyby trigger recording
