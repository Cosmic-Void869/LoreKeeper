# LoreKeeper 👑

A Discord bot that learns server culture through message analysis and generates AI-mimicked responses using Markov chain trigrams.

## Features

- **Neural Learning**: Analyzes server messages to build language patterns
- **AI Mimicry**: Generates contextual responses based on server history
- **Server Lore**: Captures and archives memorable quotes
- **Statistics**: Track emoji usage, chat activity, and user profiles
- **15+ Commands**: From `/mimic` to `/roast` to `/poll`

## Requirements

- Python 3.11+
- Discord.py 2.4.0
- A Discord bot token

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/Cosmic-Void869/LoreKeeper.git
cd LoreKeeper
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Setup environment variables

```bash
cp .env.example .env
# Edit .env and add your Discord bot token
```

### 5. Run the bot

```bash
python bot.py
```

## Configuration

All settings are in `.env`:

```bash
TOKEN=your_discord_bot_token
GUILD_ID=your_guild_id  # Optional
ENABLE_RANDOM_RESPONSES=false
RANDOM_REPLY_CHANCE=0.04
MAX_MESSAGE_ARCHIVE=5000
HISTORY_DAYS=30
```

## Commands

- `/help` - View all available commands
- `/mimic` - Generate AI response
- `/stats` - Show neural matrix stats
- `/brainscan` - Index server history (admin only)
- `/quote` - Get random server quote
- `/addquote` - Add a quote
- `/leaderboard` - Top chatters
- `/roast` - AI roast for a user
- `/magic8` - Magic 8-ball
- `/poll` - Create a poll
- `/health` - Bot health check

## Architecture

```
bot.py              Main bot and all commands
server_lore.json    Persistent data storage
requirements.txt    Python dependencies
.env                Configuration (not in git)
```

## Production Deployment

### Docker Setup

```bash
docker build -t lorekeeper .
docker run --env-file .env lorekeeper
```

### Environment Variables

- `TOKEN` - Your Discord bot token (required)
- `GUILD_ID` - Optional: restrict command sync to a specific guild
- `ENABLE_RANDOM_RESPONSES` - Enable random bot replies (default: false)

## Data

- All bot data is stored in `server_lore.json`
- Automatic backups are created to `server_lore.backup.json`
- Data is saved every 5 minutes automatically
- Archive is capped at 5000 messages by default

## Logging

Logs are saved to `lorekeeper.log` and printed to console.

## Future Improvements

- Migrate to SQLite/PostgreSQL
- Add unit tests
- CI/CD pipeline
- Database migrations

## License

MIT

## Author

Cosmic-Void869
