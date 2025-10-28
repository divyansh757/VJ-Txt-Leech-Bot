""" Advanced Telegram Downloader Bot Features included:

.txt -> download links via anonymouspwplayer API

4K support (2160p)

Step-by-step processing messages with emojis

Download progress parsing (speed, percent, ETA)

Upload progress updates

Auto-forward to channel (optional)

Animated 3s Spark Intro created on-the-fly using ffmpeg ("Downloaded by Divyansh Shukla")

Final caption uses Royal Signature style


Requirements:

python3.9+

ffmpeg installed on the server

yt-dlp accessible in PATH

pip install -r requirements.txt (pyrogram, aiohttp, yt-dlp, python-dotenv)


Place this file as main.py and create a vars.py with API_ID, API_HASH, BOT_TOKEN (and optional PW_TOKEN). """

import os import re import sys import time import json import shlex import asyncio import urllib.parse from pathlib import Path from datetime import datetime

from pyrogram import Client, filters from pyrogram.types import Message

Load configuration from vars.py

try: from vars import API_ID, API_HASH, BOT_TOKEN, PW_TOKEN except Exception: # PW_TOKEN optional try: from vars import API_ID, API_HASH, BOT_TOKEN PW_TOKEN = "" except Exception as e: print("Please create vars.py with API_ID, API_HASH, BOT_TOKEN") raise

