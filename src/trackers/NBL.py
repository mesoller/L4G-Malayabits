# -*- coding: utf-8 -*-
import json
import requests
import httpx

from src.trackers.COMMON import COMMON
from src.console import console
from src.tvmaze import get_tvmaze_show_data


class NBL():
    """
    Edit for Tracker:
        Edit BASE.torrent with announce and source
        Check for duplicates
        Set type/category IDs
        Upload
    """
    def __init__(self, config):
        self.config = config
        self.tracker = 'NBL'
        self.source_flag = 'NBL'
        self.upload_url = 'https://nebulance.io/upload.php'
        self.search_url = 'https://nebulance.io/api.php'
        self.api_key = self.config['TRACKERS'][self.tracker]['api_key'].strip()
        self.banned_groups = ['0neshot', '3LTON', '4yEo', '[Oj]', 'AFG', 'AkihitoSubs', 'AniHLS', 'Anime Time', 'AnimeRG', 'AniURL', 'ASW', 'BakedFish',
                              'bonkai77', 'Cleo', 'DeadFish', 'DeeJayAhmed', 'ELiTE', 'EMBER', 'eSc', 'EVO', 'FGT', 'FUM', 'GERMini', 'HAiKU', 'Hi10', 'ION10',
                              'JacobSwaggedUp', 'JIVE', 'Judas', 'LOAD', 'MeGusta', 'Mr.Deadpool', 'mSD', 'NemDiggers', 'neoHEVC', 'NhaNc3', 'NOIVTC',
                              'PlaySD', 'playXD', 'project-gxs', 'PSA', 'QaS', 'Ranger', 'RAPiDCOWS', 'Raze', 'Reaktor', 'REsuRRecTioN', 'RMTeam', 'ROBOTS',
                              'SpaceFish', 'SPASM', 'SSA', 'Telly', 'Tenrai-Sensei', 'TM', 'Trix', 'URANiME', 'VipapkStudios', 'ViSiON', 'Wardevil', 'xRed',
                              'XS', 'YakuboEncodes', 'YuiSubs', 'ZKBL', 'ZmN', 'ZMNT']

        pass

    async def get_cat_id(self, meta):
        if meta.get('tv_pack', 0) == 1:
            cat_id = 3
        else:
            cat_id = 1
        return cat_id

    async def edit_desc(self, meta):
        # Leave this in so manual works
        return

    genre_abbreviations = {
        "science-fiction": "sci.fi"
    }

    async def get_tags(self, meta):
        if 'tvmaze_show_data' not in meta:
            tvmaze_data = await get_tvmaze_show_data(meta.get('tvmaze_id'), debug=meta['debug'])
        else:
            tvmaze_data = meta['tvmaze_show_data']

        tags = []
        genres = ', '.join(tvmaze_data.get('genres', []))
        for genre in genres.split(','):
            genre = genre.strip(', ').lower()
            # Check for special case genres
            if genre in self.genre_abbreviations:
                tags.append(self.genre_abbreviations[genre])
            else:
                tags.append(genre.replace(' ', '.'))

        if tvmaze_data is not None:
            if 'type' in tvmaze_data and tvmaze_data['type'] != 'Scripted':
                tags.append(tvmaze_data['type'].lower().replace(' ', '.'))
            if 'network' in tvmaze_data:
                if isinstance(tvmaze_data['network'], dict):
                    if tvmaze_data['network'].get('name', '') != '':
                        tags.append(tvmaze_data['network'].get('name', '').lower().replace(' ', '.'))
                elif isinstance(tvmaze_data['network'], str) and tvmaze_data['network'] != '':
                    tags.append(tvmaze_data['network'].lower().replace(' ', '.'))
            if 'webChannel' in tvmaze_data:
                if isinstance(tvmaze_data['webChannel'], dict):
                    if tvmaze_data['webChannel'].get('name', '') != '':
                        tags.append(tvmaze_data['webChannel'].get('name', '').lower().replace(' ', '.'))
                elif isinstance(tvmaze_data['webChannel'], str) and tvmaze_data['webChannel'] != '':
                    tags.append(tvmaze_data['webChannel'].lower().replace(' ', '.'))

        # Resolution
        tags.append(meta['resolution'].lower())
        if meta['sd'] == 1:
            tags.append('sd')
        elif meta['resolution'] in ['2160p']:
            tags.append('4k')

        # Streaming Service
        if str(meta['service_longname']) != "":
            service_name = meta['service_longname'].lower()
            tags.append(f"{service_name}")

        # Release Type/Source
        for each in ['remux', 'WEB.DL', 'WEBRip', 'HDTV', 'BluRay', 'DVD', 'HDDVD']:
            if (each.lower().replace('.', '') in meta['type'].lower()) or (each.lower().replace('-', '') in meta['source'].lower()):
                tags.append(each.lower().replace('.', ''))

        if meta['category'] == "TV":
            if meta.get('tv_pack', 0) == 0:
                tags.extend(['episode'])
            else:
                tags.append('season')

        # Audio tags
        if 'atmos' in meta['audio'].lower():
            tags.append('atmos')

        # Video tags
        video_codec = meta.get('video_codec', '').lower().replace('-', '')
        if video_codec and video_codec not in tags:
            tags.append(video_codec)

        # Add alternate codec tags without duplicates
        if 'hevc' in video_codec or 'h265' in video_codec:
            if 'hevc' not in tags:
                tags.append('hevc')
            if 'h265' not in tags:
                tags.append('h265')
        elif 'avc' in video_codec or 'h264' in video_codec:
            if 'avc' not in tags:
                tags.append('avc')
            if 'h264' not in tags:
                tags.append('h264')

        # Group Tags
        if meta['tag'] != "":
            tags.append(f"{meta['tag'][1:].replace('-', '').lower()}.release")
        else:
            tags.append('nogrp.release')

        # Scene/P2P
        if meta['scene']:
            tags.append('scene')
        else:
            tags.append('p2p')

        # Has subtitles
        if meta.get('is_disc', '') != "BDMV":
            if any(track.get('@type', '') == "Text" for track in meta['mediainfo']['media']['track']):
                tags.append('subtitles')
        else:
            if len(meta['bdinfo']['subtitles']) >= 1:
                tags.append('subtitles')

        # HDR
        if 'HDR' in meta['hdr']:
            tags.append('hdr')
        if 'DV' in meta['hdr']:
            tags.append('dovi')
        if 'HLG' in meta['hdr']:
            tags.append('hlg')

        # File extensions (for non-disc releases)
        if not meta.get('is_disc') and meta.get('filelist'):
            extensions = set()
            for file_path in meta['filelist']:
                if '.' in file_path:
                    ext = file_path.split('.')[-1].lower()
                    if ext:
                        extensions.add(ext)

            for ext in extensions:
                if ext not in tags:
                    tags.append(ext)

        tags = ' '.join(tags)
        return tags

    async def upload(self, meta, disctype):
        common = COMMON(config=self.config)
        await common.edit_torrent(meta, self.tracker, self.source_flag)
        tags = await self.get_tags(meta)

        if meta['bdinfo'] is not None:
            mi_dump = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/BD_SUMMARY_00.txt", 'r', encoding='utf-8').read()
        else:
            mi_dump = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/MEDIAINFO_CLEANPATH.txt", 'r', encoding='utf-8').read().strip()
        open_torrent = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}].torrent", 'rb')
        files = {'file_input': open_torrent}
        data = {
            'api_key': self.api_key,
            'tvmazeid': int(meta.get('tvmaze_id', 0)),
            'mediainfo': mi_dump,
            'category': await self.get_cat_id(meta),
            'tags[]': tags,
            'ignoredupes': 'on'
        }

        if meta['debug'] is False:
            response = requests.post(url=self.upload_url, files=files, data=data)
            try:
                if response.ok:
                    response = response.json()
                    console.print(response.get('message', response))
                else:
                    console.print(response)
                    console.print(response.text)
            except Exception:
                console.print_exception()
                console.print("[bold yellow]It may have uploaded, go check")
                return
        else:
            console.print("[cyan]Request Data:")
            console.print(data)
        open_torrent.close()

    async def search_existing(self, meta, disctype):
        if meta['category'] != 'TV':
            console.print("[red]Only TV Is allowed at NBL")
            meta['skipping'] = "NBL"
            return []

        if meta.get('is_disc') is not None:
            console.print('[bold red]NBL does not allow raw discs')
            meta['skipping'] = "NBL"
            return []

        dupes = []
        console.print("[yellow]Searching for existing torrents on NBL...")

        if int(meta.get('tvmaze_id', 0)) != 0:
            search_term = {'tvmaze': int(meta['tvmaze_id'])}
        elif int(meta.get('imdb_id')) != 0:
            search_term = {'imdb': meta.get('imdb')}
        else:
            search_term = {'series': meta['title']}
        payload = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'getTorrents',
            'params': [
                self.api_key,
                search_term
            ]
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(self.search_url, json=payload)
                if response.status_code == 200:
                    try:
                        data = response.json()
                        for each in data.get('result', {}).get('items', []):
                            if meta['resolution'] in each.get('tags', []):
                                dupes.append(each['rls_name'])
                    except json.JSONDecodeError:
                        console.print("[bold yellow]Response content is not valid JSON. Skipping this API call.")
                        meta['skipping'] = "NBL"
                else:
                    console.print(f"[bold red]HTTP request failed. Status: {response.status_code}")
                    meta['skipping'] = "NBL"

        except httpx.TimeoutException:
            console.print("[bold red]Request timed out after 5 seconds")
            meta['skipping'] = "NBL"
        except httpx.RequestError as e:
            console.print(f"[bold red]An error occurred while making the request: {e}")
            meta['skipping'] = "NBL"
        except KeyError as e:
            console.print(f"[bold red]Unexpected KeyError: {e}")
            if 'result' not in response.json():
                console.print("[red]NBL API returned an unexpected response. Please manually check for dupes.")
                dupes.append("ERROR: PLEASE CHECK FOR EXISTING RELEASES MANUALLY")
        except Exception as e:
            meta['skipping'] = "NBL"
            console.print(f"[bold red]Unexpected error: {e}")
            console.print_exception()

        return dupes
