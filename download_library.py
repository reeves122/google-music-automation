#!/usr/bin/env python
from util.googlemusic_util import GoogleMusic_Util

if __name__ == '__main__':
    util = GoogleMusic_Util()
    util.DumpLibrary('/tmp/library.json')
    util.DumpPlaylists('/tmp/playlists.json')
