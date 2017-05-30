#!/usr/local/bin/python3
# STL imports
# Package imports
import logging
import sys
import time

import requests
import tqdm  # Progress bar

import fbd.tools


class Gatherer:
    # TODO: Move to numpy arrays / DFs?

    def __init__(self, client_id, client_secret, storage=None, logger=None, disable_progressbar=False):
        if not logger:
            logging.basicConfig(level=logging.INFO)
            logging.info(
                'Gatherer: Didn\'t receive a custom logger so falling back to the default one')
            self.logger = logging
        else:
            self.logger = logger
            self.logger.debug('Gatherer: Using logger {0}'.format(logger))
        self.logger.debug('Gatherer: Started initialization')
        self.client_id = client_id
        self.client_secret = client_secret
        self.logger.debug('Gatherer: Getting the token')
        token_params = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'client_credentials'
        }
        self.token = requests.get(
            'https://graph.facebook.com/v2.8/oauth/access_token?',
            params=token_params).json()['access_token']
        self.logger.debug('Gatherer: Initialized')
        self.storage = storage
        self.disable_progressbar = disable_progressbar

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
        # Defining the general square bounds
        top = center_point_lat + fbd.tools.lat_from_met(radius)
        bottom = center_point_lat - fbd.tools.lat_from_met(radius)
        left = center_point_lng - fbd.tools.lon_from_met(radius)
        right = center_point_lng + fbd.tools.lon_from_met(radius)

        scan_radius_step = (fbd.tools.lat_from_met(scan_radius),
                            fbd.tools.lon_from_met(scan_radius))

        lat = top
        lng = left

        # Iterating by small circles from top->bottom from left->right
        while lat > bottom:
            while lng < right:
                yield (lat, lng)
                lng += scan_radius_step[1]
            lng = left
            lat -= scan_radius_step[0]

    @staticmethod
    def _num_iters(radius, scan_radius, center_point_lat, center_point_lng):
        # Exhaust the _generate_points generator and count the # circles
        return len([x for x, _ in
                    Gatherer._generate_points(radius, scan_radius,
                                              center_point_lat,
                                              center_point_lng)])

    def _exit(self):
        self.logger.info('Gatherer - _exit: EXITING APPLICATION')
        sys.exit(0)

    # Does not return None values
    def _get_placeids_loc(self, lat, lon, scan_radius, keyword, limit):
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
        place_ids = requests.get(req_string).json()
        # Quick list comprehension to extract the IDs
        place_id_list = [i['id'] for i in place_ids['data']]
        # There are multiple pages in the response
        while 'paging' in place_ids and 'next' in place_ids['paging']:
            place_ids = requests.get(place_ids['paging']['next']).json()
            for place in place_ids['data']:
                id_ = place.get('id', None)
                if id_:
                    place_id_list.append(id_)
        return place_id_list

    def _get_place_events_from_id(self, page_id, start_time=time.time()):
        try:
            params = {
                'ids': page_id,
                'fields': 'events.fields('
                'id,name,start_time,description,place,type,category,'
                'ticket_uri,cover.fields(id,source),picture.type(large),'
                'attending_count,declined_count,maybe_count,noreply_count)'
                '.since({0}),'
                'id,name,place_type,place_topics,cover.fields(id,source),'
                'picture.type(large),location'.format(int(start_time)),
                'access_token': self.token,
            }
            self.logger.debug('Gatherer: Received request to get place_events from id'
                              ', page_id={0}, start_time={1}'.format(page_id, start_time))
            events = requests.get(
                'https://graph.facebook.com/v2.8/', params=params).json()
            return events
        except Exception as e:
            print(e)
            return None

    def _get_events_simple(self, scan_radius, city, radius, keyword, limit, events_max, places_max):
        events = []
        places = []
        city_coords = fbd.tools.get_coords(city)
        for point in tqdm.tqdm(
                self._generate_points(radius, scan_radius, *city_coords),
                total=self._num_iters(radius, scan_radius, *city_coords),
                desc='Processing points',
                disable=self.disable_progressbar):
            self.logger.debug(
                'Gatherer - Events: Processing point {0}'.format(point))
            for place_id in tqdm.tqdm(
                    self._get_placeids_loc(point[0], point[1],
                                           scan_radius, keyword, limit),
                    desc='Processing places',
                    disable=self.disable_progressbar):
                place_events = self._get_place_events_from_id(
                    place_id)[place_id]
                if place_events and 'events' in place_events:
                    for event in place_events['events']['data']:
                        place = event.get('place', None)
                        if place and place.get('id'):
                            self.logger.debug(
                                'Gatherer - Events: Processing place {0}'.format(place))
                            # Removing an 'in' check (complexity = O(n) -> O(1))
                            # But this increases required memory
                            places.append(place)
                            self.logger.debug(
                                'Gatherer - Events: Adding event {0}'.format(events))
                            event['place_id'] = place.get('id')
                            # Switching to sets/fdicts from lists to avoid an
                            # 'in' check (complexity = O(n) -> O(1))
                            events.append(event)
                            self.logger.debug('Gatherer - Events: Processed {} places with {} events...'.format(
                                len(places), len(events)))
                            if len(events) >= events_max:
                                return events, places
                    if len(places) >= places_max:
                        self.logger.info(
                            'Gatherer - Events: Processed >=max pages, stopping...')
                        return events, places
        return events, places

    def get_events_loc(self, scan_radius, city, radius, use_storage=True, **kwargs):
        if not self.storage and use_storage:
            raise Exception(
                'Gatherer: get_events_loc - storage wasn\'t defined')

        self.logger.debug('Gatherer: Get events request, city = {0}, scan_r = {1}, radius = {2}'
                          .format(city, scan_radius, radius))

        places_max = kwargs.get('places_max', 5)
        events_max = kwargs.get('events_max', 30)
        keyword = kwargs.get('keyword', '*')
        limit = kwargs.get('limit', '')

        events, places = self._get_events_simple(
            scan_radius, city, radius, keyword, limit, events_max, places_max)

        if use_storage:
            for p in tqdm.tqdm(places, desc='Saving places',
                               disable=self.disable_progressbar):
                self.storage.save_place(p)
            for e in tqdm.tqdm(events, desc='Saving events',
                               disable=self.disable_progressbar):
                self.storage.save_event(e)
            return places, events
        else:
            return places, events

    def get_place_from_id(self, place_id, use_storage=True):
        if not self.storage and use_storage:
            raise Exception(
                'Gatherer: get_events_loc - storage wasn\'t defined')
        self.logger.debug('Gatherer: Get place request, id={0}'
                          .format(place_id))
        params = {
            'ids': place_id,
            'fields': 'id,name,place_type,place_topics,cover.fields(id,source),'
            'picture.type(large),location',
            'access_token': self.token,
        }
        place = requests.get(
            'https://graph.facebook.com/v2.8/',
            params=params).json()[place_id]
        if use_storage:
            self.storage.update_place(place)
        return place

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
