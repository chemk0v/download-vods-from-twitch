import os
import re
import yt_dlp
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont
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
    thumbnail_url = info.get("thumbnail")

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
video_id = None

while response is None:
    status, response = request.next_chunk()
    if status:
        print(f"Upload progress: {int(status.progress() * 100)}%")

video_id = response.get("id")

print("Upload complete! Video ID:", video_id)

# ======================
# Превью с чёрным блоком и датой
# ======================

if thumbnail_url and video_id:
    # скачать превью
    r = requests.get(thumbnail_url)
    with open("thumb.jpg", "wb") as f:
        f.write(r.content)

    img = Image.open("thumb.jpg").convert("RGB")
    draw = ImageDraw.Draw(img)

    width, height = img.size

    # размеры блока (как вебка)
    box_width = int(width * 0.25)
    box_height = int(height * 0.20)

    # позиция (правый нижний угол)
    x1 = width - box_width - 20
    y1 = height - box_height - 20
    x2 = width - 20
    y2 = height - 20

    # чёрный блок
    draw.rectangle([x1, y1, x2, y2], fill="black")

    text = formatted_date

    # шрифт
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except:
        font = ImageFont.load_default()

    # центрирование текста
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    text_x = x1 + (box_width - text_width) // 2
    text_y = y1 + (box_height - text_height) // 2

    # белый текст
    draw.text((text_x, text_y), text, fill="white", font=font)

    # сохранить
    img.save("thumb_final.jpg")

    # загрузить превью в YouTube
    youtube.thumbnails().set(
        videoId=video_id,
        media_body=MediaFileUpload("thumb_final.jpg")
    ).execute()

    print("Thumbnail uploaded!")
