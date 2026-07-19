import os
import io
import json
import asyncio
import discord
from discord.ext import commands
from discord import app_commands

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "games.json")


def load_data() -> dict:
    if not os.path.exists(DATA_PATH):
        return {}
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data: dict):
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class GameReviewModal(discord.ui.Modal):
    strengths = discord.ui.TextInput(
        label="Points forts (optionnel)",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=200,
    )
    weaknesses = discord.ui.TextInput(
        label="Points faibles (optionnel)",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=200,
    )

    def __init__(self, score: int, message_id: int):
        super().__init__(title=f"Note : {score}/10 ⭐")
        self.score = score
        self.message_id = message_id

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        data = load_data()
        key = str(self.message_id)
        game = data.setdefault(key, {"title": "Jeu", "ratings": {}})
        game["ratings"][str(interaction.user.id)] = {
            "score": self.score,
            "strengths": self.strengths.value.strip(),
            "weaknesses": self.weaknesses.value.strip(),
            "username": interaction.user.display_name,
        }
        save_data(data)

        try:
            message = await interaction.channel.fetch_message(self.message_id)
        except discord.NotFound:
            await interaction.followup.send("❌ Message du jeu introuvable.", ephemeral=True)
            return

        embed = message.embeds[0]
        ratings = list(game["ratings"].values())
        avg = sum(r["score"] for r in ratings) / len(ratings)
        embed.set_field_at(
            0, name="⭐ Moyenne", value=f"**{avg:.1f}/10** ({len(ratings)} avis)", inline=False
        )

        lines = []
        for r in sorted(ratings, key=lambda r: -r["score"]):
            line = f"**{r['username']}** — {r['score']}/10"
            if r["strengths"]:
                line += f"\n✅ {r['strengths']}"
            if r["weaknesses"]:
                line += f"\n❌ {r['weaknesses']}"
            lines.append(line)
        reviews_text = "\n\n".join(lines)
        if len(reviews_text) > 1000:
            reviews_text = reviews_text[:1000] + "\n… et d'autres avis"
        embed.set_field_at(
            1,
            name="📋 Points forts / faibles",
            value=reviews_text or "Aucun avis pour l'instant",
            inline=False,
        )

        await message.edit(embed=embed)
        await interaction.followup.send(f"✅ Note enregistrée : {self.score}/10 !", ephemeral=True)


class GameRatingButton(discord.ui.Button):
    def __init__(self, score: int):
        super().__init__(
            label=str(score),
            style=discord.ButtonStyle.secondary,
            custom_id=f"note_jeu_btn_{score}",
            row=0 if score <= 5 else 1,
        )
        self.score = score

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(GameReviewModal(self.score, interaction.message.id))


class GameRatingView(discord.ui.View):
    """Vue persistante — custom_id statiques (note_jeu_btn_1 à 10), un seul enregistrement
    au démarrage couvre tous les jeux postés."""

    def __init__(self):
        super().__init__(timeout=None)
        for i in range(1, 11):
            self.add_item(GameRatingButton(i))


class GameTitleModal(discord.ui.Modal, title="Nouveau jeu à noter"):
    game_title = discord.ui.TextInput(label="Titre du jeu", max_length=100)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"🎮 Envoie maintenant la jaquette de **{self.game_title.value}** "
            f"(en pièce jointe, ici) — t'as 2 minutes !"
        )

        def check(m: discord.Message):
            return (
                m.author.id == interaction.user.id
                and m.channel.id == interaction.channel_id
                and len(m.attachments) > 0
            )

        try:
            msg = await interaction.client.wait_for("message", check=check, timeout=120)
        except asyncio.TimeoutError:
            await interaction.channel.send("⌛ Temps écoulé, relance `/note_jeu` pour réessayer.")
            return

        cover_bytes = await msg.attachments[0].read()
        file = discord.File(io.BytesIO(cover_bytes), filename="cover.png")

        embed = discord.Embed(
            title=f"🎮 {self.game_title.value}",
            color=discord.Color.from_rgb(140, 200, 255),
        )
        embed.set_image(url="attachment://cover.png")
        embed.add_field(name="⭐ Moyenne", value="Pas encore de note", inline=False)
        embed.add_field(
            name="📋 Points forts / faibles", value="Sois le premier à noter !", inline=False
        )
        embed.set_footer(text=f"Ajouté par {interaction.user.display_name}")

        card_message = await interaction.channel.send(
            embed=embed, file=file, view=GameRatingView()
        )

        data = load_data()
        data[str(card_message.id)] = {"title": self.game_title.value, "ratings": {}}
        save_data(data)

        try:
            await msg.delete()
        except (discord.Forbidden, discord.NotFound):
            pass


class Games(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(GameRatingView())

    @app_commands.command(
        name="note_jeu", description="Ajoute un jeu vidéo que tout le serveur peut noter /10"
    )
    async def note_jeu(self, interaction: discord.Interaction):
        await interaction.response.send_modal(GameTitleModal())


async def setup(bot: commands.Bot):
    await bot.add_cog(Games(bot))


