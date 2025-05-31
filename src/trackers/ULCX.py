# -*- coding: utf-8 -*-
# import discord
import asyncio
import requests
import platform
import os
import glob
import httpx
import cli_ui
from src.trackers.COMMON import COMMON
from src.console import console
from src.dupe_checking import check_for_english


class ULCX():

    def __init__(self, config):
        self.config = config
        self.tracker = 'ULCX'
        self.source_flag = 'ULCX'
        self.upload_url = 'https://upload.cx/api/torrents/upload'
        self.search_url = 'https://upload.cx/api/torrents/filter'
        self.torrent_url = 'https://upload.cx/api/torrents/'
        self.signature = "\n[center][url=https://github.com/Audionut/Upload-Assistant]Created by Audionut's Upload Assistant[/url][/center]"
        self.banned_groups = ['Tigole', 'x0r', 'Judas', 'SPDVD', 'MeGusta', 'YIFY', 'SWTYBLZ', 'TAoE', 'TSP', 'TSPxL', 'LAMA', '4K4U',
                              'ION10', 'Will1869', 'TGx', 'Sicario', 'QxR', 'Hi10', 'EMBER', 'FGT', 'AROMA', 'd3g', 'nikt0', 'Grym',
                              'RARBG', 'iVy', 'FnP', 'EDGE2020', 'NuBz', 'NAHOM', 'Ralphy']
        pass

    async def get_cat_id(self, category_name):
        category_id = {
            'MOVIE': '1',
            'TV': '2',
        }.get(category_name, '0')
        return category_id

    async def get_type_id(self, type):
        type_id = {
            'DISC': '1',
            'REMUX': '2',
            'WEBDL': '4',
            'WEBRIP': '5',
            'HDTV': '6',
            'ENCODE': '3'
        }.get(type, '0')
        return type_id

    async def get_res_id(self, resolution, type):
        resolution_id = {
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
            '480i': '9'
        }.get(resolution, '10')
        return resolution_id

    async def upload(self, meta, disctype):
        common = COMMON(config=self.config)
        await common.edit_torrent(meta, self.tracker, self.source_flag)
        cat_id = await self.get_cat_id(meta['category'])
        modq = await self.get_flag(meta, 'modq')
        type_id = await self.get_type_id(meta['type'])
        resolution_id = await self.get_res_id(meta['resolution'], meta['type'])
        await common.unit3d_edit_desc(meta, self.tracker, self.signature, comparison=True)
        region_id = await common.unit3d_region_ids(meta.get('region'))
        distributor_id = await common.unit3d_distributor_ids(meta.get('distributor'))
        name, region_id, distributor_id = await self.edit_name(meta, region_id, distributor_id)
        if region_id == "SKIPPED" or distributor_id == "SKIPPED":
            console.print("Region or Distributor ID not found; skipping ULCX upload.")
            return
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
        nfo_files = glob.glob(specified_dir_path)
        nfo_file = None
        if nfo_files:
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
            'mod_queue_opt_in': modq,
            'sticky': 0,
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
        headers = {
            'User-Agent': f'Upload Assistant/2.2 ({platform.system()} {platform.release()})'
        }
        params = {
            'api_token': self.config['TRACKERS'][self.tracker]['api_key'].strip()
        }

        if meta['debug'] is False:
            response = requests.post(url=self.upload_url, files=files, data=data, headers=headers, params=params)
            try:
                console.print(response.json())
                # adding torrent link to comment of torrent file
                t_id = response.json()['data'].split(".")[1].split("/")[3]
                await common.add_tracker_torrent(meta, self.tracker, self.source_flag, self.config['TRACKERS'][self.tracker].get('announce_url'), "https://upload.cx/torrents/" + t_id)
            except Exception:
                console.print("It may have uploaded, go check")
                return
        else:
            console.print("[cyan]Request Data:")
            console.print(data)
        open_torrent.close()

    async def edit_name(self, meta, region_id, distributor_id):
        common = COMMON(config=self.config)
        ulcx_name = meta['name']
        if meta['category'] == 'TV':
            ulcx_name = ulcx_name.replace(f"{meta['title']} {meta['year']}", f"{meta['title']}", 1)
        else:
            ulcx_name = ulcx_name
        if meta.get('is_disc') == "BDMV":
            if not region_id:
                if not meta['unattended'] or (meta['unattended'] and meta.get('unattended-confirm', False)):
                    region_name = cli_ui.ask_string("ULCX: Region code not found for disc. Please enter it manually (UPPERCASE): ")
                    region_id = await common.unit3d_region_ids(region_name)
                    if not meta.get('edition', ""):
                        ulcx_name = ulcx_name.replace(f"{meta['resolution']}", f"{meta['resolution']} {region_name}", 1)
                    else:
                        ulcx_name = ulcx_name.replace(f"{meta['resolution']} {meta['edition']}", f"{meta['resolution']} {meta['edition']} {region_name}", 1)
                else:
                    region_id = "SKIPPED"
            if not distributor_id:
                if not meta['unattended'] or (meta['unattended'] and meta.get('unattended-confirm', False)):
                    distributor_name = cli_ui.ask_string("ULCX: Distributor code not found for disc. Please enter it manually (UPPERCASE): ")
                    distributor_id = await common.unit3d_distributor_ids(distributor_name)
                else:
                    distributor_id = "SKIPPED"

        return ulcx_name, region_id, distributor_id

    async def get_flag(self, meta, flag_name):
        config_flag = self.config['TRACKERS'][self.tracker].get(flag_name)
        if config_flag is not None:
            return 1 if config_flag else 0

        return 1 if meta.get(flag_name, False) else 0

    async def search_existing(self, meta, disctype):
        if 'concert' in meta['keywords']:
            console.print('[bold red]Concerts not allowed at ULCX.')
            if not meta['unattended'] or (meta['unattended'] and meta.get('unattended-confirm', False)):
                if cli_ui.ask_yes_no("Do you want to upload anyway?", default=False):
                    pass
                else:
                    meta['skipping'] = "ULCX"
                    return
            else:
                meta['skipping'] = "ULCX"
                return
        if meta['video_codec'] == "HEVC" and meta['resolution'] != "2160p" and 'animation' not in meta['keywords'] and meta.get('anime', False) is not True:
            console.print('[bold red]This content might not fit HEVC rules for ULCX.')
            if not meta['unattended'] or (meta['unattended'] and meta.get('unattended-confirm', False)):
                if cli_ui.ask_yes_no("Do you want to upload anyway?", default=False):
                    pass
                else:
                    meta['skipping'] = "ULCX"
                    return
            else:
                meta['skipping'] = "ULCX"
                return
        if meta['type'] == "ENCODE" and meta['resolution'] not in ['8640p', '4320p', '2160p', '1440p', '1080p', '1080i', '720p']:
            console.print('[bold red]Encodes must be at least 720p resolution for ULCX.')
            meta['skipping'] = "ULCX"
            return

        tracker = self.tracker
        await check_for_english(meta, tracker)

        dupes = []
        console.print("[yellow]Searching for existing torrents on ULCX...")
        params = {
            'api_token': self.config['TRACKERS'][self.tracker]['api_key'].strip(),
            'tmdbId': meta['tmdb'],
            'categories[]': await self.get_cat_id(meta['category']),
            'types[]': await self.get_type_id(meta['type']),
            'resolutions[]': await self.get_res_id(meta['resolution'], meta['type']),
            'name': ""
        }
        if meta['category'] == 'TV':
            params['name'] = params['name'] + f" {meta.get('season', '')}"
        if meta.get('edition', "") != "":
            params['name'] = params['name'] + f" {meta['edition']}"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url=self.search_url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    for each in data['data']:
                        attributes = each['attributes']
                        if not meta['is_disc']:
                            result = {
                                'name': attributes['name'],
                                'size': attributes['size'],
                                'files': [file['name'] for file in attributes.get('files', []) if isinstance(file, dict) and 'name' in file],
                                'file_count': len(attributes.get('files', [])) if isinstance(attributes.get('files'), list) else 0
                            }
                        else:
                            result = {
                                'name': attributes['name'],
                                'size': attributes['size']
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