APP = Client("divyansh_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

WORKDIR = Path("./downloads") WORKDIR.mkdir(exist_ok=True)

INTRO_FILE = Path("intro_spark.mp4")

Royal signature caption style

CREDIT_CAPTION = ( "━━━━━━━━━━━━━━━\n" "🎬 𝗖𝗿𝗮𝗳𝘁𝗲𝗱 𝗯𝘆 𝗗𝗶𝘃𝘆𝗮𝗻𝘀𝗵 𝗦𝗵𝘂𝗸𝗹𝗮 💫\n" "━━━━━━━━━━━━━━━" )

Helper: create a 3-second animated intro using ffmpeg drawtext (sparkle-like)

def ensure_intro(): if INTRO_FILE.exists(): return # Generate a simple 3s intro with animated text using drawtext and fade cmd = ( "ffmpeg -y -f lavfi -i color=size=1280x720:duration=3:rate=25:color=0x000000 " "-vf " "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:" "text='✨ Downloaded by Divyansh Shukla ✨':fontcolor=white:fontsize=48:box=1:boxcolor=black@0.4:boxborderw=10:" "x=(w-text_w)/2:y=(h-text_h)/2,format=yuv420p,fade=t=in:st=0:d=0.7,fade=t=out:st=2.3:d=0.7" " f"-c:v libx264 -crf 18 -pix_fmt yuv420p {shlex.quote(str(INTRO_FILE))}" ) print("Creating intro clip... this may take a few seconds.") os.system(cmd)

async def run_cmd_and_stream_progress(cmd, status_message, chat_id, edit_every=1.0): """Run yt-dlp (or any shell command) and stream progress by parsing stdout lines. This implementation watches for yt-dlp progress lines like: [download]  12.3% of 50.00MiB at 1.23MiB/s ETA 00:00:30 """ process = await asyncio.create_subprocess_shell( cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT, cwd=str(WORKDIR) )

last_edit = time.time()
percent = 0
speed = "0"
eta = "--:--"

# read lines
while True:
    line = await process.stdout.readline()
    if not line:
        break
    try:
        text = line.decode(errors="ignore").strip()
    except:
        text = str(line)

    # parse common yt-dlp progress format
    m = re.search(r"download\s+([0-9]{1,3}\.\d|[0-9]{1,3})%.*?at\s+([0-9\.]+\w+/s)\s+ETA\s+([0-9:\-]+)", text)
    if m:
        percent = m.group(1)
        speed = m.group(2)
        eta = m.group(3)
    else:
        # alternative pattern
        m2 = re.search(r"download\s+([0-9]{1,3}\.\d|[0-9]{1,3})%", text)
        if m2:
            percent = m2.group(1)

    # periodically edit status
    if time.time() - last_edit > edit_every:
        last_edit = time.time()
        try:
            await status_message.edit_text(
                f"🎞️ Processing...\n🚀 Speed: {speed} | Progress: {percent}% | ⏳ ETA: {eta}"
            )
        except Exception:
            pass

await process.wait()
return process.returncode

async def send_file_with_progress(bot, chat_id, file_path, caption, status_message): """Upload file (video/document) with progress edits.""" total = os.path.getsize(file_path) sent_bytes = 0

async def _progress(current, total_bytes):
    nonlocal sent_bytes
    sent_bytes = current
    try:
        percent = (current / total_bytes) * 100 if total_bytes else 0
        text = f"📤 Uploading...\nProgress: {percent:.2f}% | {current//1024//1024}MB/{total_bytes//1024//1024}MB"
        await status_message.edit_text(text)
    except Exception:
        pass

# use send_video if mp4, else send_document
try:
    if str(file_path).lower().endswith(('.mp4', '.mkv', '.mov')):
        msg = await APP.send_video(chat_id=chat_id, video=str(file_path), caption=caption, progress=_progress, progress_args=(total,))
    else:
        msg = await APP.send_document(chat_id=chat_id, document=str(file_path), caption=caption, progress=_progress, progress_args=(total,))
except Exception as e:
    # fallback to send_document
    msg = await APP.send_document(chat_id=chat_id, document=str(file_path), caption=caption)

return msg

@APP.on_message(filters.command("start")) async def start(_, m: Message): await m.reply_text("Hello! Send /upload to begin. This bot adds a short animated intro and credits to each video.")

@APP.on_message(filters.command("upload")) async def upload_handler(_, m: Message): chat_id = m.chat.id editable = await m.reply_text("📥 Please send the .txt file with one link per line.")

try:
    txt_msg: Message = await APP.listen(chat_id)
except Exception as e:
    await editable.edit("⚠️ Timed out waiting for file.")
    return

# download txt
try:
    txt_path = await txt_msg.download(file_name=str(WORKDIR / f"links_{chat_id}.txt"))
    await txt_msg.delete(True)
except Exception as e:
    await editable.edit("⚠️ Failed to download the .txt file.")
    return

await editable.edit("🔍 Reading links...")
with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
    items = [line.strip() for line in f.readlines() if line.strip()]

if not items:
    await editable.edit("⚠️ No links found in the file.")
    return

await editable.edit(f"⚙️ Found {len(items)} links. Which link number to start from? (type number e.g. 1)")
start_msg: Message = await APP.listen(chat_id)
try:
    start_idx = int(start_msg.text.strip()) - 1
except Exception:
    start_idx = 0
await start_msg.delete(True)

await editable.edit("📛 Enter your batch name (this will be used in captions):")
batch_msg: Message = await APP.listen(chat_id)
batch_name = batch_msg.text.strip() or "Batch"
await batch_msg.delete(True)

await editable.edit("📸 Choose resolution: 144,240,360,480,720,1080,2160 (type number)")
res_msg: Message = await APP.listen(chat_id)
raw_res = res_msg.text.strip()
await res_msg.delete(True)
try:
    max_height = int(raw_res)
except Exception:
    max_height = 720

await editable.edit("✍️ Enter a caption (type 'no' to skip):")
cap_msg: Message = await APP.listen(chat_id)
user_caption = cap_msg.text.strip()
await cap_msg.delete(True)
if user_caption.lower() == 'no':
    user_caption = ''

await editable.edit("🖼️ Send thumbnail URL or type 'no' to skip:")
thumb_msg: Message = await APP.listen(chat_id)
thumb = thumb_msg.text.strip()
await thumb_msg.delete(True)
if thumb.lower() == 'no':
    thumb = None

# ask for pw_token (can use env PW_TOKEN if present)
await editable.edit("🔐 Send pw_token for anonymouspwplayer API or type 'skip' to bypass:")
token_msg: Message = await APP.listen(chat_id)
given_token = token_msg.text.strip()
await token_msg.delete(True)
if given_token.lower() == 'skip' or given_token == '':
    given_token = PW_TOKEN or ''

# ask for channel id or skip
await editable.edit("📢 Send channel username or ID to auto-forward (e.g. @channel or -1001234567890). Type 'skip' to disable.")
ch_msg: Message = await APP.listen(chat_id)
channel_id = ch_msg.text.strip()
await ch_msg.delete(True)
if channel_id.lower() == 'skip' or channel_id == '':
    channel_id = None

# summary
await editable.edit(f"✅ Starting from link #{start_idx+1}. Batch: {batch_name}. Resolution: {max_height}p. Links: {len(items)}")

# ensure intro exists
ensure_intro()

# process links
count = start_idx + 1
for idx in range(start_idx, len(items)):
    raw = items[idx]
    # build original url if needed
    if raw.startswith('http'):
        original_url = raw
    else:
        # in case txt had scheme-less entries
        original_url = 'https://' + raw

    # wrap with API if token present
    final_url = original_url
    if given_token:
        encoded = urllib.parse.quote_plus(original_url)
        final_url = f"https://anonymouspwplayer-25261acd1521.herokuapp.com/pw?url={encoded}&token={urllib.parse.quote_plus(given_token)}"

    name_safe = re.sub(r"[^0-9A-Za-z\-_. ]+", "", original_url)[:60]
    base_name = f"{str(count).zfill(3)}_{name_safe}"
    out_file = WORKDIR / f"{base_name}.mp4"

    status = await APP.send_message(chat_id, f"🎞️ Starting {count}/{len(items)}\n🔗 {original_url}\n⏳ Preparing download...")

    # build yt-dlp command
    ytf = f"bestvideo[height<={max_height}]+bestaudio/best"
    cmd = f"yt-dlp -f \"{ytf}\" -o {shlex.quote(str(out_file))} --newline {shlex.quote(final_url)}"

    # run and stream progress
    try:
        rc = await run_cmd_and_stream_progress(cmd, status, chat_id)
        if rc != 0:
            await status.edit_text(f"⚠️ Download failed for link {count}. Trying direct URL fallback...")
            # try fallback direct
            if final_url != original_url:
                cmd2 = f"yt-dlp -f \"{ytf}\" -o {shlex.quote(str(out_file))} --newline {shlex.quote(original_url)}"
                await run_cmd_and_stream_progress(cmd2, status, chat_id)
    except Exception as e:
        await status.edit_text(f"⚠️ Exception during download: {e}")
        count += 1
        continue

    # after download, merge intro + video
    final_output = WORKDIR / f"final_{base_name}.mp4"
    await status.edit_text("✨ Adding intro animation...")
    concat_cmd = (
        f"ffmpeg -y -i {shlex.quote(str(INTRO_FILE))} -i {shlex.quote(str(out_file))} "
        f"-filter_complex \"[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[outv][outa]\" -map \"[outv]\" -map \"[outa]\" "
        f"-c:v libx264 -crf 18 -preset veryfast -c:a aac {shlex.quote(str(final_output))}"
    )
    os.system(concat_cmd)

    # optional: remove original downloaded to save space
    try:
        if out_file.exists():
            out_file.unlink()
    except Exception:
        pass

    # upload with progress
    caption = (user_caption + "\n\n" if user_caption else "") + f"{CREDIT_CAPTION}\nBatch: {batch_name} | ID: {str(count).zfill(3)}"

    try:
        uploaded_msg = await send_file_with_progress(APP, chat_id, str(final_output), caption, status)
    except Exception as e:
        await status.edit_text(f"⚠️ Upload failed: {e}")
        count += 1
        continue

    # forward to channel if set
    if channel_id:
        try:
            # try to copy message to channel (preserves file)
            await APP.copy_message(chat_id=channel_id, from_chat_id=chat_id, message_id=uploaded_msg.message_id)
            await APP.send_message(chat_id, f"📢 Auto-forwarded to {channel_id}")
        except Exception as e:
            await APP.send_message(chat_id, f"⚠️ Forward failed: {e}")

    # cleanup final_output
    try:
        if final_output.exists():
            final_output.unlink()
    except Exception:
        pass

    await status.edit_text(f"✅ Done {count}/{len(items)}\n{CREDIT_CAPTION}")
    count += 1

await APP.send_message(chat_id, "🏁 All tasks completed. Enjoy! ✨")

if name == 'main': print("Starting bot...") APP.run()
