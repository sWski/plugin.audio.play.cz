# -*- coding: utf-8 -*-
"""
    resources.lib.api
    ~~~~~~~~~~~~~~~~~~

    Implementation of play.cz API.

    :copyright: (c) 2015 by Jakub Smutný
    :license: GPLv3, see LICENSE.txt for more details.
"""
from urllib import urlencode
from urllib2 import urlopen, Request, HTTPError, URLError
from json import loads

# http://api.play.cz/<FORMAT>/<FUNKCE>/<...params...>
API_URL = 'http://api.play.cz/json/'


class NetworkError(Exception):
    pass


class PlayApi():

    USER_AGENT = (
        'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:36.0) '
        'Gecko/20100101 Firefox/36.0'
    )

    def get_stations(self, genre_id, region_id, top25):
        params = {}
        if genre_id:
            params['styl'] = genre_id
        if region_id:
            params['kraj'] = region_id
        path = 'getRadios'
        if top25:
            path = 'getTopRadios'
        data = self.__api_call(path, params)
        return self._parse_stations(data['data'])

    def get_genres(self):
        path = 'getStyles'
        data = self.__api_call(path)
        return self._parse_basic_info(data['data'])

    def get_regions(self):
        path = 'getRegions'
        data = self.__api_call(path)
        return self._parse_basic_info(data['data'])

    def get_all_streams(self, station_id):
        path = 'getAllStreams/%s' % station_id
        data = self.__api_call(path)
        return self._parse_streams(data['data']['streams'])

    def get_stream(self, station_id, format, bitrate):
        path = 'getStream/%s/%s/%s' % (station_id, format, bitrate)
        data = self.__api_call(path)
        return data['data']['stream']['pubpoint']

    @staticmethod
    def _parse_stations(stations):

        def get_genre(style, style_title):
            if style_title:
                return style_title[0]
            elif style:
                return style[0]
            return ''

        items = []
        for key in stations:
            station = stations[key]
            info = station.get('radio_info', {})
            items.append({
                'id': station.get('shortcut', key),
                'thumbnail': station.get('logoimg_m', station.get('logo', '')),
                'title': station.get('title', '').strip(),
                'listeners': station.get('listeners', ''),
                'comment': station.get('description', '').strip(),
                'genre': get_genre(station.get('style', []),
                                   station.get('style_title', [])),
                'web': info.get('web1', '').strip()
            })
        return items

    @staticmethod
    def _parse_basic_info(info):
        return [{
            'id': item.get('id', ''),
            'title': item.get('title', '')
        } for item in info]

    @staticmethod
    def _parse_streams(streams):
        items = []
        for format in streams:
            for bitrate in streams[format]:
                items.append({
                    'format': format,
                    'bitrate': bitrate
                })
        return items

    def __api_call(self, path, params=None):
        url = API_URL + path
        if params:
            url += '?%s' % urlencode(params)
        response = self.__urlopen(url)
        return loads(response)

    def __urlopen(self, url):
        print 'Opening url: %s' % url
        req = Request(url)
        req.add_header('User-Agent', self.USER_AGENT)
        try:
            response = urlopen(req).read()
        except HTTPError, error:
            raise NetworkError('HTTPError: %s' % error)
        except URLError, error:
            raise NetworkError('URLError: %s' % error)
        return response
