"""This module hosts classes and functions related to downloading artifacts."""

from pathlib import Path

import aiohttp
import yarl


class DownloadData:

    __slots__ = ('url', 'dest', 'headers', 'params')

    def __init__(self, url, dest, headers=None, params=None):
        """"""
        self.url = url
        self.dest = dest
        if not headers:
            self.headers = []
        if not params:
            self.params = []

    def dict(self):
        """"""
        return {
            'url': self.url,
            'dest': self.dest,
            'headers': self.headers,
            'params': self.params,
        }


class DownloadManager:
    """"""

    __slots__ = ('_downloads', '_downloaders')

    def __init__(self, downloads):
        """"""
        self._downloads = downloads
        self._downloaders = []

    def initialize(self):
        """"""
        for download in self._downloads:
            if not isinstance(download, DownloadData):
                raise TypeError(f'Must be DownloadData class, not {type(download)}')
            self._downloaders.append(Downloader(**download.dict()))

    async def start(self):
        """"""
        async with aiohttp.ClientSession() as session:
            for downloader in self._downloaders:
                await downloader.fetch(session)


class Downloader:
    """"""

    __slots__ = ('url', 'dest', '_size', '_progress', 'headers', 'params', 'filename')

    def __init__(self, url, dest, headers=None, params=None):
        """"""
        self.url = yarl.URL(url)
        self.dest = Path(dest)
        self._size = 0
        self._progress = 0
        if not headers:
            self.headers = {}
        if not params:
            self.params = {}
        self.filename = self.url.name

    @property
    def size(self):
        """"""
        return self._size

    @property
    def progress(self):
        """"""
        return self._progress

    async def fetch(self, session):
        """

        :param aiohttp.ClientSession session:
        :return:
        """
        async with session.get(self.url, headers=self.headers, params=self.params) as response:
            self._size = response.content_length
            with open(self.filename, 'wb') as f:
                async for chunk in response.content.iter_chunked(2048):
                    written = f.write(chunk)
                    self._progress += written
