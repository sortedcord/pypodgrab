import os
import requests
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor

class FilePartDownload:
    def __init__(self, start, end, url, part, progress_bar):
        self.start = start
        self.end = end
        self.url = url
        self.part = part
        self.progress_bar = progress_bar

    def download(self, filename):
        # Check if part file already exists
        if os.path.exists(f"{self.part}_{filename}"):
            current_size = os.path.getsize(f"{self.part}_{filename}")
            # Adjust start based on what we already downloaded
            self.start += current_size

        headers = {'Range': f'bytes={self.start}-{self.end}'}
        r = requests.get(self.url, headers=headers, stream=True)
        # Open the file in append mode
        with open(f"{self.part}_{filename}", 'ab') as fp:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    fp.write(chunk)
                    self.progress_bar.update(len(chunk))

def combine_files(parts, filename):
    with open(filename, 'wb') as fp:
        for part in parts:
            with open(f"{part}_{filename}", 'rb') as fpart:
                fp.write(fpart.read())
            os.remove(f"{part}_{filename}")

def download_file(url, filename, location=None, download_threads=5,):
    r = requests.get(url)
    # print("\n\n")
    # for key, value in r.headers.items():
    #     print(key, ":", value)
    # print("\n\n")

    file_size = int(r.headers['content-length'])

    parts = list(range(download_threads))
    starts = [file_size//download_threads * i for i in range(download_threads)]
    ends = [file_size//download_threads * i - 1 for i in range(1, download_threads)] + [file_size]

    progress_bar = tqdm(total=file_size, unit='B', unit_scale=True, desc="Total Progress")

    # Create FilePartDownload instances without starting the downloads
    downloads = [FilePartDownload(start, end, url, part, progress_bar) for part, start, end in zip(parts, starts, ends)]

    # Update the progress bar with the size of already downloaded parts
    for download in downloads:
        if os.path.exists(f"{download.part}_{filename}"):
            progress_bar.update(os.path.getsize(f"{download.part}_{filename}"))

    # Start the downloads
    with ThreadPoolExecutor() as executor:
        for download in downloads:
            executor.submit(download.download, filename)

    progress_bar.close()
    combine_files(parts, filename)

# if __name__ == '__main__':
#     download_file('https://dts.podtrac.com/redirect.mp3/dovetail.prxu.org/5340/f5b82dd5-e9cc-454e-b8f0-ffb7c9405b4c/JOW_Ep._2_Flocking_FinalMix_v07_SEG_A.mp3', 1)