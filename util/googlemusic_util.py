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

    def __init__(self, login=True, dry_run=False):
        if login:
            try:
                google_username = os.environ.get('USERNAME')
                google_password = os.environ.get('PASSWORD')

                api = Mobileclient()
                api.login(google_username, google_password,
                          Mobileclient.FROM_MAC_ADDRESS)
                if api.is_authenticated():
                    self.api = api
            except:
                print "ERROR: Unable to login with the credentials provided!"
                sys.exit(1)
        if dry_run:
            print "Dry-run mode enabled. Logging only. No changes will be made."
            self.dry_run = True
        else:
            self.dry_run = False

    def AddSongsToPlaylist(self, playlists, playlist_name, list_of_songs, batch_size=100):
        # Dont continue if new list is empty
        if len(list_of_songs) < 1:
            print 'ERROR: No songs to add!'
            return False

        # Dont continue if new list contains too many songs
        if len(list_of_songs) > 1000:
            print 'ERROR: List contains more than 1000 songs!'
            return False

        # Get the ID of the playlist if it already exists
        playlist_id = self.GetPlaylistID(playlists, playlist_name)
        if playlist_id is False:
            if self.dry_run:
                print "DRY-RUN: Would create playlist", playlist_name
            else:
                # Create a new playlist
                playlist_id = self.api.create_playlist(playlist_name)
                print "Created new playlist:", playlist_name
            existing_tracks = [] # empty
        else:
            # Remove tracks from existing playlist if needed
            existing_tracks = self.GetTracksInPlaylist(playlists, playlist_name)
            tracks_to_remove = []
            if len(existing_tracks) > 0:
                for track in existing_tracks:
                    if track['trackId'] not in list_of_songs:
                        tracks_to_remove.append(track['id'])

            if len(tracks_to_remove) > 0:
                self.RemoveTracksFromPlaylist(tracks_to_remove)

        tracks_to_add = []
        for new_track in list_of_songs:
            if any(new_track == old_track['trackId'] for old_track in existing_tracks):
                True # track already exists in playlist
            else:
                tracks_to_add.append(new_track)

        if len(tracks_to_add) > 0:
            print "Adding " + len(tracks_to_add).__str__() + " tracks to playlist..."
            if self.dry_run:
                print "DRY-RUN: Would add these songs to playlist", playlist_name
            else:
                for i in range(0, len(tracks_to_add), batch_size):
                    for retries in range(0,5):
                        try:
                            tracks_added = self.api.add_songs_to_playlist(playlist_id, tracks_to_add[i:i+batch_size])
                            #print "Successfully added " + len(tracks_added).__str__() + " tracks to playlist."
                            #sleep(0.5)
                        except:
                            print "Error adding tracks. Trying again..."
                            continue
                        break
            print "Successfully added " + len(tracks_to_add).__str__() + " tracks to playlist."
        else:
            print "No new tracks to add"
        # Update playlist description
        if not self.dry_run:
            self.api.edit_playlist(playlist_id, new_description="Synced " + time.strftime('%m/%d/%Y, %I:%M:%S %p', time.localtime()))
        return True

    def RemoveTracksFromPlaylist(self, list_of_tracks, batch_size=100):
        print "Removing " + len(list_of_tracks).__str__() + ' tracks from playlist...'
        if self.dry_run:
            print "DRY-RUN: Not removing tracks from playlist"
        else:
            for i in range(0, len(list_of_tracks), batch_size):
                for retries in range(0, 5):
                    try:
                        tracks_removed = self.api.remove_entries_from_playlist(list_of_tracks[i:i+batch_size])
                        #print len(tracks_removed).__str__() + ' tracks removed from playlist.'
                        #sleep(0.5)
                    except:
                        "Error removing tracks. Trying again..."
                        continue
                    break

        print len(list_of_tracks).__str__() + ' tracks removed from playlist.'

    def LoadLocalJSON(self, file_name):
        # Open tracks from previous run json file
        try:
            with open(file_name) as f:
                items = []
                for line in f:
                    items.append(json.loads(line))
            print len(items[0]), 'items detected in file: ' + file_name
            return items[0]
        except:
            print "ERROR: Unable to load local library file!"

    def GetLibrary(self):
        print "Getting library..."
        library = self.api.get_all_songs()
        print len(library), 'tracks detected.'
        return library

    def GetPlaylists(self):
        # Get all playlists including tracks in each
        print "Getting list of playlists..."
        all_playlists = self.api.get_all_user_playlist_contents()
        print len(all_playlists), 'playlists detected.'
        return all_playlists

    def DumpTracksToJSON(self, list_of_tracks, json_file):
        try:
            with open(json_file, 'wb') as fp:
                json.dump(list_of_tracks, fp)
                fp.write('\n')
        except:
            print "ERROR: Unable to dump library to JSON file!"

        print "Wrote " + len(list_of_tracks).__str__() + " total tracks to " + json_file

    def DumpTracksToCSV(self, list_of_tracks, csv_file):
        # print "Opening CSV for writing..."
        # Open CSV file
        f = open(csv_file, 'wt')

        # Write header row
        writer = csv.writer(f, delimiter=',')
        writer.writerow(('Artist', 'Album', 'Title', 'Genre', 'Plays', 'Rating', 'Last Played'))

        # Write each track to CSV
        for track in list_of_tracks:

            # Not all fields may be present and usable
            try:
                artist = (track['artist']).encode('utf-8')
            except:
                artist = ''

            try:
                album = (track['album']).encode('utf-8')
            except:
                album = ''

            try:
                title = (track['title']).encode('utf-8')
            except:
                title = ''

            try:
                genre = (track['genre']).encode('utf-8')
            except:
                genre = ''

            try:
                plays = track['playCount']
            except:
                plays = ''

            try:
                rating = track['rating']
            except:
                rating = ''

            try:
                lastPlayed = (track['lastPlayed']).encode('utf-8')
            except:
                lastPlayed = ''


            writer.writerow((artist, album, title, genre, plays, rating, lastPlayed))

        f.close()
        print "Wrote " + len(list_of_tracks).__str__() + " total tracks to " + csv_file
        # print

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
                        # played then the key may not exist.
                        if 'playCount' in new_track.keys() and 'playCount' in old_track.keys():
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

        print len(new_plays).__str__() + ' new plays found.'
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
                datetime.fromtimestamp(float(time_played))

            lastfm.scrobble(artist=track['artist'],
                            title=track['title'],
                            timestamp=time_played)

            time.sleep(0.5)
        except:
            print "There was a problem scrobbling the track."

    def SetPlayCount(self, track, new_plays):
        if track['playCount'] < new_plays:
            increment_count = new_plays - track['playCount']
            print "incrementing play count by " + increment_count.__str__()
            if self.dry_run:
                print "DRY-RUN: Would increment playcount of", track['artist'] + '-' + track['album'] + '-' + track['title']
            else:
                self.api.increment_song_playcount(track['id'], plays=increment_count)
                time.sleep(0.5)  # Throttle calls to Google API
        else:
            print "Error: Current plays is higher than value provided!"

    def GetLastFMPlays(self, track):
        try:
            lastfm_username = os.environ.get('LASTFM_USERNAME')
            lastfm_password = pylast.md5(os.environ.get('LASTFM_PASSWORD'))
            lastfm_apikey = os.environ.get('LASTFM_APIKEY')
            lastfm_apisecret = os.environ.get('LASTFM_APISECRET')

            lastfm = pylast.LastFMNetwork(api_key=lastfm_apikey,
                                          api_secret=lastfm_apisecret,
                                          username=lastfm_username,
                                          password_hash=lastfm_password)

            lastfm_track = pylast.Track(artist=track['artist'],
                                        title=track['title'],
                                        network=lastfm,
                                        username=lastfm_username)

            time.sleep(0.5)
            return lastfm_track.get_userplaycount()
        except:
            print "There was a problem connecting to Last.FM."

    def SyncLastFMPlayCount(self, library):
        index = 1
        for track in library:
            try:
                # If the playCount key doesnt exist for this track, set it to 0
                if 'playCount' not in track.keys():
                    track['playCount'] = 0

                # Query Last.FM for the user's play count of this track
                lastfm_plays = self.GetLastFMPlays(track)

                # Debugging information
                print index.__str__() + "/" + len(library).__str__() + " Last.fm: " + lastfm_plays.__str__() + \
                      ", Google: " + track['playCount'].__str__() + ", " + track['artist'] \
                      + ' - ' + track['album'] + ' - ' + track['title']

                # If the Last.FM play count is higher, increment the Google music play count
                if lastfm_plays > track['playCount']:
                    self.SetPlayCount(track, lastfm_plays)

                # If the Google Music play count is higher, scrobble the track to Last.FM
                if track['playCount'] > lastfm_plays:
                    self.ScrobbleTrack(track)

                index += 1
            except:
                print index.__str__() + "/" + len(library).__str__() + " ERROR"
                continue

    def ScrobbleRecentPlays(self, library):
        previous_scrobbles = []
        try:
            # Load list of previous scrobbles (in epochs)
            with open('previous_scrobbles.txt') as f:
                previous_scrobbles = f.read().splitlines()
                print "Previous scrobbles:", len(previous_scrobbles)
                f.close()
        except:
            print

        days_ago = 14
        # Get epoch time from N days ago
        start_time_window = time.mktime((datetime.now() - timedelta(days=days_ago)).timetuple())

        new_scrobbles = []

        for track in library:
            time_played = (int(track['lastModifiedTimestamp']) / 1000000)
            if time_played > start_time_window:
                if time_played.__str__() not in previous_scrobbles:
                    print 'Scrobbling track:', \
                        track['artist'], '-', \
                        track['title'], '-', \
                        datetime.fromtimestamp(float(time_played))
                    self.ScrobbleTrack(track)
                    new_scrobbles.append(time_played.__str__())

        # Write out new scrobbles to log
        print "New scrobbles: ", len(new_scrobbles).__str__()
        with open('previous_scrobbles.txt', 'a') as f:
            for item in new_scrobbles:
                f.write("%s\n" % item)

    def GetPlaylistID(self, list_of_playlists, playlist_name):
        for playlist in list_of_playlists:
            #print playlist['name']
            if playlist['name'] == playlist_name:
                return playlist['id']
        print "Playlist not found: " + playlist_name
        return False

    def GetTracksInPlaylist(self, list_of_playlists, playlist_name):
        list_of_tracks = []
        for playlist in list_of_playlists:
            if playlist['name'] == playlist_name:
                for track in playlist['tracks']:
                    list_of_tracks.append(track)
        print "Found " + len(list_of_tracks).__str__() + " tracks in existing playlist: " + playlist_name
        return list_of_tracks

    def LeastPlayed(self, library, playlists, number_of_tracks=1000):
        print "Creating playlist of least played thumbs up tracks"
        least_played_tracks = []
        library.sort(key=operator.itemgetter('id'))
        library.sort(key=operator.itemgetter('playCount'))
        for track in library:
            if 'rating' in track.keys():
                if track['rating'] == '4' or track['rating'] == '5':  # 4-5 stars is thumbs up
                    if len(least_played_tracks) < number_of_tracks:
                        if self.dry_run:
                            print 'Plays:', track['playCount'], ' - ', \
                                            track['artist'].encode('utf-8'), ' - ', \
                                            track['title'].encode('utf-8'), ' - ', \
                                            datetime.fromtimestamp(float(track['lastPlayed']))
                        least_played_tracks.append(track['id'])
                    else:
                        break

        # Call function to add songs to playlist
        if self.AddSongsToPlaylist(playlists, 'Thumbs Up Least Played', least_played_tracks):
            print "Done!"
        else:
            print "Failed!"

    def NotRecentlyPlayed(self, library, playlists, number_of_tracks=1000, excluded_genres=None):
        library.sort(key=operator.itemgetter('id'))
        library.sort(key=operator.itemgetter('lastPlayed'))
        not_recently_played = []
        for track in library:
            if 'rating' in track.keys():
                if track['rating'] == '4' or track['rating'] == '5':  # 4-5 stars is thumbs up
                    if excluded_genres is not None:
                        if track['genre'] not in excluded_genres:
                            if len(not_recently_played) < number_of_tracks:
                                if self.dry_run:
                                    print 'Plays:', track['playCount'], ' - ', \
                                                    track['artist'].encode('utf-8'), ' - ', \
                                                    track['title'].encode('utf-8'), ' - ', \
                                                    datetime.fromtimestamp(float(track['lastPlayed']))
                                not_recently_played.append(track['id'])
                            else:
                                break
                    else:
                        if len(not_recently_played) < number_of_tracks:
                            not_recently_played.append(track['id'])
                        else:
                            break

        # Call function to add songs to playlist
        if self.AddSongsToPlaylist(playlists, 'Thumbs Up Not Recently Played', not_recently_played):
            print "Done!"
        else:
            print "Failed!"

    def LeastPlayedByGenre(self, library, playlists, genre, number_of_tracks=1000):
        print "Creating playlist of least played tracks in genre: " + genre
        genre_tracks = []
        for track in library:
            if track['genre'] == genre:
                genre_tracks.append(track)

        print "Found " + len(genre_tracks).__str__() + " tracks in genre: " + genre
        least_played_tracks = []
        genre_tracks.sort(key=operator.itemgetter('id'))
        genre_tracks.sort(key=operator.itemgetter('playCount'))
        for track in genre_tracks:
            if 'rating' in track.keys():
                if track['rating'] == '4' or track['rating'] == '5':  # 4-5 stars is thumbs up
                    if len(least_played_tracks) < number_of_tracks:
                        if self.dry_run:
                            print 'Plays:', track['playCount'], ' - ', \
                                            track['artist'].encode('utf-8'), ' - ', \
                                            track['title'].encode('utf-8'), ' - ', \
                                            datetime.fromtimestamp(float(track['lastPlayed']))
                        least_played_tracks.append(track['id'])
                    else:
                        break
                        
        # Call function to add songs to playlist
        if self.AddSongsToPlaylist(playlists, genre + ' Least Played', least_played_tracks):
            print "Done!"
        else:
            print "Failed!"

    def MostPlayedByGenre(self, library, playlists, genre, number_of_tracks=1000):
        print "Creating playlist of most played tracks in genre: " + genre
        genre_tracks = []
        for track in library:
            if track['genre'] == genre:
                genre_tracks.append(track)

        print "Found " + len(genre_tracks).__str__() + " tracks in genre: " + genre

        most_played_tracks = []
        genre_tracks.sort(key=operator.itemgetter('id'))
        genre_tracks.sort(key=operator.itemgetter('playCount'), reverse=True)
        for track in genre_tracks:
            if 'rating' in track.keys():
                if track['rating'] == '4' or track['rating'] == '5':  # 4-5 stars is thumbs up
                    if len(most_played_tracks) < number_of_tracks:
                        if self.dry_run:
                            print 'Plays:', track['playCount'], ' - ', \
                                            track['artist'].encode('utf-8'), ' - ', \
                                            track['title'].encode('utf-8'), ' - ', \
                                            datetime.fromtimestamp(float(track['lastPlayed']))
                        most_played_tracks.append(track['id'])
                    else:
                        break

        # Call function to add songs to playlist
        if self.AddSongsToPlaylist(playlists, genre + ' Most Played', most_played_tracks):
            print "Done!"
        else:
            print "Failed!"

    def NotRecentlyPlayedByGenre(self, library, playlists, genre, number_of_tracks=1000):
        print "Creating playlist of not recently played tracks in genre: " + genre
        genre_tracks = []
        for track in library:
            if track['genre'] == genre:
                genre_tracks.append(track)

        print "Found " + len(genre_tracks).__str__() + " tracks in genre: " + genre

        genre_tracks.sort(key=operator.itemgetter('id'))
        genre_tracks.sort(key=operator.itemgetter('lastPlayed'))
        not_recently_played = []
        for track in genre_tracks:
            if 'rating' in track.keys():
                if track['rating'] == '4' or track['rating'] == '5':  # 4-5 stars is thumbs up
                    if len(not_recently_played) < number_of_tracks:
                        if self.dry_run:
                            print 'Plays:', track['playCount'], ' - ', \
                                            track['artist'].encode('utf-8'), ' - ', \
                                            track['title'].encode('utf-8'), ' - ', \
                                            datetime.fromtimestamp(float(track['lastPlayed']))
                        not_recently_played.append(track['id'])
                    else:
                        break

        # Call function to add songs to playlist
        if self.AddSongsToPlaylist(playlists, genre + ' Not Recently Played', not_recently_played):
            print "Done!"
        else:
            print "Failed!"

    def UnratedByGenre(self, library, playlists, genre, number_of_tracks=999):
        print "Creating playlist of unrated tracks in genre: " + genre
        genre_tracks = []
        for track in library:
            if track['genre'] == genre:
                genre_tracks.append(track)

        print "Found " + len(genre_tracks).__str__() + " tracks in genre: " + genre
        unrated_tracks = []
        genre_tracks.sort(key=operator.itemgetter('id'))
        genre_tracks.sort(key=operator.itemgetter('playCount'), reverse=True)
        for track in genre_tracks:
            if 'rating' in track.keys():
                if track['rating'] == '0' or track['rating'] == '3':  # 0 or 3 stars is unrated
                    if len(unrated_tracks) < number_of_tracks:
                        if self.dry_run:
                            print 'Plays:', track['playCount'], ' - ', \
                                            track['artist'].encode('utf-8'), ' - ', \
                                            track['title'].encode('utf-8'), ' - ', \
                                            datetime.fromtimestamp(float(track['lastPlayed']))
                        unrated_tracks.append(track['id'])
                    else:
                        break


        # Call function to add songs to playlist
        if self.AddSongsToPlaylist(playlists, genre + ' Unrated', unrated_tracks):
            print "Done!"
        else:
            print "Failed!"

    def UnratedPlaylist(self, library, playlists, number_of_tracks=1000):
        print "Creating playlist of most played unrated tracks"
        unrated_tracks = []
        library.sort(key=operator.itemgetter('id'))
        library.sort(key=operator.itemgetter('playCount'), reverse=True)
        for track in library:
            if 'rating' in track.keys():
                if track['rating'] == '0' or track['rating'] == '3':  # 0 or 3 stars is unrated
                    if len(unrated_tracks) < number_of_tracks:
                        if self.dry_run:
                            print 'Plays:', track['playCount'], ' - ', \
                                            track['artist'].encode('utf-8'), ' - ', \
                                            track['title'].encode('utf-8'), ' - ', \
                                            datetime.fromtimestamp(float(track['lastPlayed']))
                        unrated_tracks.append(track['id'])
                    else:
                        break

        # Call function to add songs to playlist
        if self.AddSongsToPlaylist(playlists, 'Unrated', unrated_tracks):
            print "Done!"
        else:
            print "Failed!"

    def ArtistPlaylist(self, library, playlists, artist, number_of_tracks=1000):
        print "Creating playlist of tracks by artist: " + artist
        artist_tracks = []
        for track in library:
            if track['artist'] == artist:
                artist_tracks.append(track)

        print "Found " + len(artist_tracks).__str__() + " tracks by artist: " + artist
        tracks_to_add = []
        artist_tracks.sort(key=operator.itemgetter('trackNumber'))
        try:
            # Sort by year and then album name
            artist_tracks.sort(key=operator.itemgetter('year', 'album'), reverse=True)
        except:
            # If year doesnt exist, just sort by album
            artist_tracks.sort(key=operator.itemgetter('album'), reverse=True)

        for track in artist_tracks:
            if 'rating' in track.keys():
                if track['rating'] != '1': # 1 stars is thumbs down
                    if len(tracks_to_add) < number_of_tracks:
                        if self.dry_run:
                            print 'Plays:', track['playCount'], ' - ', \
                                            track['artist'].encode('utf-8'), ' - ', \
                                            track['album'].encode('utf-8'), ' - ', \
                                             track['title'].encode('utf-8'), ' - ', \
                                            datetime.fromtimestamp(float(track['lastPlayed']))
                        tracks_to_add.append(track['id'])
                    else:
                        break

        # Call function to add songs to playlist
        if self.AddSongsToPlaylist(playlists, artist, tracks_to_add):
            print "Done!"
        else:
            print "Failed!"

    def AlbumPlaylist(self, library, playlists, name, album_names, number_of_tracks=1000):
        album_tracks = []
        for track in library:
            for album in album_names:
                # Case-insentive matching
                if album.lower() in track['album'].lower():
                    album_tracks.append(track)

        print "Found " + len(album_tracks).__str__() + " album tracks."
        tracks_to_add = []
        album_tracks.sort(key=operator.itemgetter('trackNumber'))
        album_tracks.sort(key=operator.itemgetter('year', 'album'), reverse=True)
        for track in album_tracks:
            if 'rating' in track.keys():
                if track['rating'] != '1': # 1 stars is thumbs down
                    if len(tracks_to_add) < number_of_tracks:
                        if self.dry_run:
                            print 'Plays:', track['playCount'], ' - ', \
                                            track['album'].encode('utf-8'), ' - ', \
                                            track['artist'].encode('utf-8'), ' - ', \
                                            track['title'].encode('utf-8'), ' - ', \
                                            datetime.fromtimestamp(float(track['lastPlayed']))
                        tracks_to_add.append(track['id'])
                    else:
                        break

        # Call function to add songs to playlist
        if self.AddSongsToPlaylist(playlists, name, tracks_to_add):
            print "Done!"
        else:
            print "Failed!"

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
