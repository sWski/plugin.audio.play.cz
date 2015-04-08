# -*- coding: utf-8 -*-
"""
    Play.cz Kodi addon
    ~~~~~~~~~~~~~~~~~~

    Listen to on-line radios via play.cz
    http://www.play.cz/

    :copyright: (c) 2015 by Jakub Smutný
    :license: GPLv3, see LICENSE.txt for more details.
"""

from xbmcswift2 import Plugin
from resources.lib.api import PlayApi, NetworkError

plugin = Plugin()
api = PlayApi()

STRINGS = {
    'all_stations': 30000,
    'top25_stations': 30001,
    'genres': 30002,
    'regions': 30003,
    'website': 30004,
    'network_error': 30010,
}

TTL_WEEK = 7 * 24 * 60


@plugin.cached_route('/', TTL=TTL_WEEK)
def show_root_menu():
    """The plugin menu, shows available categories"""
    items = [
        {'label': _T('all_stations'),
         'path': plugin.url_for('show_stations')},
        {'label': _T('top25_stations'),
         'path': plugin.url_for('show_top25')},
        {'label': _T('genres'),
         'path': plugin.url_for('show_genres')},
        {'label': _T('regions'),
         'path': plugin.url_for('show_regions')}
    ]
    return items


@plugin.route('/stations/')
@plugin.route('/stations/top25/', name='show_top25', options={'top25': True})
@plugin.route('/stations/by_genre/<genre_id>/', name='show_by_genre')
@plugin.route('/stations/by_region/<region_id>/', name='show_by_region')
def show_stations(genre_id=None, region_id=None, top25=False):
    """Shows the list with stations. Output can be filtered by genre, style
    or it can show top 25 stations only.
    """

    def prepare_comment(comment, web):
        if comment:
            comment = comment[0].upper() + comment[1:]
            if not comment.endswith(('.', '!', '?')):
                comment += '.'
        if web:
            if comment:
                comment += '\n'
            web = _T('website') + ': ' + web
        return comment + web

    ttl = 24 * 60
    if top25:
        ttl = 5

    stations = get_cached(api.get_stations, genre_id, region_id, top25, TTL=ttl)
    items = [{
        'label': station.get('title'),
        'thumbnail': station.get('thumbnail'),
        'info': {
            'comment': prepare_comment(station.get('comment'),
                                       station.get('web')),
            'genre': station.get('genre'),
            'listeners': int(station.get('listeners'))
        },
        'path': plugin.url_for(
            endpoint='show_streams',
            station_id=station.get('id'),
            params={
                'name': station.get('title').encode('utf-8'),
                'genre': station.get('genre').encode('utf-8'),
                'listeners': station.get('listeners'),
                'thumbnail': station.get('thumbnail')
            }
        ),
    } for station in stations]

    sort_methods = ['label', 'listeners']
    if top25:
        del sort_methods[0]

    return plugin.finish(items, sort_methods=sort_methods)


@plugin.route('/genres/')
def show_genres():
    genres = get_cached(api.get_genres, TTL=TTL_WEEK)
    items = [{
        'label': genre.get('title'),
        'path': plugin.url_for(
            endpoint='show_by_genre',
            genre_id=genre.get('id')
        )
    } for genre in genres]
    return plugin.finish(items, sort_methods=['label'])


@plugin.route('/regions/')
def show_regions():
    regions = get_cached(api.get_regions, TTL=TTL_WEEK)
    items = [{
        'label': region.get('title'),
        'path': plugin.url_for(
            endpoint='show_by_region',
            region_id=region.get('id')
        )
    } for region in regions]
    return plugin.finish(items, sort_methods=['label'])


@plugin.route('/station/<station_id>/')
def show_streams(station_id):
    """Shows avaible stream formats and bitrates"""
    params = plugin.request.args['params'][0]
    name = params.get('name').decode('utf-8')
    genre = params.get('genre').decode('utf-8')
    listeners = int(params.get('listeners'))
    thumb = params.get('thumbnail')

    streams = get_cached(api.get_all_streams, station_id)
    items = [{
        'label': name + ' | ' + stream.get('format').upper(),
        'thumbnail': thumb,
        'info': {
            'title': name + ' | ' + stream.get('format').upper(),
            'genre': genre,
            'listeners': listeners,
            'size': int(stream.get('bitrate'))
        },
        'path': plugin.url_for(
            endpoint='get_stream_url',
            station_id=station_id,
            format=stream.get('format'),
            bitrate=stream.get('bitrate'),
        ),
        'is_playable': True,
    } for stream in streams]
    return plugin.finish(items, sort_methods=[('label', '%X'), 'bitrate'])


@plugin.route('/station/<station_id>/<format>/<bitrate>/')
def get_stream_url(station_id, format, bitrate):
    """Returns stream URL for specified station, format and bitrate"""
    stream_url = get_cached(api.get_stream, station_id, format, bitrate)
    return plugin.set_resolved_url(stream_url)


def get_cached(func, *args, **kwargs):
    """Returns the result of func with the given args and kwargs
    from cache or executes it if needed
    """
    @plugin.cached(kwargs.pop('TTL', 1440))
    def wrap(func_name, *args, **kwargs):
        return func(*args, **kwargs)
    return wrap(func.__name__, *args, **kwargs)


def _T(string_id):
    """Returns the localized string from strings.xml for the given string_id.
    If the string_id is not in known strings, returns string_id.
    """
    if string_id in STRINGS:
        return plugin.get_string(STRINGS[string_id]).encode('utf-8')
    else:
        plugin.log.warning('String is missing: %s' % string_id)
        return string_id


if __name__ == '__main__':
    try:
        plugin.run()
    except NetworkError, error:
        plugin.notify(msg=_T('network_error'))
        plugin.log.error(error)
