import os
import requests
import xml.dom.minidom
import xml.etree.ElementTree as ET
import threading

from downloader import download_file
import music_tag
from rich.progress import Progress
import time


class Episode:
    def __init__(self, title: str,image: str, duration: int, download_url: str, season:int, episode:int):
        self.title = title
        self.image = image
        self.duration = duration
        self.download_url = download_url
        self.season = season
        self.episode = episode
    
    def download(self, location=None, is_single_season=False):
        if not is_single_season:
            file_name = f"{self.season}.{self.episode} - {self.title.replace('/', '-')}.mp3"
        else:
            file_name = f"{self.episode} - {self.title.replace('/', '-')}.mp3"
        if os.path.exists(file_name):
            return
        # download_file(self.download_url, file_name, location, 1)
        resp = requests.get(self.download_url).content
        with open(file_name, 'wb') as f:
            f.write(resp)

        music_file = music_tag.load_file(file_name)
        music_file['title'] = self.title
        music_file['track number'] = str(self.episode)

        if self.image != "" and self.image is not None:
            resp = requests.get(self.image).content
            music_file['artwork'] = resp 

        music_file.save()           
    
    def __str__(self) -> str:
        return f"#{self.season}.{self.episode} - {self.title.replace('/', '-')}"


class Podcast:
    def __init__(self,rss_feed: str, title: str=None, language: str=None, cover: str=None, episodes: list[Episode]=None):
        self.title = title
        self.language = language
        self.cover = cover
        self.rss_feed = rss_feed

        self.is_single_season = True

        self.episodes = episodes
        if self.episodes is None:
            self.episodes = []

    def get_podcast_data(self):
        rss_xml = requests.get(self.rss_feed).text
        root = ET.fromstring(rss_xml)
        self.title = root.find(".//title").text
        self.language = root.find(".//language").text
        self.cover = root.find(".//{http://www.itunes.com/dtds/podcast-1.0.dtd}image").attrib.get("href")

        current_ep = 0
        current_season = 1
        for i, item in enumerate(root.findall(".//item")[::-1]):
            title = item.find("title").text
            season_tag = item.find("{http://www.itunes.com/dtds/podcast-1.0.dtd}season")
            if season_tag is not None:
                current_season = season_tag.text
                if int(current_season) != 0:
                    self.is_single_season = False
            season = current_season

            episodetype = item.find("{http://www.itunes.com/dtds/podcast-1.0.dtd}episodeType")
            if episodetype is None:
                episodetype = "full"
            else:
                episodetype = episodetype.text

            episode_type = item.find("{http://www.itunes.com/dtds/podcast-1.0.dtd}episode")
            if episode_type is None and "trailer" in title.lower() or episodetype == "trailer":
                current_ep = 0
            episode = current_ep
            current_ep+=1

            image = item.find("{http://www.itunes.com/dtds/podcast-1.0.dtd}image")
            if image is None:
                image = ""
            else:
                image = image.attrib.get("href")

            ep = Episode(
                image = image,
                duration = item.find("{http://www.itunes.com/dtds/podcast-1.0.dtd}duration").text,
                download_url= item.find("enclosure").attrib.get("url"),
                season = season,
                episode = episode,
                title = title
            )
            self.episodes.append(ep)

def process_queue(episodes: list[Episode], is_single_season):

    with Progress() as progress:
        task1 = progress.add_task("[green] Downloading Episodes", total=len(episodes))

        for episode in episodes:
            progress.update(task1, description=str(episode.episode)+" - "+episode.title[:30]+"... ")
            episode.download(is_single_season=is_single_season)
            progress.update(task1, advance=1)

joy = Podcast('https://feed.cdnstream1.com/zjb/feed/download/ea/af/56/eaaf5628-4c1c-456f-8874-00720745cc23.xml')
joy.get_podcast_data()


num_threads = 1  # You can adjust this number as needed
total_episodes = len(joy.episodes)
episodes_per_thread = total_episodes // num_threads

queues = []
for i in range(num_threads-1):
    start = i*episodes_per_thread
    end = start + episodes_per_thread

    queues.append(joy.episodes[start:end])

last_q = []
for ep in joy.episodes:
    ep_in = False
    for q in queues:
        if ep in q:
            ep_in = True
    
    if not ep_in:
        last_q.append(ep)

queues.append(last_q)

# for q in queues:
#     print(queues.index(q))
#     print("====================================================")
#     for ep in q:
#         print(ep)


# exit()
threads = []        
for queue in queues:
    process_queue(queue,joy.is_single_season)