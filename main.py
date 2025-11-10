import discord
from discord.ext import commands
import asyncio
import random
import os
from rapidfuzz import fuzz
import subprocess
import json

# Load environment variables
TOKEN = os.getenv("DISCORD_TOKEN")
MUSIC_TEXT_CHANNEL = int(os.getenv("MUSIC_TEXT_CHANNEL"))
MUSIC_VOICE_CHANNEL = int(os.getenv("MUSIC_VOICE_CHANNEL"))
SONGS_JSON_PATH = "songs.json"  # your local JSON database of songs

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

scores = {}
current_song = None
answer_found = False
fastest_answered = False

# Detect ffmpeg path dynamically
def get_ffmpeg_path():
    try:
        path = subprocess.check_output(["which", "ffmpeg"]).decode().strip()
        print(f"Using ffmpeg executable at: {path}")
        return path
    except Exception as e:
        print(f"Could not find ffmpeg executable, falling back to 'ffmpeg': {e}")
        return "ffmpeg"

FFMPEG_PATH = get_ffmpeg_path()


async def load_songs_from_json():
    try:
        with open(SONGS_JSON_PATH, "r", encoding="utf-8") as f:
            songs = json.load(f)
            print(f"Loaded {len(songs)} tracks from {SONGS_JSON_PATH}.")
            return songs
    except Exception as e:
        print(f"Failed to load songs from JSON: {e}")
        return []


async def start_music_round():
    try:
        channel = await bot.fetch_channel(MUSIC_TEXT_CHANNEL)
    except discord.NotFound:
        print("❌ Text channel not found via fetch_channel.")
        return
    except discord.Forbidden:
        print("❌ No permission to fetch the text channel.")
        return
    except Exception as e:
        print(f"❌ Unexpected error fetching text channel: {e}")
        return

    vc_channel = bot.get_channel(MUSIC_VOICE_CHANNEL)
    if not vc_channel:
        await channel.send("❌ Voice channel not found.")
        return

    try:
        vc = await vc_channel.connect()
    except Exception as e:
        await channel.send(f"❌ Failed to connect to voice channel: {e}")
        return

    await channel.send("🎶 **Welcome to Music Trivia!** Guess the song title as fast as you can!")

    songs = await load_songs_from_json()
    if len(songs) < 10:
        await channel.send("⚠️ Not enough tracks in the JSON file!")
        await vc.disconnect()
        return

    random.shuffle(songs)

    global current_song, answer_found, fastest_answered

    for i, song in enumerate(songs[:10], 1):
        current_song, answer_found, fastest_answered = song, False, False

        await channel.send(f"▶️ **Song {i}/10** — listen carefully!")
        vc.play(
            discord.FFmpegPCMAudio(
                song["preview_url"],
                executable=FFMPEG_PATH,
                before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                options="-vn"
            )
        )
        await asyncio.sleep(10)  # play 10-second preview
        vc.stop()

        if not answer_found:
            await channel.send(f"⏰ Time's up! The answer was **{song['title']}** by *{song['artist']}*.")
        await asyncio.sleep(6)

    await vc.disconnect()
    await show_leaderboard(channel)
    await channel.send("🎵 Round complete! Type `!music` to start another game.")


@bot.event
async def on_ready():
    print(f"{bot.user} is live as the Music Trivia Bot 🎵")
    # Auto-start on bot ready:
    await start_music_round()


@bot.event
async def on_message(message):
    global answer_found, fastest_answered

    if message.author.bot or message.channel.id != MUSIC_TEXT_CHANNEL:
        return

    if current_song and not answer_found:
        guess = message.content.lower()
        correct = current_song["answer"].lower()
        ratio = fuzz.partial_ratio(guess, correct)
        if ratio >= 80:
            answer_found = True
            user = message.author

            if not fastest_answered:
                fastest_answered = True
                scores[user] = scores.get(user, 0) + 15  # 10 pts + 5 bonus
                await message.channel.send(
                    f"⚡ {user.mention} got it first! **{current_song['title']}** (+15 pts)"
                )
            else:
                scores[user] = scores.get(user, 0) + 10
                await message.channel.send(
                    f"✅ {user.mention} got it! **{current_song['title']}** (+10 pts)"
                )

    await bot.process_commands(message)


async def show_leaderboard(channel):
    if not scores:
        await channel.send("No correct answers this round.")
        return

    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    leaderboard = "\n".join(
        [f"**{i+1}. {user.display_name}** — {points} pts" for i, (user, points) in enumerate(sorted_scores)]
    )
    await channel.send(f"🏆 **Final Leaderboard:**\n{leaderboard}")


@bot.command(name="music")
async def manual_start(ctx):
    await ctx.send("🎧 Starting a new music trivia round!")
    await start_music_round()


bot.run(TOKEN)
