# STL imports
import datetime

# Package imports
import geocoder

# Project imports
import storage

LAT_PER_100M = 0.001622 / 1.8
LONG_PER_100M = 0.005083 / 5.5


def lat_from_met(met):
    return LAT_PER_100M * float(met) / 100.0


def lon_from_met(met):
    return LONG_PER_100M * float(met) / 100


def get_coords(city):
    # with open('google_api.json', 'r') as f:
    #     key = json.load(f)['key']
    return geocoder.google(city).latlng


def default_json_serializer(obj):
    """JSON serializer for objects not supported by the default json package"""
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    if isinstance(obj, storage.Topic):
        return obj.to_dict()
    raise TypeError('{} type could not be serialized.'
                    .format(type(obj)))
