import os
import yt_dlp
import asyncio
import time
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set! Add it as an environment variable.")

async def download_audio(youtube_url, update: Update, context: ContextTypes.DEFAULT_TYPE):
    output_path = "downloads"
    os.makedirs(output_path, exist_ok=True)
    output_template = os.path.join(output_path, "%(title)s.%(ext)s")

    msg = await update.message.reply_text("Starting download...")  # Initial message
    last_progress = 0  # Track progress
    last_update_time = 0

    async def report_progress(d):
        nonlocal last_progress, last_update_time
        if d['status'] == 'downloading':
            progress_str = d.get('_percent_str', '0%').strip()
            try:
                progress = int(float(progress_str.replace('%', '')))
            except ValueError:
                progress = last_progress

            current_time = time.time()
            if (progress >= last_progress + 5) or (current_time - last_update_time > 2):
                last_progress = progress
                last_update_time = current_time
                await msg.edit_text(f"Downloading... {progress}%")

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'progress_hooks': [report_progress],
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
        'ffmpeg_location': '/usr/bin/ffmpeg'  # This is the default path on Linux
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
            base_filename = ydl.prepare_filename(info).rsplit(".", 1)[0]
            mp3_file = f"{base_filename}.mp3"

        await msg.edit_text("Downloading... 100% ✅")  # Ensure it shows 100%
        return mp3_file, msg
    except Exception as e:
        await msg.edit_text(f"Download error: {e}")
        return None, msg

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    youtube_url = update.message.text.strip()
    
    if "youtube.com" not in youtube_url and "youtu.be" not in youtube_url:
        await update.message.reply_text("Please send a valid YouTube video link.")
        return
    
    mp3_file, msg = await download_audio(youtube_url, update, context)

    if not mp3_file or not os.path.exists(mp3_file):
        await msg.edit_text("Error: Audio file not found.")
        return

    await msg.edit_text("Uploading to Telegram... ⏳")

    try:
        with open(mp3_file, 'rb') as file:
            await update.message.reply_audio(InputFile(file))

        await msg.edit_text("✅ Done!")
    except Exception as e:
        await msg.edit_text(f"Error: {str(e)}")
    finally:
        # Always delete the file after processing
        try:
            os.remove(mp3_file)
        except Exception as e:
            print(f"Failed to delete file: {e}")

def main():
    app = Application.builder().token(BOT_TOKEN).read_timeout(300).write_timeout(300).build()
    app.add_handler(CommandHandler("start", lambda update, context: update.message.reply_text("Send a YouTube link.")))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
