#Scrape Genius.com for samples on an album and use Spotipy to automatically create a playlist of the samples

import pandas as pd
import spotipy
import spotipy.util as util
from bs4 import BeautifulSoup
import sys
import requests
import metadata_parser
import json


scope = 'playlist-modify-public'
username = 'Insert Spotify username here'
client_id = 'Insert Spotify client id here'
client_secret = 'Insert Spotify client secret here'
genius_url = 'Insert Genius Album URL Here ex: https://genius.com/albums/Kanye-west/The-college-dropout'



#Initiate Spotipy
token = util.prompt_for_user_token(username,scope,client_id=client_id,client_secret=client_secret
                                   ,redirect_uri='http://localhost/') #Follow Directions in Console
sp = spotipy.Spotify(auth=token)

#Scrape Genius
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
        sample_data.append({'title' : y['song']['song_relationships'][0]['songs'][j]['title'], 'artist' : y['song']['song_relationships'][0]['songs'][j]['primary_artist']['name']})

sample_data = pd.DataFrame(sample_data) #dataframe with sample title and artist

#Get Spotify track ids for samples
track_ids = []
for i in range(len(sample_data)):
        #sample_data['query'][i] = f"artist: {sample_data['artist'][i]}, title: {sample_data['title'][i]}" #generate track queries
        results = sp.search(q=f"artist: {sample_data['artist'][i]} track: {sample_data['title'][i]}", limit=5, type='track') #get 5 responses since first isn't always accurate
        if results['tracks']['total'] == 0: #if track isn't on spotify as queried, go to next track
            continue
        else:
            for j in range(len(results['tracks']['items'])):
                if results['tracks']['items'][j]['artists'][0]['name'] == sample_data['artist'][i]: #get right response by matching on artist
                    track_ids.append(results['tracks']['items'][j]['id']) #append track id
                    break #don't want repeats of a sample ex: different versions
                else:
                    continue





#Create Appropriately Titled Empty Playlist For Samples
playlist_name = f"Samples in {album_title} by {album_artist}"
sp.user_playlist_create(username, name=playlist_name )

playlists = sp.user_playlists(username)

for playlist in playlists['items']: #iterate through playlists I follow
            if playlist['name'] == playlist_name: #filter for newly created playlist
                playlist_id = playlist['id']

#Populate playlist with samples
sp.user_playlist_add_tracks(username, playlist_id, track_ids)