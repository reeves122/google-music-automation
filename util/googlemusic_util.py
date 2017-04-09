#!/usr/bin/env python
from gmusicapi import Mobileclient
import json
import os
import sys
import smtplib
import pylast
import time
import random
import operator
import csv
from time import sleep
import itertools
from datetime import datetime, timedelta

# This class is a collection of useful methods for dealing with the unofficial
# Google Music python API. (https://github.com/simon-weber/gmusicapi)
#
# Usage:
# 1. Export environment variables for your Google username and password
#    (the password should be a app-specific generated using google settings)
#    export USERNAME=bob
#    export PASSWORD=password123
#
# 2. Create your python script, import the module, and then create a instance
#    of the class. For example, to dump your library to json:
#
#    from googlemusic_util import GoogleMusic_Util
#    util = GoogleMusic_Util()
#    util.DumpLibrary('library.json')
#
# Notes:
# Warning: When you log in with this utility, it registers your computer as an
#          authorized device. You can only deregister 4 devices per year
#          according to Google's policy.


class GoogleMusic_Util(object):

    def __init__(self):
        try:
            google_username = os.environ.get('USERNAME')
            google_password = os.environ.get('PASSWORD')

            api = Mobileclient()
            api.login(google_username, google_password, Mobileclient.FROM_MAC_ADDRESS)
            if api.is_authenticated():
                self.api = api
        except:
            print "ERROR: Unable to login with the credentials provided!"
            sys.exit(1)

    def AddSongsToPlaylist(self, playlist_name, list_of_songs):
        # Dont continue if new list is empty
        if len(list_of_songs) < 1:
            print 'ERROR: No songs to add!'
            return False

        # Dont continue if new list contains too many songs
        if len(list_of_songs) > 1000:
            print 'ERROR: List contains more than 1000 songs!'
            return False

        # Get a list of all the user's playlists
        all_playlists = self.api.get_all_playlists()

        # Search for the one to delete
        for playlist in all_playlists:
            if playlist['name'] == playlist_name:
                print 'Deleting old playlist', playlist['name']
                self.api.delete_playlist(playlist['id'])

        # Create a new playlist
        playlist_id = self.api.create_playlist(playlist_name)
        self.api.add_songs_to_playlist(playlist_id, list_of_songs)
        return True

    def LoadLocalLibrary(self, file_name):
        # Open library from previous run json file
        try:
            with open(file_name) as f:
                library = []
                for line in f:
                    library.append(json.loads(line))
            print len(library), 'tracks detected.'
            return library
        except:
            print "ERROR: Unable to load local library file!"

    def GetLibrary(self):
        print "Getting library..."
        library = self.api.get_all_songs()
        print len(library), 'tracks detected.'
        print
        return library

    def DumpLibrary(self, file_name):
        print "Getting library..."
        library = self.api.get_all_songs()
        print len(library), 'tracks detected.'
        print
        print "Dumping tracks to JSON..."
        try:
            with open(file_name, 'wb') as fp:
                for track in library:
                    json.dump(track, fp)
                    fp.write('\n')
        except:
            print "ERROR: Unable to dump library to JSON file!"
        print "done!"
        print

    def DumpPlaylists(self, file_name):
        # Get all playlists including tracks in each
        print "Getting list of playlists..."
        all_playlists = self.api.get_all_user_playlist_contents()
        print len(all_playlists), 'playlists detected.'
        print
        print "Dumping playlists to JSON..."
        try:
            with open(file_name, 'wb') as fp:
                json.dump(all_playlists, fp)
                fp.write('\n')
        except:
            print "ERROR: Unable to dump library to JSON file!"

        print "Done!"
        print

    def FilterForUnplayed(self, library):
        # Returns library of unplayed songs
        unplayed_songs = []
        for track in library:
            if 'playCount' not in track.keys():
                unplayed_songs.append(track)

        print len(unplayed_songs), 'unplayed songs.'
        return unplayed_songs

    def FilterForPlayed(self, library):
        # Returns library of played songs
        played_songs = []
        for track in library:
            if 'playCount' in track.keys():
                played_songs.append(track)

        print len(played_songs), 'played songs.'
        return played_songs

    def SendEmail(self, from_address, to_address, body):
        try:
            smtpObj = smtplib.SMTP('localhost')
            smtpObj.sendmail(from_address, to_address, body)
            print "Successfully sent email"
        except:
            print "Error: unable to send email"

    def FindNewPlays(self, old_library, new_library):
        # This returns a list of track dictionaries which have been played in
        # the time between old_library and new_library
        print "Scanning library for new plays. This may take some time..."
        # Compare each entry of current library against old library.
        # Add new track plays to list
        new_plays = []
        for new_track in new_library:
            for old_track in old_library:
                try:
                    # For each track in the old library, look for a match
                    # in the old library
                    if new_track['id'] == old_track['id']:
                        # If a match is found, check if the playcount is higher
                        # now. First check if the playcount key even exists in
                        # new and old tracks. If the track has never been
                        # played then the key will not exist.
                        if 'playCount' in new_track.keys() \
                          and 'playCount' in old_track.keys():
                            if new_track['playCount'] > old_track['playCount']:
                                print "Found new track play:", new_track['artist'], '-', new_track['title']
                                # Add track to scrobble list
                                new_plays.append(new_track)
                        elif 'playCount' in new_track.keys() and 'playCount' not in old_track.keys():
                            # This means the track has been played for the
                            # first time and playCount key was created.
                            print "Found new track play:", new_track['artist'], '-', new_track['title']
                            # Add track to scrobble list
                            new_plays.append(new_track)
                        break  # Break out to for loop
                except:
                    continue
            else:
                try:
                    # If no matches are found in old library it must be new
                    # print "Newly added track found"
                    if 'playCount' in new_track.keys() and new_track['playCount'] > 0:
                        print "Found new track play:", new_track['artist'], '-', new_track['title']
                        new_plays.append(new_track)
                except:
                    continue

        print len(new_plays).__str__() + ' new plays found!'
        print
        return new_plays

    def ScrobbleTrack(self, track):
        try:
            lastfm_username = os.environ.get('LASTFM_USERNAME')
            lastfm_password = pylast.md5(os.environ.get('LASTFM_PASSWORD'))
            lastfm_apikey = os.environ.get('LASTFM_APIKEY')
            lastfm_apisecret = os.environ.get('LASTFM_APISECRET')

            lastfm = pylast.LastFMNetwork(api_key=lastfm_apikey,
                                          api_secret=lastfm_apisecret,
                                          username=lastfm_username,
                                          password_hash=lastfm_password)

            # Get last modified time of track (which seems to be last played)
            # Divide by 1,000,000 to get unix timestamp in seconds
            time_played = (int(track['lastModifiedTimestamp']) / 1000000)
            print 'Scrobbling track:', \
                track['artist'], '-', \
                track['title'], '-', \
                datetime.datetime.fromtimestamp(float(time_played))

            lastfm.scrobble(artist=track['artist'],
                            title=track['title'],
                            timestamp=time_played)

            time.sleep(1)
        except:
            print "There was a problem scrobbling the track."
    def UpdateLastPlayedDB(self, track):
        # Accepts one track (which is a new play) and updates the LastPlayed file.
        file_name = 'last_played.json'
        items = {}
        # Open tracks from previous run json file
        with open(file_name) as f:
                items = json.load(f)

        # Add current track to DB
        items[track['id']] = time.time()

        # Write out JSON file
        with open(file_name, 'wb') as fp:
            json.dump(items, fp)
            fp.write('\n')

        print "Wrote " + len(items).__str__() + " total tracks to " + file_name

    def LoadLastPlayedDB(self, library):
        # Loads the last_played DB and overlays it on the library
        file_name = 'last_played.json'
        items = {}
        tracks_appended = 0
        # Open tracks from previous run json file
        with open(file_name) as f:
                items = json.load(f)

        for track in library:
            if track['id'] in items:
                track['lastPlayed'] = items[track['id']]
                tracks_appended += 1
            else:
                track['lastPlayed'] = 0.0

        print "Last Played info retrieved for",tracks_appended,"tracks."
        return library
