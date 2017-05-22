#!/usr/local/bin/python3
import sys
import time
import json
import requests
import logging
import geocoder
# import multiprocessing
from backend.storage import Storage


class Gatherer:
    LAT_PER_100M = 0.001622 / 1.8
    LONG_PER_100M = 0.005083 / 5.5

    def __init__(self, client_id, client_secret, storage=None):
        logging.debug('Gatherer: Started initialization')
        self.client_id = client_id
        self.client_secret = client_secret
        logging.debug('Gatherer: Getting the token')
        token_params = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'client_credentials'
        }
        self.token = requests.get(
            'https://graph.facebook.com/v2.8/oauth/access_token?',
            params=token_params).json()['access_token']
        logging.debug('Gatherer: Initialized')
        self.storage = storage

    @staticmethod
    def lat_from_met(met):
        return Gatherer.LAT_PER_100M * met / 100.0

    @staticmethod
    def long_from_met(met):
        return Gatherer.LONG_PER_100M * met / 100

    @staticmethod
    def _get_coords(city):
        return geocoder.google(city).latlng

    @staticmethod
    def _clean_url(url):
        if url.startswith('http://web.'):
            url = url[:7] + url[11:]
        elif url.startswith('https://web.'):
            url = url[:8] + url[12:]
        return url

    @staticmethod
    def _response_to_post(post, page_id):
        return {
            'id': post['id'],
            'page_id': page_id,
            'message': post['message'],
            'created_time': post['created_time'],
            'link': post['link'],
            'like': post['like']['summary']['total_count'],
            'love': post['love']['summary']['total_count'],
            'haha': post['haha']['summary']['total_count'],
            'wow': post['wow']['summary']['total_count'],
            'sad': post['sad']['summary']['total_count'],
            'angry': post['angry']['summary']['total_count'],
            'thankful': post['thankful']['summary']['total_count'],
        }

    # Generator
    @staticmethod
    def _generate_points(radius, scan_radius, center_point_lat, center_point_lng):
        top = center_point_lat + Gatherer.lat_from_met(radius)
        left = center_point_lng - Gatherer.long_from_met(radius)

        bottom = center_point_lat - Gatherer.lat_from_met(radius)
        right = center_point_lng + Gatherer.long_from_met(radius)

        scan_radius_step = (Gatherer.lat_from_met(scan_radius),
                            Gatherer.long_from_met(scan_radius))

        lat = top
        lng = left
        while lat > bottom:
            while lng < right:
                yield (lat, lng)
                lng += scan_radius_step[1]
            lng = left
            lat -= scan_radius_step[0]

    def _get_pageids_loc(self, lat, lon, scan_radius, keyword, limit):
        # Getting the pages from graph api
        args = (
            keyword,
            lat,
            lon,
            scan_radius,
            limit,
            self.token
        )
        req_string = 'https://graph.facebook.com/v2.8/search?type=place&' + \
            'q={0}&center={1},{2}&distance={3}&limit={4}&fields=id&access_token={5}'\
            .format(*args)
        pages_id = requests.get(req_string).json()
        # Quick list comprehension to extract the IDs
        pages_id_list = [i['id'] for i in pages_id['data']]
        # There are multiple pages in the response
        while 'paging' in pages_id and 'next' in pages_id['paging']:
            pages_id = requests.get(pages_id['paging']['next']).json()
            for page in pages_id['data']:
                pages_id_list.append(page.get('id', None))
        return pages_id_list

    def _events_from_pageid(self, page_id, start_time=time.time()):
        try:
            params = {
                'ids': page_id,
                'fields': 'events.fields(id,name,start_time,description,place,type,category,ticket_uri,cover.' +
                          'fields(id,source),picture.type(large),attending_count,declined_count,maybe_count,' +
                          'noreply_count).since({0}),id,name,cover.fields(id,source),picture.type(large),location'.format(
                              int(start_time)),
                'access_token': self.token,
            }
            # TODO: Add place_type to the query
            events = requests.get(
                'https://graph.facebook.com/v2.8/', params=params)
            return events.json()
        except Exception as e:
            print(e)
            return None

    def _get_events_simple(self, scan_radius, city, radius, keyword, limit, events_max, pages_max):
        i = 0
        events = []
        places = []
        for point in self._generate_points(radius, scan_radius, *Gatherer._get_coords(city)):
            logging.debug(
                'Gatherer - Events <simple>: Processing point {0}'.format(point))
            for page_id in self._get_pageids_loc(point[0], point[1], scan_radius, keyword, limit):
                if page_id:
                    page_events = self._events_from_pageid(page_id)[page_id]
                    if page_events and 'events' in page_events:
                        for event in page_events['events']['data']:
                            place = event.get('place', None)
                            if place:
                                logging.debug(
                                    'Gatherer - Events <simple>: Processing place {0}'.format(place))
                                if place not in places:
                                    places.append(place)
                                    i += 1
                                logging.debug(
                                    'Gatherer - Events <simple>: Adding event {0}'.format(events))
                                event['place_id'] = place.get('id', '0')
                                events.append(event)
                                logging.debug('Gatherer - Events <simple>: Processed {} places with {} events...'.format(
                                    len(places), len(events)))
                                if len(events) >= events_max:
                                    return events, places
                        if i >= pages_max:
                            logging.info(
                                'Gatherer - Events <simple>: Processed >=max pages, stopping...')
                            return events, places
        return events, places

    def _get_events_storage(self, scan_radius, city, radius, keyword, limit, events_max, pages_max):
        i = 0
        events = []
        places = []
        for point in self._generate_points(radius, scan_radius, *Gatherer._get_coords(city)):
            logging.debug(
                'Gatherer - Events <storage>: Processing point {0}'.format(point))
            for page_id in self._get_pageids_loc(point[0], point[1], scan_radius, keyword, limit):
                if page_id:
                    page_events = self._events_from_pageid(page_id)[page_id]
                    if page_events and 'events' in page_events:
                        for event in page_events['events']['data']:
                            place = event.get('place', None)
                            if place:
                                logging.debug(
                                    'Gatherer - Events <storage>: Processing place {0}'.format(place))
                                if place not in places and not self.storage.place_exists(place.get('id', '0')):
                                    places.append(place)
                                    i += 1
                                if event and event not in events and not self.storage.event_exists(event.get('id', '0')):
                                    event['place_id'] = place.get('id', '0')
                                    events.append(event)
                                    logging.debug(
                                        'Gatherer - Events <storage>: Adding event {0}'.format(events))
                                    if len(events) >= events_max:
                                        return events, places
                                logging.debug('Gatherer - Events <storage>: Processed {} places with {} events...'
                                              .format(len(places), len(events)))
                        if i >= pages_max:
                            logging.info(
                                'Gatherer - Events <storage>: Processed >=max pages, stopping...')
                            return events, places
        return events, places

    def _exit(self):
        sys.exit(0)

    def get_place_topics(self, place_id, use_storage=True, **kwargs):
        if not self.storage and use_storage:
            raise Exception(
                'Gatherer: get_events_loc - Storage wasn\'t defined')
        logging.debug('Gatherer: Get place topics request, id={0}'
                      .format(place_id))
        # TODO: Read the place_id, process the api with ?place_topics, return
        # the topics

    # TODO: Add a function for updating place types based on the db
    # TODO: Add a function for updating place topics based on the db

    def get_events_loc(self, scan_radius, city, radius, use_storage=True, **kwargs):
        if not self.storage and use_storage:
            raise Exception(
                'Gatherer: get_events_loc - Storage wasn\'t defined')

        logging.debug('Gatherer: Get events request, city = {0}, scan_r = {1}, radius = {2}'
                      .format(city, scan_radius, radius))

        pages_max = kwargs.get('pages_max', 5)
        events_max = kwargs.get('events_max', 30)
        keyword = kwargs.get('keyword', '*')
        limit = kwargs.get('limit', '')
        if use_storage:
            places, events = self._get_events_storage(
                scan_radius, city, radius, keyword, limit, events_max, pages_max
            )
            for p in places:
                storage.save_place(p)
            for e in events:
                storage.save_event(e)
            return places, events
        else:
            return self._get_events_simple(
                scan_radius, city, radius, keyword, limit, events_max, pages_max
            )

    def get_page(self, page_id, get_posts=True):
        # id,name,about,category,fan_count
        request_str = ('https://graph.facebook.com/v2.9/{}'
                       '?fields=id,name,about,category,fan_count'
                       '&access_token={}')
        page = requests.get(request_str.format(page_id, self.token)).json()
        self.storage.save_page(page)
        if get_posts:
            for post in self.get_posts(page['id']):
                self.storage.save_post(post)

    def get_page_id(self, url):
        url = Gatherer._clean_url(url)
        request_str = 'https://graph.facebook.com/v2.9/?id={}&access_token={}'
        response = requests.get(request_str.format(url, self.token)).json()
        return response['id']

    def get_posts(self, page_id, limit=100):
        # nytimes?fields=posts{link,message,id,created_time}
        request_str = ('https://graph.facebook.com/v2.9/{}'
                       '?fields=posts{{link, message, id, created_time,'
                       'reactions.type(LIKE).limit(0).summary(total_count).as(like),'
                       'reactions.type(LOVE).limit(0).summary(total_count).as(love),'
                       'reactions.type(HAHA).limit(0).summary(total_count).as(haha),'
                       'reactions.type(WOW).limit(0).summary(total_count).as(wow),'
                       'reactions.type(SAD).limit(0).summary(total_count).as(sad),'
                       'reactions.type(ANGRY).limit(0).summary(total_count).as(angry),'
                       'reactions.type(THANKFUL).limit(0).summary(total_count).as(thankful)}}'
                       '&access_token={}')
        # print(request_str.format(page_id, self.token))
        response = requests.get(request_str.format(
            page_id, self.token)).json()['posts']
        posts = []
        i = 0
        while 'paging' in response and 'next' in response['paging']:
            response = requests.get(response['paging']['next']).json()
            for post in response['data']:
                posts.append(Gatherer._response_to_post(post, page_id))
                i += 1
            if i >= limit:
                break
        return posts

    def get_post_reactions(self, post_id):
        request_str = ('https://graph.facebook.com/v2.9/{}?fields='
                       'reactions.type(LIKE).limit(0).summary(total_count).as(like),'
                       'reactions.type(LOVE).limit(0).summary(total_count).as(love),'
                       'reactions.type(HAHA).limit(0).summary(total_count).as(haha),'
                       'reactions.type(WOW).limit(0).summary(total_count).as(wow),'
                       'reactions.type(SAD).limit(0).summary(total_count).as(sad),'
                       'reactions.type(ANGRY).limit(0).summary(total_count).as(angry),'
                       'reactions.type(THANKFUL).limit(0).summary(total_count).as(thankful)'
                       '&access_token={}')
        response = requests.get(request_str.format(post_id, self.token)).json()
        del response['id']
        return {item: response[item]['summary']['total_count'] for item in response}


if __name__ == '__main__':
    import argparse
    argparser = argparse.ArgumentParser(
        description='Updates the facebook database with new data')
    argparser.add_argument('-up', '--update-places', dest='update_places', action='store_true',
                           help='Update the place_type column in the table Places')
    argparser.add_argument('-ue', '--update-events', dest='update_events', action='store_true',
                           help='Update the Event database. Configure which events are added in config.json')
    argparser.add_argument('-v', '--verbose', dest='verbose', action='store_true',
                           help='Enable DEBUG verbosity mode.')
    args = argparser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if args.update_places:
        pass

    if args.update_events:
        with open('config.json', 'r') as f:
            args = json.load(f)

        storage = Storage()
        gatherer = Gatherer(args['client_id'],
                            args['client_secret'], storage=storage)
        # print(gatherer.get_posts(gatherer.get_page_id('https://web.facebook.com/cnn/')))
        gatherer.get_events_loc(args['scan_radius'], args['city'], args['radius'],
                                keyword=args['keyword'], pages_max=args['pages_max'],
                                limit=args['limit'], events_max=args['events_max'])
