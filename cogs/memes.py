import random
import aiohttp
import discord
from discord.ext import commands
from discord import app_commands

SUBREDDITS = [
    "memes",
    "dankmemes",
    "wholesomememes",
    "ProgrammerHumor",
    "funny",
    "me_irl",
    "meirl",
    "AdviceAnimals",
    "terriblefacebookmemes",
    "SimpsonsShitposting",
    "HistoryMemes",
    "gamingmemes",
    "Animemes",
    "MarvelMemes",
    "comedyheaven",
    "BlackPeopleTwitter",
    "whitepeopletwitter",
    "ComedyCemetery",
    "shitposting",
    "cursedcomments",
    "surrealmemes",
]
HEADERS = {"User-Agent": "NoctaliBot/1.0"}


class Memes(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _fetch_meme(self):
        for _ in range(4):  # jusqu'à 4 essais sur des sous-reddits différents
            subreddit = random.choice(SUBREDDITS)
            url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=75"

            async with aiohttp.ClientSession(headers=HEADERS) as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status != 200:
                        continue
                    data = await resp.json()

            posts = [
                p["data"]
                for p in data["data"]["children"]
                if not p["data"].get("over_18")
                and not p["data"].get("stickied")
                and p["data"].get("url", "").lower().endswith((".jpg", ".jpeg", ".png", ".gif"))
            ]
            if posts:
                return random.choice(posts)

        return None

    @app_commands.command(name="meme", description="Envoie un meme random")
    async def meme(self, interaction: discord.Interaction):
        await interaction.response.defer()

        post = await self._fetch_meme()
        if not post:
            await interaction.followup.send("❌ Pas réussi à trouver un meme, réessaie.")
            return

        embed = discord.Embed(title=post.get("title", "Meme"), color=discord.Color.orange())
        embed.set_image(url=post["url"])
        embed.set_footer(text=f"r/{post.get('subreddit', '?')} • 👍 {post.get('ups', 0)}")
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Memes(bot))

