import yt_dlp

url = "https://parlament.mt/Audio/14thLeg/Plenary/Plenary%20008%2023-05-2022%201600hrs.mp3"

# Define a custom User-Agent string
user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"

# Set up the download options
ydl_opts = {
    'outtmpl': '%(title)s.%(ext)s',
    'user_agent': user_agent,
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}

# Download the file
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download([url])
