# Noctali Bot 🌙

Bot Discord communautaire : messages de bienvenue / départ avec bannière générée
(pseudo + pp en cercle) dans des salons dédiés.

## 1. Créer l'application Discord

1. Va sur https://discord.com/developers/applications → **New Application**.
2. Onglet **Bot** → **Reset Token** → copie le token (tu ne le reverras qu'une fois).
3. Toujours dans **Bot**, active les **Privileged Gateway Intents** :
   - `SERVER MEMBERS INTENT` (obligatoire pour détecter les arrivées/départs)
   - `MESSAGE CONTENT INTENT`
4. Onglet **OAuth2 > URL Generator** :
   - Scopes : `bot`, `applications.commands`
   - Permissions : `Send Messages`, `Embed Links`, `Attach Files`, `Read Message History`
   - Ouvre le lien généré pour inviter le bot sur ton serveur.

## 2. Préparer les salons

Crée (ou réutilise) deux salons textuels : `#bienvenue` et `#depart`.
Récupère leur ID (active le **mode développeur** dans Discord : Réglages >
Avancés > Mode développeur, puis clic droit sur le salon > **Copier l'identifiant**).

## 3. Mettre le projet sur GitHub

```bash
git init
git add .
git commit -m "Initial commit - Noctali Bot"
git branch -M main
git remote add origin https://github.com/<ton-user>/noctali-bot.git
git push -u origin main
```

⚠️ Le fichier `.env` est ignoré par git (`.gitignore`) — ne mets **jamais**
ton token dans le repo.

## 4. Déployer sur Railway

1. https://railway.app → **New Project** → **Deploy from GitHub repo** →
   sélectionne `noctali-bot`.
2. Railway détecte le `Procfile` et `requirements.txt` automatiquement.
3. Onglet **Variables**, ajoute :
   - `DISCORD_TOKEN`
   - `WELCOME_CHANNEL_ID`
   - `LEAVE_CHANNEL_ID`
4. Déploie. Dans les **Logs**, tu dois voir `✅ Connecté en tant que ...`.

## 5. Tester en local (optionnel)

```bash
python3 -m venv venv
source venv/bin/activate       # Windows : venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           # puis remplis les valeurs
python main.py
```

## Structure du projet

```
noctali-bot/
├── main.py              # point d'entrée du bot
├── keep_alive.py        # petit serveur Flask (garde le bot éveillé)
├── cogs/
│   └── welcome.py        # events on_member_join / on_member_remove
├── utils/
│   └── image_gen.py      # génération des bannières (Pillow)
├── assets/fonts/          # police Poppins utilisée sur les bannières
├── requirements.txt
├── Procfile
└── .env.example
```

## Personnalisation rapide

- **Couleurs des bannières** → dictionnaire `STYLES` dans `utils/image_gen.py`.
- **Texte affiché** (titre, sous-texte) → même fichier, fonction `generate_card`.
- **Prefix des commandes** → `command_prefix="!"` dans `main.py`.
- Pour ajouter d'autres fonctionnalités (modération, économie, rôles...),
  crée simplement un nouveau fichier dans `cogs/` avec une fonction `setup()` —
  il sera chargé automatiquement au démarrage.
