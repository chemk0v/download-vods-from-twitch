import os
import yt_dlp
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

# ===== Secrets =====
client_secret_json = os.getenv("CLIENT_SECRET_JSON")
token_json = os.getenv("YOUTUBE_TOKEN_JSON")
twitch_url = os.getenv("TWITCH_URL")

# ===== Создаём файлы =====
with open("client_secret.json", "w") as f:
    f.write(client_secret_json)

with open("token.json", "w") as f:
    f.write(token_json)

# ===== Скачивание VOD =====
ydl_opts = {
    "outtmpl": "video.mp4",
    "format": "bestvideo+bestaudio/best"
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download([twitch_url])

# ===== YouTube auth =====
creds = Credentials.from_authorized_user_file("token.json")
youtube = build("youtube", "v3", credentials=creds)

# ===== Upload =====
request_body = {
    "snippet": {
        "title": "Twitch VOD",
        "description": "Auto upload",
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
        print(f"Progress: {int(status.progress() * 100)}%")

print("Done!")
