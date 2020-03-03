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
#To help with nested dictionary response
def gen_dict_extract(key, var): #Courtesy of https://stackoverflow.com/questions/9807634/find-all-occurrences-of-a-key-in-nested-dictionaries-and-lists
    if hasattr(var, 'items'):
        for k, v in var.items():
            if k == key:
                yield v
            if isinstance(v, dict):
                for result in gen_dict_extract(key, v):
                    yield result
            elif isinstance(v, list):
                for d in v:
                    for result in gen_dict_extract(key, d):
                        yield result

def ScrapeGeniusURL(genius_url):
    r = requests.get(genius_url)

    soup = BeautifulSoup(r.content, features='html.parser')
    album_title = soup.find(class_ = 'breadcrumb breadcrumb-current_page').find(itemprop = "title").get_text()
    album_artist = soup.find(class_ = 'header_with_cover_art-primary_info-primary_artist').get_text()

    song_links = []
    for link in soup.find_all(class_ = 'u-display_block', href=True):
        song_links.append(link['href'])

    sample_data = []
    titles = []



    for i in range(len(song_links)):
        # Track Info Box Flow
        s = requests.get(song_links[i]) #picking specific song
        song_content = BeautifulSoup(s.content, features='html.parser')
        song_json = song_content.find(itemprop = "page_data").get('content') #convert page metadata to json
        y = json.loads(song_json)
        m = len(y['song']['song_relationships'][0]['songs'])  #indices for accessing sample artist and sample title
        for j in range(m):
            sample_data.append({'title' : re.sub("\(.*\)", "", y['song']['song_relationships'][0]['songs'][j]['title']), 'artist' : y['song']['song_relationships'][0]['songs'][j]['primary_artist']['name']})
        #Track Annotation Flow
        annotation_id = song_content.find(class_='referent').get('data-id') #Get Genius annotation id
        querystring = "https://api.genius.com/annotations/" + annotation_id  # Annotations endpoint
        response = requests.get(querystring, headers=headers) #Get info on annotation from Genius API
        x = response.json()

        if "Produced by" in x['response']['referent']['range']['content']:
            possible_links = list(gen_dict_extract('href', x))
            for link in possible_links:
                r = requests.get(link)
                soup = BeautifulSoup(r.content, features='html.parser')
                try:
                    title = soup.find('span', attrs={'class': 'watch-title'}).get('title') #This will work if the link is a youtube video
                except:
                    continue
                title = re.sub("\(.*\)", "", title)
                title = re.sub('[\W_]+', ' ', title, flags=re.UNICODE) #format title
                title = re.sub("[0-9]", '', title)
                titles.append(title)


    sample_data = pd.DataFrame(sample_data)  # dataframe with sample title and artist from Track info boxes
    print("Scrape Finished.")



    return sample_data, album_artist, album_title, titles

def CreatePlaylist(username, album_title, album_artist):
    # Create Appropriately Titled Empty Playlist For Samples
    playlist_name = f"Samples in {album_title} by {album_artist}"
    sp.user_playlist_create(username, name=playlist_name)
    print("Playlist Created.")
    return playlist_name

def GetTrackIDs(sample_data, titles):
    #Get Spotify track ids for samples
    track_ids = []
    #Track Info Box Flow
    for i in range(len(sample_data)):
        results = sp.search(q=f"{sample_data['title'][i]} {sample_data['artist'][i]} ", limit=5, type='track') #get 5 responses since first isn't always accurate
        if results['tracks']['total'] == 0: #if track isn't on spotify as queried, go to next track
            continue
        else:
            for j in range(len(results['tracks']['items'])):
                if fuzz.partial_ratio(results['tracks']['items'][j]['artists'][0]['name'], sample_data['artist'][i]) > 90 and fuzz.partial_ratio(results['tracks']['items'][j]['name'], sample_data['title'][i]) > 90 : #get right response by matching on artist and title
                    track_ids.append(results['tracks']['items'][j]['id']) #append track id
                    break #don't want repeats of a sample ex: different versions
                else:
                    continue
    #Track Annotation Flow
    annotation_track_ids = []
    for title in titles:
        results = sp.search(q=f"{title} ", type='track')
        if results['tracks']['total'] == 0: #if track isn't on spotify as queried, go to next track
            continue
        else:
            annotation_track_ids.append(results['tracks']['items'][0]['id'])
    track_ids = track_ids + annotation_track_ids
    print("Got TrackIDs")
    return track_ids

def GetPlaylistID(username, playlist_name):
    playlist_id = ''
    playlists = sp.user_playlists(username)
    for playlist in playlists['items']:  # iterate through playlists I follow
        if playlist['name'] == playlist_name:  # filter for newly created playlist
            playlist_id = playlist['id']
    print("Got Playlist ID.")
    return playlist_id


#Initiate Spotipy
scope = 'playlist-modify-public'
username = ''
client_id = ''
client_secret = ''
token = util.prompt_for_user_token(username,scope,client_id=client_id,client_secret=client_secret,redirect_uri='http://localhost/') #Follow Directions in Console
sp = spotipy.Spotify(auth=token)

#For Genius API
client_access_token = ''
headers = {"Authorization" : "Bearer " + client_access_token, "User-Agent" : ""}


#Paste Genius Album URL
genius_url = 'ex: https://genius.com/albums/Kanye-west/late-registration'

# Scrape samples into dataframe and create sample playlist on Spotify
sample_data, album_artist, album_title, titles = ScrapeGeniusURL(genius_url)
playlist_name = CreatePlaylist(username, album_title, album_artist)
track_ids = GetTrackIDs(sample_data, titles)
track_ids = list(dict.fromkeys(track_ids)) #remove duplicates
playlist_id = GetPlaylistID(username, playlist_name)


#Populate playlist with samples
sp.user_playlist_add_tracks(username, playlist_id, track_ids)

