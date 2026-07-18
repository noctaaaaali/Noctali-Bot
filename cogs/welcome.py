import os
import discord
from discord.ext import commands

from utils.image_gen import generate_card

WELCOME_CHANNEL_ID = int(os.environ.get("WELCOME_CHANNEL_ID", 0))
LEAVE_CHANNEL_ID = int(os.environ.get("LEAVE_CHANNEL_ID", 0))


class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
        if channel is None:
            print("⚠️ Salon de bienvenue introuvable (vérifie WELCOME_CHANNEL_ID)")
            return

        try:
            buf = await generate_card(member, kind="welcome")
            file = discord.File(buf, filename="welcome.png")
            embed = discord.Embed(
                description=f"**{member.mention}** vient de rejoindre le serveur ! 🎉",
                color=discord.Color.from_rgb(170, 120, 255),
            )
            embed.set_image(url="attachment://welcome.png")
            await channel.send(content=f"👋 Bienvenue {member.mention} !", embed=embed, file=file)
        except Exception as e:
            print(f"Erreur génération image bienvenue : {e}")
            await channel.send(f"👋 Bienvenue {member.mention} sur le serveur !")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        channel = member.guild.get_channel(LEAVE_CHANNEL_ID)
        if channel is None:
            print("⚠️ Salon de départ introuvable (vérifie LEAVE_CHANNEL_ID)")
            return

        try:
            buf = await generate_card(member, kind="leave")
            file = discord.File(buf, filename="leave.png")
            embed = discord.Embed(
                description=f"**{member.name}** a quitté le serveur. 👋",
                color=discord.Color.from_rgb(255, 110, 110),
            )
            embed.set_image(url="attachment://leave.png")
            await channel.send(embed=embed, file=file)
        except Exception as e:
            print(f"Erreur génération image départ : {e}")
            await channel.send(f"👋 **{member.name}** a quitté le serveur.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))

