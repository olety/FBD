from geopy.geocoders import Nominatim

LAT_PER_100M = 0.001622 / 1.8
LONG_PER_100M = 0.005083 / 5.5


def lat_from_met(met):
    return LAT_PER_100M * float(met) / 100.0


def lon_from_met(met):
    return LONG_PER_100M * float(met) / 100


def get_coords(city):
    loc = Nominatim().geocode(city)
    return loc.latitude, loc.longitude
