import os
import re
import yt_dlp
from datetime import datetime
from zoneinfo import ZoneInfo
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

# ======================
# Secrets / env
# ======================

client_secret_json = os.getenv("CLIENT_SECRET_JSON")
token_json = os.getenv("YOUTUBE_TOKEN")
twitch_url = os.getenv("TWITCH_URL")

# ======================
# Создаём файлы
# ======================

with open("client_secret.json", "w") as f:
    f.write(client_secret_json)

with open("token.json", "w") as f:
    f.write(token_json)

# ======================
# Получаем metadata
# ======================

with yt_dlp.YoutubeDL({}) as ydl:
    info = ydl.extract_info(twitch_url, download=False)

    stream_title = info.get("title")
    timestamp = info.get("timestamp")

# ======================
# Безопасность title
# ======================

if not stream_title:
    stream_title = "Twitch VOD"

# ======================
# Дата по Москве
# ======================

if timestamp:
    dt_moscow = datetime.fromtimestamp(timestamp, ZoneInfo("Europe/Moscow"))
    formatted_date = dt_moscow.strftime("%d.%m.%Y")
else:
    formatted_date = ""

# ======================
# Формирование title
# ======================

if formatted_date:
    final_title = f"{formatted_date} | {stream_title}"
else:
    final_title = stream_title

# ======================
# Очистка title
# ======================

final_title = re.sub(r'[<>:"/\\|?*]', '-', final_title)
final_title = final_title.replace(">", "-")
final_title = final_title[:100]

print("FINAL TITLE:", final_title)

# ======================
# Скачивание VOD (720p)
# ======================

ydl_opts = {
    "outtmpl": "video.mp4",
    "format": "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "merge_output_format": "mp4"
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download([twitch_url])

# ======================
# Авторизация YouTube
# ======================

creds = Credentials.from_authorized_user_file("token.json")
youtube = build("youtube", "v3", credentials=creds)

# ======================
# Загрузка видео
# ======================

request_body = {
    "snippet": {
        "title": final_title,
        "description": "Auto uploaded Twitch VOD",
        "categoryId": "22"
    },
    "status": {
        "privacyStatus": "private"
    }
}

media = MediaFileUpload("video.mp4", chunksize=-1, resumable=True)

request = youtube.videos().insert(
    part="snippet,status",
    body=request_body,
    media_body=media
)

response = None

while response is None:
    status, response = request.next_chunk()
    if status:
        print(f"Upload progress: {int(status.progress() * 100)}%")

print("Upload complete! Video ID:", response.get("id"))
