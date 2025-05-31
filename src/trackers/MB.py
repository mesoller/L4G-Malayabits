# -*- coding: utf-8 -*-
# import discord
import asyncio
import requests
import platform
import re
import os
import glob
import httpx

from src.trackers.COMMON import COMMON
from src.console import console


class MB():
    """
    Edit for Tracker:
        Edit BASE.torrent with announce and source
        Check for duplicates
        Set type/category IDs
        Upload
    """
    def __init__(self, config):
        self.config = config
        self.tracker = 'MB'
        self.source_flag = 'Malayabits'
        self.search_url = 'https://malayabits.cc/api/torrents/filter'
        self.upload_url = 'https://malayabits.cc/api/torrents/upload'
        self.torrent_url = 'https://malayabits.cc/api/torrents/'
        self.signature = "\n[center][url=https://github.com/Audionut/Upload-Assistant]Created by Audionut's Upload Assistant[/url][/center]"
        self.banned_groups = []
        pass

    async def upload(self, meta, disctype):
        common = COMMON(config=self.config)
        await common.edit_torrent(meta, self.tracker, self.source_flag)
        await common.unit3d_edit_desc(meta, self.tracker, self.signature, comparison=True)
        cat_id = await self.get_cat_id(meta['category'])
        type_id = await self.get_type_id(meta['type'])
        resolution_id = await self.get_res_id(meta['resolution'])
        modq = await self.get_flag(meta, 'modq')
        name = await self.edit_name(meta)
        region_id = await common.unit3d_region_ids(meta.get('region'))
        distributor_id = await common.unit3d_distributor_ids(meta.get('distributor'))
        if meta['anon'] == 0 and not self.config['TRACKERS'][self.tracker].get('anon', False):
            anon = 0
        else:
            anon = 1
        if meta['bdinfo'] is not None:
            mi_dump = None
            bd_dump = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/BD_SUMMARY_00.txt", 'r', encoding='utf-8').read()
        else:
            mi_dump = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/MEDIAINFO.txt", 'r', encoding='utf-8').read()
            bd_dump = None
        desc = open(f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}]DESCRIPTION.txt", 'r', encoding='utf-8').read()
        torrent_file_path = f"{meta['base_dir']}/tmp/{meta['uuid']}/[{self.tracker}].torrent"
        open_torrent = open(torrent_file_path, 'rb')
        files = {'torrent': open_torrent}
        base_dir = meta['base_dir']
        uuid = meta['uuid']
        specified_dir_path = os.path.join(base_dir, "tmp", uuid, "*.nfo")
        bhd_dir_path = os.path.join(base_dir, "tmp", uuid, "bhd.nfo")
        bhd_files = glob.glob(bhd_dir_path)
        nfo_files = glob.glob(specified_dir_path)
        nfo_file = None
        if nfo_files and not bhd_files:
            nfo_file = open(nfo_files[0], 'rb')
        if nfo_file:
            files['nfo'] = ("nfo_file.nfo", nfo_file, "text/plain")
        data = {
            'name': name,
            'description': desc,
            'mediainfo': mi_dump,
            'bdinfo': bd_dump,
            'category_id': cat_id,
            'type_id': type_id,
            'resolution_id': resolution_id,
            'tmdb': meta['tmdb'],
            'imdb': meta['imdb'],
            'tvdb': meta['tvdb_id'],
            'mal': meta['mal_id'],
            'igdb': 0,
            'anonymous': anon,
            'stream': meta['stream'],
            'sd': meta['sd'],
            'keywords': meta['keywords'],
            'personal_release': int(meta.get('personalrelease', False)),
            'internal': 0,
            'featured': 0,
            'free': 0,
            'doubleup': 0,
            'sticky': 0,
            'mod_queue_opt_in': modq,
        }
        headers = {
            'User-Agent': f'Upload Assistant/2.2 ({platform.system()} {platform.release()})'
        }
        params = {
            'api_token': self.config['TRACKERS'][self.tracker]['api_key'].strip()
        }

        # Internal
        if self.config['TRACKERS'][self.tracker].get('internal', False) is True:
            if meta['tag'] != "" and (meta['tag'][1:] in self.config['TRACKERS'][self.tracker].get('internal_groups', [])):
                data['internal'] = 1
        if meta.get('freeleech', 0) != 0:
            data['free'] = meta.get('freeleech', 0)
        if region_id != 0:
            data['region_id'] = region_id
        if distributor_id != 0:
            data['distributor_id'] = distributor_id
        if meta.get('category') == "TV":
            data['season_number'] = meta.get('season_int', '0')
            data['episode_number'] = meta.get('episode_int', '0')
        if meta['debug'] is False:
            response = requests.post(url=self.upload_url, files=files, data=data, headers=headers, params=params)
            try:
                console.print(response.json())
                # adding torrent link to comment of torrent file
                t_id = response.json()['data'].split(".")[1].split("/")[3]
                await common.add_tracker_torrent(meta, self.tracker, self.source_flag, self.config['TRACKERS'][self.tracker].get('announce_url'), "https://malayabits.cc/torrents/" + t_id)
            except Exception:
                console.print("It may have uploaded, go check")
                return
        else:
            console.print("[cyan]Request Data:")
            console.print(data)
        open_torrent.close()

    async def get_flag(self, meta, flag_name):
        config_flag = self.config['TRACKERS'][self.tracker].get(flag_name)
        if config_flag is not None:
            return 1 if config_flag else 0

        return 1 if meta.get(flag_name, False) else 0

    async def edit_name(self, meta):
        malayabits_name = meta['name']
        media_info_tracks = meta.get('media_info_tracks', [])  # noqa #F841
        resolution = meta.get('resolution')
        video_codec = meta.get('video_codec')
        video_encode = meta.get('video_encode')
        name_type = meta.get('type', "")
        source = meta.get('source', "")

        if not meta['is_disc']:

            def has_english_audio(tracks=None, media_info_text=None):
                if media_info_text:
                    audio_section = re.findall(r'Audio[\s\S]+?Language\s+:\s+(\w+)', media_info_text)
                    for i, language in enumerate(audio_section):
                        language = language.lower().strip()
                        if language.lower().startswith('en'):
                            title_match = re.findall(r'Audio[\s\S]+?Title\s+:\s+(.+)', media_info_text)
                            # Check if title_match has enough elements to access index i
                            if title_match and len(title_match) > i and "commentary" in title_match[i].lower():
                                continue
                            return True
                return False

            def get_audio_lang(tracks=None, is_bdmv=False, media_info_text=None):
                if media_info_text:
                    match = re.search(r'Audio[\s\S]+?Language\s+:\s+(\w+)', media_info_text)
                    if match:
                        return match.group(1).upper()
                return ""

            try:
                media_info_path = f"{meta['base_dir']}/tmp/{meta['uuid']}/MEDIAINFO.txt"
                with open(media_info_path, 'r', encoding='utf-8') as f:
                    media_info_text = f.read()

                if not has_english_audio(media_info_text=media_info_text):
                    audio_lang = get_audio_lang(media_info_text=media_info_text)
                    if audio_lang:
                        if (name_type == "REMUX" and source in ("PAL DVD", "NTSC DVD", "DVD")):
                            malayabits_name = malayabits_name.replace(str(meta['year']), f"{meta['year']} {audio_lang}", 1)
                        else:
                            malayabits_name = malayabits_name.replace(meta['resolution'], f"{audio_lang} {meta['resolution']}", 1)
            except (FileNotFoundError, KeyError) as e:
                print(f"Error processing MEDIAINFO.txt: {e}")

        if name_type == "DVDRIP":
            malayabits_name = malayabits_name.replace(f"{meta['source']}{meta['video_encode']}", f"{meta['source']}", 1)
            malayabits_name = malayabits_name.replace(f"{meta['source']}", f"{resolution} {meta['source']}", 1)
            malayabits_name = malayabits_name.replace((meta['audio']), f"{meta['audio']}{video_encode}", 1)

        elif meta['is_disc'] == "DVD" or (name_type == "REMUX" and source in ("PAL DVD", "NTSC DVD", "DVD")):
            malayabits_name = malayabits_name.replace((meta['source']), f"{resolution} {meta['source']}", 1)
            malayabits_name = malayabits_name.replace((meta['audio']), f"{video_codec} {meta['audio']}", 1)

        return malayabits_name

    async def get_cat_id(self, category_name):
        category_id = {
            'MOVIE': '1',
            'TV': '2',
            'Musik': '3',
        }.get(category_name, '0')
        return category_id

    async def get_type_id(self, type=None, reverse=False):
        type_mapping = {
            'DISC': '1', 
            'REMUX': '2',
            'WEBDL': '4', 
            'WEBRIP': '5', 
            'HDTV': '6',
            'ENCODE': '3',
            'FLAC': '7',
            'MP3': '8',
        }

        if reverse:
            # Return a reverse mapping of type IDs to type names
            return {v: k for k, v in type_mapping.items()}
        elif type is not None:
            # Return the specific type ID
            return type_mapping.get(type, '0')
        else:
            # Return the full mapping
            return type_mapping

    async def get_res_id(self, resolution=None, reverse=False):
        resolution_mapping = {
            '8640p': '10',
            '4320p': '1',
            '2160p': '2',
            '1440p': '3',
            '1080p': '3',
            '1080i': '4',
            '720p': '5',
            '576p': '6',
            '576i': '7',
            '480p': '8',
            '480i': '9',
        }

        if reverse:
            # Return reverse mapping of IDs to resolutions
            return {v: k for k, v in resolution_mapping.items()}
        elif resolution is not None:
            # Return the ID for the given resolution
            return resolution_mapping.get(resolution, '10')  # Default to '10' for unknown resolutions
        else:
            # Return the full mapping
            return resolution_mapping

    async def search_existing(self, meta, disctype):
        dupes = []
        console.print("[yellow]Searching for existing torrents on Malayabits...")
        params = {
            'api_token': self.config['TRACKERS'][self.tracker]['api_key'].strip(),
            'tmdbId': meta['tmdb'],
            'categories[]': await self.get_cat_id(meta['category']),
            'name': ""
        }
        if not meta.get('sd'):
            params['resolutions[]'] = await self.get_res_id(meta['resolution'])
            params['types[]'] = await self.get_type_id(meta['type'])
        if meta['category'] == 'TV':
            params['name'] = params['name'] + f" {meta.get('season', '')}"
        if meta.get('edition', "") != "":
            params['name'] = params['name'] + f" {meta['edition']}"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url=self.search_url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    for each in data['data']:
                        result = {
                            'name': each['attributes']['name'],
                            'size': each['attributes']['size']
                        }
                        dupes.append(result)
                else:
                    console.print(f"[bold red]Failed to search torrents. HTTP Status: {response.status_code}")
        except httpx.TimeoutException:
            console.print("[bold red]Request timed out after 5 seconds")
        except httpx.RequestError as e:
            console.print(f"[bold red]Unable to search for existing torrents: {e}")
        except Exception as e:
            console.print(f"[bold red]Unexpected error: {e}")
            await asyncio.sleep(5)

        return dupes
