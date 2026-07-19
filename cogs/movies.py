import os
import io
import json
import asyncio
import discord
from discord.ext import commands
from discord import app_commands

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "movies.json")


def load_data() -> dict:
    if not os.path.exists(DATA_PATH):
        return {}
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data: dict):
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class ReviewModal(discord.ui.Modal):
    review = discord.ui.TextInput(
        label="Avis (optionnel)",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=300,
    )

    def __init__(self, score: int, message_id: int):
        super().__init__(title=f"Note : {score}/10 ⭐")
        self.score = score
        self.message_id = message_id

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        data = load_data()
        key = str(self.message_id)
        movie = data.setdefault(key, {"title": "Film", "ratings": {}})
        movie["ratings"][str(interaction.user.id)] = {
            "score": self.score,
            "review": self.review.value.strip(),
            "username": interaction.user.display_name,
        }
        save_data(data)

        try:
            message = await interaction.channel.fetch_message(self.message_id)
        except discord.NotFound:
            await interaction.followup.send("❌ Message du film introuvable.", ephemeral=True)
            return

        embed = message.embeds[0]
        ratings = list(movie["ratings"].values())
        avg = sum(r["score"] for r in ratings) / len(ratings)
        embed.set_field_at(
            0, name="⭐ Moyenne", value=f"**{avg:.1f}/10** ({len(ratings)} avis)", inline=False
        )

        lines = []
        for r in sorted(ratings, key=lambda r: -r["score"]):
            line = f"**{r['username']}** — {r['score']}/10"
            if r["review"]:
                line += f" : {r['review']}"
            lines.append(line)
        reviews_text = "\n".join(lines)
        if len(reviews_text) > 1000:
            reviews_text = reviews_text[:1000] + "\n… et d'autres avis"
        embed.set_field_at(
            1, name="📝 Avis", value=reviews_text or "Aucun avis pour l'instant", inline=False
        )

        await message.edit(embed=embed)
        await interaction.followup.send(f"✅ Note enregistrée : {self.score}/10 !", ephemeral=True)


class RatingButton(discord.ui.Button):
    def __init__(self, score: int):
        super().__init__(
            label=str(score),
            style=discord.ButtonStyle.secondary,
            custom_id=f"note_film_btn_{score}",
            row=0 if score <= 5 else 1,
        )
        self.score = score

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ReviewModal(self.score, interaction.message.id))


class MovieRatingView(discord.ui.View):
    """Vue persistante — un seul enregistrement au démarrage couvre tous les films
    grâce aux custom_id statiques (note_film_btn_1 à 10)."""

    def __init__(self):
        super().__init__(timeout=None)
        for i in range(1, 11):
            self.add_item(RatingButton(i))


class MovieTitleModal(discord.ui.Modal, title="Nouveau film à noter"):
    movie_title = discord.ui.TextInput(label="Titre du film", max_length=100)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"🎬 Envoie maintenant l'affiche de **{self.movie_title.value}** "
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
            await interaction.channel.send("⌛ Temps écoulé, relance `/note_film` pour réessayer.")
            return

        poster_bytes = await msg.attachments[0].read()
        file = discord.File(io.BytesIO(poster_bytes), filename="poster.png")

        embed = discord.Embed(
            title=f"🎬 {self.movie_title.value}",
            color=discord.Color.from_rgb(255, 170, 210),
        )
        embed.set_image(url="attachment://poster.png")
        embed.add_field(name="⭐ Moyenne", value="Pas encore de note", inline=False)
        embed.add_field(name="📝 Avis", value="Sois le premier à noter !", inline=False)
        embed.set_footer(text=f"Ajouté par {interaction.user.display_name}")

        card_message = await interaction.channel.send(
            embed=embed, file=file, view=MovieRatingView()
        )

        data = load_data()
        data[str(card_message.id)] = {"title": self.movie_title.value, "ratings": {}}
        save_data(data)

        try:
            await msg.delete()
        except (discord.Forbidden, discord.NotFound):
            pass


class Movies(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(MovieRatingView())

    @app_commands.command(
        name="note_film", description="Ajoute un film que tout le serveur peut noter /10"
    )
    async def note_film(self, interaction: discord.Interaction):
        await interaction.response.send_modal(MovieTitleModal())


async def setup(bot: commands.Bot):
    await bot.add_cog(Movies(bot))
