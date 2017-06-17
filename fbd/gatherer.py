# STL imports
# Package imports
import asyncio
import json
import logging
import sys

import aiohttp
import async_timeout
import numpy as np
import requests
from tqdm import tqdm, trange  # Progress bar

import fbd.tools
from fbd.storage import Storage


class Gatherer:
    # TODO: Move to numpy arrays / DFs?
    # TODO: Store the already processed points as a table in a db for faster
    # --get-places
    def __init__(self, client_id, client_secret, storage=None, logger=None):
        if not logger:
            logging.basicConfig(level=logging.INFO)
            logging.info('Gatherer: Didn\'t receive a custom logger,'
                         'so falling back to the default one')
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
            'https://graph.facebook.com/v2.9/oauth/access_token?',
            params=token_params).json()['access_token']
        self.logger.debug('Gatherer: Initialized')
        self.storage = storage
        self.PLACE_ID_DETAILS_URL = ('https://graph.facebook.com/v2.9/{}'
                                     '?fields=id,name,place_type,place_topics,'
                                     'cover.fields(id,source),picture.type(large),'
                                     f'location&access_token={self.token}')
        self.PLACE_LAT_LON_RADIUS_URL = ('https://graph.facebook.com/v2.9/'
                                         'search?type=place&q="*"&center={},{}'
                                         '&distance={}&fields=id&'
                                         f'access_token={self.token}''')

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
    def _generate_points(radius, circle_radius, center_point_lat,
                         center_point_lng):
        # Defining the general square bounds
        top = center_point_lat + fbd.tools.lat_from_met(radius)
        bottom = center_point_lat - fbd.tools.lat_from_met(radius)
        left = center_point_lng - fbd.tools.lon_from_met(radius)
        right = center_point_lng + fbd.tools.lon_from_met(radius)

        circle_step = (fbd.tools.lat_from_met(circle_radius),
                       fbd.tools.lon_from_met(circle_radius))

        lat = top
        lng = left

        # Iterating by small circles from top->bottom from left->right
        while lat > bottom:
            while lng < right:
                yield lat, lng
                lng += circle_step[1]
            lng = left
            lat -= circle_step[0]

    @staticmethod
    def _num_iters(radius, circle_radius, center_point_lat, center_point_lng):
        # Exhaust the _generate_points generator and count the # circles
        return len([
            x
            for x, _ in Gatherer._generate_points(
                radius, circle_radius, center_point_lat, center_point_lng)
        ])

    def _exit(self):
        self.logger.info('Gatherer - _exit: EXITING APPLICATION')
        sys.exit(0)

    def get_place_from_id(self, place_id, save_storage=True):
        if not self.storage and save_storage:
            raise Exception('Gatherer: get_place_from_id - '
                            'storage wasn\'t defined')
        self.logger.debug(
            'Gatherer: Get place request, id={0}'.format(place_id))
        params = {
            'ids': place_id,
            'fields': 'id,name,place_type,place_topics,cover.fields(id,source),'
                      'picture.type(large),location',
            'access_token': self.token
        }
        place = requests.get('https://graph.facebook.com/v2.9/',
                             params=params).json()[place_id]
        if save_storage:
            self.storage.update_place(place)
        return place

    @staticmethod
    async def get_json(url, session, sem, params=None, timeout=10):
        async with sem:
            with async_timeout.timeout(timeout):
                async with session.get(url, params=params) as response:
                    return json.loads(await response.text())

    @staticmethod
    async def get_text(url, session, sem, params=None, timeout=10):
        async with sem:
            with async_timeout.timeout(timeout):
                async with session.get(url, params=params) as response:
                    return await response.text()

    @staticmethod
    async def get_links_list(links, json=True, max_concurrent=3, desc=None):
        sem = asyncio.Semaphore(max_concurrent)
        async with aiohttp.ClientSession() as session:
            tasks = [
                asyncio.ensure_future(
                    Gatherer.get_json(link, session, sem)
                    if json else Gatherer.get_text(link, session, sem))
                for link in links
            ]
            responses = [
                await resp
                for resp in tqdm(
                    asyncio.as_completed(tasks),
                    desc=desc,
                    total=len(tasks),
                )
            ]
        return responses

    @staticmethod
    async def get_links(links, json=True, max_concurrent=3, desc=None):
        sem = asyncio.Semaphore(max_concurrent)
        async with aiohttp.ClientSession() as session:
            tasks = [
                asyncio.ensure_future(
                    Gatherer.get_json(link, session, sem)
                    if json else Gatherer.get_text(link, session, sem))
                for link in links
            ]
            for resp in tqdm(
                    asyncio.as_completed(tasks),
                    desc=desc,
                    total=len(tasks),
            ):
                yield await resp

    async def _get_place_ids_point(self, lat, lon, circle_radius, session, sem):
        # Getting the pages from graph api

        id_list = []
        response = await self.get_json(
            self.PLACE_LAT_LON_RADIUS_URL.format(lat, lon, circle_radius),
            session, sem
        )
        # Quick list comprehension to extract the IDs
        place_id_list = [i.get('id') for i in response.get('data', [{}])]
        for id_ in place_id_list:
            if id_:
                id_list.append(id_)
        next_page = 'paging' in response and 'next' in response['paging']
        # There are multiple pages in the response

        while next_page:
            response = await self.get_json(response['paging']['next'], session, sem)
            for place in response['data']:
                id_ = place.get('id')
                if id_:
                    id_list.append(id_)
            next_page = 'paging' in response and 'next' in response['paging']
        return id_list if id_list else None

    async def _process_saving_places(self, fetch_tasks, save_storage,
                                     loop, session, sem, block_id):
        self.logger.debug(f'_process_saving_places - ftasks={len(fetch_tasks)}'
                          f'block id = {block_id}')
        places_details_tasks = []
        places = []
        for place_ids in tqdm(asyncio.as_completed(fetch_tasks),
                              total=len(fetch_tasks), file=sys.stdout,
                              desc=f'[Block {block_id}] Processing points'):
            for pid in await place_ids:
                places_details_tasks.append(asyncio.ensure_future(
                    self.get_json(
                        self.PLACE_ID_DETAILS_URL.format(pid), session, sem
                    )))
        for place_details in tqdm(asyncio.as_completed(places_details_tasks),
                                  total=len(places_details_tasks),
                                  file=sys.stdout,
                                  desc=f'[Block {block_id}] Processing place details'):
            places.append(await place_details)
        if save_storage:
            return asyncio.ensure_future(
                loop.run_in_executor(
                    None, self.storage.save_placelist, places)
            )
        else:
            return places

    async def _get_places_loc(self, circle_radius, city, radius, loop,
                              save_storage, max_concurrent, block_size):
        self.logger.debug('_get_places_loc - starting')
        sem = asyncio.Semaphore(max_concurrent)
        city_coords = fbd.tools.get_coords(city)
        # num_iters = self._num_iters(radius, circle_radius, *city_coords)
        fetch_tasks = []
        save_outs = []
        block_id = 0
        async with aiohttp.ClientSession() as session:
            for i, coords in enumerate(
                    self._generate_points(radius, circle_radius, *city_coords)
            ):
                fetch_tasks.append(
                    asyncio.ensure_future(
                        self._get_place_ids_point(*coords, radius, session, sem)
                    )
                )
                if (i + 1) % block_size == 0:
                    block_id += 1
                    save_outs.append(
                        self._process_saving_places(
                            fetch_tasks, save_storage, loop,
                            session, sem, block_id)
                    )
                    fetch_tasks = []
            else:
                block_id += 1
                save_outs.append(
                    self._process_saving_places(fetch_tasks, save_storage,
                                                loop, session, sem, block_id)
                )
                fetch_tasks = []
            res = await asyncio.gather(*save_outs)
            if save_storage:
                for task in tqdm(asyncio.as_completed(res),
                                 total=len(res),
                                 file=sys.stdout,
                                 desc='Saving the results'):
                    await task
            else:
                if type(res[0]) == list:
                    return [item for subarray in res for item in subarray]
                else:
                    return res

    def get_places_loc(self, circle_radius, city, radius, save_storage=True,
                       max_concurrent=3, block_size=3):
        if not self.storage and save_storage:
            raise Exception('Gatherer: get_places_loc - '
                            'storage wasn\'t defined')
        # ASYNC
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            res = loop.run_until_complete(
                self._get_places_loc(circle_radius, city, radius, loop,
                                     save_storage, max_concurrent, block_size)
            )
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

        return res

    def _get_events_from_place_id_syn(self, place_id):
        # Getting the pages from graph api
        req_string = (
            'https://graph.facebook.com/v2.9/{}?fields=events{{id,name,'
            'start_time,description,place,type,category,ticket_uri,'
            'cover.fields(id,source),picture.type(large),attending_count,'
            'declined_count,maybe_count,noreply_count}}&access_token={}'
        ).format(place_id, self.token)
        response = requests.get(req_string).json()
        event_list = [i for i in response.get('events', {}).get('data', [])]
        # There are multiple pages in the response and we already went thru 1
        while response.get('events', {}).get('paging', {}).get('next', None):
            response = requests.get(response['events']['paging']['next']).json()
            for event in response.get('data', []):
                event_list.append(event)
        return [place_id, event_list]

    async def _get_events_from_places(self, loop, place_ids):
        tasks = [
            loop.run_in_executor(None, self._get_events_from_place_id_syn,
                                 place_id) for place_id in place_ids
        ]
        events = []
        for pid_elist in tqdm(
                asyncio.as_completed(tasks), total=len(place_ids),
                desc='Getting events per place', unit='place', file=sys.stdout):
            pelist = await pid_elist
            for event in tqdm(pelist[1], desc='Processing place events',
                              unit='events', file=sys.stdout):
                event['place_id'] = pelist[0]
                events.append(event)
        return events

    def get_events_from_places(self, save_storage=True):
        if not self.storage:
            raise Exception('Gatherer: get_events_from_places - '
                            'storage wasn\'t defined')
        self.logger.debug('Gatherer: get_events_from_places request')
        place_ids = self.storage.get_all_place_ids()

        loop = asyncio.get_event_loop()
        events = loop.run_until_complete(
            asyncio.ensure_future(
                self._get_events_from_places(loop, place_ids)
            )
        )
        loop.close()

        if save_storage:
            for e in tqdm(events, desc='Saving events', leave=False,
                          file=sys.stdout, unit='event'):
                self.storage.save_event(e)
        return events

    async def _update_places(self, place_ids, max_concurrent=3):
        places = []
        sem = asyncio.Semaphore(max_concurrent)
        # TODO: make those urls into classwide constants
        url = ('https://graph.facebook.com/v2.9/{0}?fields=id,name,'
               'place_type,place_topics,cover.fields(id,source),'
               'picture.type(large),location&access_token={1}')
        async with aiohttp.ClientSession() as session:
            tasks = [
                Gatherer.get_json(url.format(pid, self.token), session, sem)
                for pid in place_ids
            ]
            for place in tqdm(
                    asyncio.as_completed(tasks), total=len(place_ids),
                    desc='Updating places', unit='place', file=sys.stdout):
                places.append(await place)
            return places

    def update_places(self, max_concurrent=3):
        if not self.storage:
            raise Exception('Gatherer: update_places - '
                            'storage wasn\'t defined')
        place_ids = self.storage.get_all_place_ids()
        loop = asyncio.get_event_loop()
        places = loop.run_until_complete(
            asyncio.ensure_future(
                self._update_places(place_ids, max_concurrent)))
        loop.close()

        for p in tqdm(places, desc='Saving places', leave=False,
                      file=sys.stdout, unit='place'):
            self.storage.update_place(p)

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
        request_str = (
            'https://graph.facebook.com/v2.9/{}'
            '?fields=posts{{'
            'link, message, id, created_time,'
            'reactions.type(LIKE).limit(0).summary(total_count).as(like),'
            'reactions.type(LOVE).limit(0).summary(total_count).as(love),'
            'reactions.type(HAHA).limit(0).summary(total_count).as(haha),'
            'reactions.type(WOW).limit(0).summary(total_count).as(wow),'
            'reactions.type(SAD).limit(0).summary(total_count).as(sad),'
            'reactions.type(ANGRY).limit(0).summary(total_count).as(angry),'
            'reactions.type(THANKFUL).limit(0).summary(total_count)'
            '.as(thankful)}}&access_token={}')
        # print(request_str.format(page_id, self.token))
        response = requests.get(
            request_str.format(page_id, self.token)).json()['posts']
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
        request_str = (
            'https://graph.facebook.com/v2.9/{}?fields='
            'reactions.type(LIKE).limit(0).summary(total_count).as(like),'
            'reactions.type(LOVE).limit(0).summary(total_count).as(love),'
            'reactions.type(HAHA).limit(0).summary(total_count).as(haha),'
            'reactions.type(WOW).limit(0).summary(total_count).as(wow),'
            'reactions.type(SAD).limit(0).summary(total_count).as(sad),'
            'reactions.type(ANGRY).limit(0).summary(total_count).as(angry),'
            'reactions.type(THANKFUL).limit(0).summary(total_count)'
            '.as(thankful)&access_token={}')
        response = requests.get(request_str.format(post_id, self.token)).json()
        del response['id']
        return {
            item: response[item]['summary']['total_count']
            for item in response
        }


