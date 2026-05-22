import requests
from bs4 import BeautifulSoup
import json
import pandas as pd
from IPython.display import Image, display
from collections import defaultdict
import sqlite3
import os
from googleapiclient.discovery import build

def get_latest_videos(playListId,developerKey):
  # Initialize the YouTube API client
  youtube = build('youtube', 'v3', developerKey=developerKey)

  # Request the latest videos from a playlist
  request = youtube.playlistItems().list(
      part="snippet",
      playlistId=playListId,
      maxResults=5
  )
  response = request.execute()

  recordings = defaultdict(dict)
  for video in response['items']:
    title = video['snippet']['title']
    image_url = video['snippet']['thumbnails']['default']['url']
    link = 'https://www.youtube.com/watch?v=' + video['snippet']['resourceId']['videoId']
    recordings[title]['link'] = link
    recordings[title]['image_url'] = image_url
    
  return recordings

def save_to_database(recordings, name, database = 'default.db'):
  #All tables have columns title, length, link, and image_url
  connection = sqlite3.connect(database)
  cursor = connection.cursor()

  #Find the table or create it if it doesn't exist!
  find_table = cursor.execute(f'SELECT name FROM sqlite_master WHERE name="{name}"')
  if find_table.fetchone() == None:
    cursor.execute(f'CREATE TABLE {name}(title, link, image_url)')

  new_videos = {}
  for title in recordings.keys():
    result = cursor.execute(f'SELECT title FROM {name} WHERE title="{title}" AND link="{recordings[title]['link']}"')
    if result.fetchone() == None:
      #This video doesn't exist in the database yet!
      new_videos[title] = {'Link': recordings[title]['link'],'Image URL': recordings[title]['image_url']}
      cursor.execute(f'INSERT INTO {name} VALUES ("{title}", "{recordings[title]['link']}", "{recordings[title]['image_url']}")')
      connection.commit()

  connection.close()
  return new_videos

def upload_to_discord(url,new_videos):
  split = []
  for a,b in new_videos.items():
    if not split:
      split.append({})
      split[0][a] = b['Link']
    elif len(split[-1]) < 5:
      split[-1][a] = b['Link']
    else:
      split.append({})
      split[-1][a] = b['Link']
  for group in split:
    data = {"content": json.dumps(group,indent=4)}
    requests.post(url, json=data)

def notification(webhook, playListId, database_name, developerKey):
  recordings = get_latest_videos(playListId, developerKey)
  new_videos = save_to_database(recordings = recordings, name = database_name)
  upload_to_discord(webhook,new_videos)

if __name__ == "__main__":
  boss_cr_webhook = os.getenv('BOSS_CR_WEBHOOK')
  alt_webhook = os.getenv('ALT_WEBHOOK')
  developer_key = os.getenv('DEVELOPER_KEY')
  database_name = 'clashroyale'
  boss_cr_playlist_id = 'UU2PcZfmy7CYrKmFH2-yx_wQ'
  
  notification(boss_cr_webhook, boss_cr_playlist_id, database_name, developer_key)
