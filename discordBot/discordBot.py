import os
import subprocess
import time
from datetime import datetime, timezone
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv


load_dotenv()

DB = os.getenv("DB_PATH")
CHANNEL = int(os.getenv("CHANNEL"))
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@tasks.loop(minutes=14)
async def check_database_activity():    
    if not os.path.exists(DB):
        return

    mtime = os.path.getmtime(DB)
    last_modified = datetime.fromtimestamp(mtime)
    diff = datetime.now() - last_modified

    channel = bot.get_channel(CHANNEL)
    if not channel:
        print("no channel")
        return
    

    if diff.total_seconds() > 1800:
        await channel.send("<@everyone> Database has not been edited for over half an hour!")
        
    elif diff.total_seconds() <= 1800:
        await channel.send("<@everyone> Database is active again and has received new data updates.")

@bot.event
async def on_ready():
    print("Logged in")
    if not check_database_activity.is_running():
        check_database_activity.start()

@bot.command(name="dbstatus")
async def dbstatus(ctx):
    if not os.path.exists(DB):
        await ctx.send(f"Database file not found at: `{DB}`")
        return

    try:
        mtime = os.path.getmtime(DB)
        last_modified = datetime.fromtimestamp(mtime)
        diff = datetime.now() - last_modified
        time_diff = diff.total_seconds() / 1800
        
        embed = discord.Embed(title="Database Monitor", color=discord.Color.blue())
        embed.add_field(name="File", value=f"`{os.path.basename(DB)}`", inline=False)
        embed.add_field(name="Last Modified", value=f"<t:{int(mtime)}:R>", inline=True) # Discord handles relative time dynamically for each user
        
        if time_diff > 1:
            embed.color = discord.Color.red()
            embed.description = f"<@everyone> The database has not been edited for over half an hour!\nLast modified at: `{last_modified.strftime('%Y-%m-%d %H:%M:%S')}`"
        else:
            embed.color = discord.Color.green()
            embed.description = f"<@everyone> The database was recently updated.\nLast modified at: `{last_modified.strftime('%Y-%m-%d %H:%M:%S')}`"
            
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"Error checking database: `{e}`")

bot.run(TOKEN)