if __name__ == '__main__':
    config = {
        'storage_url': 'sqlite:///fbd/db/fb.sqlite',
        'verbose': False,
        'update_places': False,
        'update_events': False,
    }
    # Configuring the logger
    if config['verbose']:
        logging.basicConfig(level=logging.DEBUG)
        log = logging
    else:
        log = logging.getLogger(__name__)
        log.setLevel(logging.INFO)
        log.addHandler(logging.StreamHandler())

    if config['storage_url']:
        storage = Storage(db_url=config['storage_url'])
    else:
        storage = Storage()

    with open('fbd/config.json', 'r') as f:
        params = json.load(f)

    gatherer = Gatherer(params['client_id'], params['client_secret'],
                        storage=storage, logger=log)
    import time

    start = time.time()
    gatherer.get_places_loc(500, 'Wroclaw', 1000, block_size=20)
    end = time.time()
    print(end - start)

    start = time.time()
    gatherer.get_places_loc(500, 'Wroclaw', 1000, block_size=10)
    end = time.time()
    print(end - start)

    start = time.time()
    gatherer.get_places_loc(500, 'Wroclaw', 1000)
    end = time.time()
    print(end - start)

    # gatherer.get_events_from_places()
    # gatherer.update_places()
    # print(gatherer.get_posts(gatherer.get_page_id('https://web.facebook.com/cnn/')))
    # print(gatherer.get_posts(gatherer.get_page_id('https://web.facebook.com/cnn/')))
