import requests
from bs4 import BeautifulSoup
import json
import pandas as pd
from IPython.display import Image, display
from collections import defaultdict
import sqlite3
import os

def get_latest_videos(link = 'https://www.youtube.com/@Bosscr/videos'):
  #Retrieve the HTML from the desired channel
  url = link
  headers = {"User-Agent": "Mozilla/5.0"}
  response = requests.get(url, headers=headers)
  html = response.text

  #Parse the HTML and find the json text containing information about recent YouTube videos
  soup = BeautifulSoup(html, "html.parser")
  script_tag = soup.find("script", string=lambda t: t and "var ytInitialData = " in t)
  json_text = script_tag.string.strip()[len("var ytInitialData = "):-1]

  #Load the json into a dictionary format for easier analysis and extract the relevant metadata
  data = json.loads(json_text)
  videos_data = data['contents']['twoColumnBrowseResultsRenderer']['tabs'][1]['tabRenderer']['content']['richGridRenderer']['contents'][:-1]
  recordings = defaultdict(dict) #title: {length,link,image_url}
  for i,video in enumerate(videos_data):
    title = video['richItemRenderer']['content']['videoRenderer']['title']['runs'][0]['text']
    length = video['richItemRenderer']['content']['videoRenderer']['lengthText']['accessibility']['accessibilityData']['label']
    link = 'https://www.youtube.com/' + video['richItemRenderer']['content']['videoRenderer']['navigationEndpoint']['commandMetadata']['webCommandMetadata']['url']
    image_url = video['richItemRenderer']['content']['videoRenderer']['thumbnail']['thumbnails'][0]['url']
    recordings[title]['length'] = length
    recordings[title]['link'] = link
    recordings[title]['image_url'] = image_url


  #Return the video metadata we found
  return recordings

def save_to_database(database = 'default.db',recordings = defaultdict(dict), name = 'clashroyale'):
  #All tables have columns title, length, link, and image_url
  connection = sqlite3.connect(database)
  cursor = connection.cursor()

  #Find the table or create it if it doesn't exist!
  find_table = cursor.execute(f'SELECT name FROM sqlite_master WHERE name="{name}"')
  if find_table.fetchone() == None:
    cursor.execute(f'CREATE TABLE {name}(title, length, link, image_url)')

  new_videos = {}
  for title in recordings.keys():
    result = cursor.execute(f'SELECT title FROM {name} WHERE title="{title}" AND length="{recordings[title]['length']}"')
    if result.fetchone() == None:
      #This video doesn't exist in the database yet!
      new_videos[title] = {'Length': recordings[title]['length'],'Link': recordings[title]['link'],'Image URL': recordings[title]['image_url']}
      cursor.execute(f'INSERT INTO {name} VALUES ("{title}", "{recordings[title]['length']}", "{recordings[title]['link']}", "{recordings[title]['image_url']}")')
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

def notification(webhook,video_link = 'https://www.youtube.com/@Bosscr/videos', database_name = 'clashroyale'):
  recordings = get_latest_videos(video_link)
  new_videos = save_to_database(recordings = recordings, name = database_name)
  upload_to_discord(webhook,new_videos)

if __name__ == "__main__":
  boss_cr_webhook = os.getenv('BOSS_CR_WEBHOOK')
  notification(boss_cr_webhook)