#Scrape Genius.com for samples on an album and use Spotipy to automatically create a playlist of the samples

import pandas as pd
import re
import spotipy
import spotipy.util as util
from bs4 import BeautifulSoup
import requests
import json
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

#Define Functions
def ScrapeGeniusURL(genius_url):
    r = requests.get(genius_url)
    soup = BeautifulSoup(r.content, features='html.parser')
    album_title = soup.find(class_ = 'breadcrumb breadcrumb-current_page').find(itemprop = "title").get_text()
    album_artist = soup.find(class_ = 'header_with_cover_art-primary_info-primary_artist').get_text()

    song_links = []
    for link in soup.find_all(class_ = 'u-display_block', href=True):
        song_links.append(link['href'])

    sample_data = []

    for i in range(len(song_links)):
        s = requests.get(song_links[i]) #picking specific song
        song_content = BeautifulSoup(s.content, features='html.parser')
        song_json = song_content.find(itemprop = "page_data").get('content') #convert page metadata to json
        y = json.loads(song_json)
        m = len(y['song']['song_relationships'][0]['songs'])  #indices for accessing sample artist and sample title

        for j in range(m):
            sample_data.append({'title' : re.sub("\(.*\)", "", y['song']['song_relationships'][0]['songs'][j]['title']), 'artist' : y['song']['song_relationships'][0]['songs'][j]['primary_artist']['name']})

    sample_data = pd.DataFrame(sample_data)  # dataframe with sample title and artist
    return sample_data, album_artist, album_title

def CreatePlaylist(username, album_title, album_artist):
    # Create Appropriately Titled Empty Playlist For Samples
    playlist_name = f"Samples in {album_title} by {album_artist}"
    sp.user_playlist_create(username, name=playlist_name)
    return playlist_name

def GetTrackIDs(sample_data):
    #Get Spotify track ids for samples
    track_ids = []
    for i in range(len(sample_data)):
        #sample_data['query'][i] = f"artist: {sample_data['artist'][i]}, title: {sample_data['title'][i]}" #generate track queries
        results = sp.search(q=f"artist: {sample_data['artist'][i]} track: {sample_data['title'][i]}", limit=5, type='track') #get 5 responses since first isn't always accurate
        if results['tracks']['total'] == 0: #if track isn't on spotify as queried, go to next track
            continue
        else:
            for j in range(len(results['tracks']['items'])):
                if fuzz.partial_ratio(results['tracks']['items'][j]['artists'][0]['name'], sample_data['artist'][i]) > 50: #get right response by matching on artist
                    track_ids.append(results['tracks']['items'][j]['id']) #append track id
                    break #don't want repeats of a sample ex: different versions
                else:
                    continue

    return track_ids

def GetPlaylistID(username, playlist_name):
    playlist_id = ''
    playlists = sp.user_playlists(username)
    for playlist in playlists['items']:  # iterate through playlists I follow
        if playlist['name'] == playlist_name:  # filter for newly created playlist
            playlist_id = playlist['id']
    return playlist_id

#Initiate Spotipy
scope = 'playlist-modify-public'
username = 'Insert Username Here'
client_id = 'Insert Client ID Here'
client_secret = 'Insert Client Secret Here'
token = util.prompt_for_user_token(username,scope,client_id=client_id,client_secret=client_secret,redirect_uri='http://localhost/') #Follow Directions in Console
sp = spotipy.Spotify(auth=token)

#Paste Genius Album URL
genius_url = 'Insert Genius Album URL Here'

# Scrape samples into dataframe and create sample playlist on Spotify
sample_data, album_artist, album_title = ScrapeGeniusURL(genius_url)
playlist_name = CreatePlaylist(username, album_title, album_artist)
track_ids = GetTrackIDs(sample_data)
track_ids = list(dict.fromkeys(track_ids)) #remove duplicates
playlist_id = GetPlaylistID(username, playlist_name)


#Populate playlist with samples
sp.user_playlist_add_tracks(username, playlist_id, track_ids)