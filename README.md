# Telegram Bot Host

Multi-bot hosting server for Telegram bots with support for both **webhook** and **polling** modes.

## Features

- Host 50+ Telegram bots simultaneously
- Support for both Webhook and Long Polling modes
- PostgreSQL database for bot persistence
- RESTful Admin API with JWT authentication
- Automatic bot recovery on restart
- Concurrent polling with configurable limits
- Docker deployment ready

## Quick Start

### 1. Configure Environment

```bash
cp .env.example .env
# Edit .env with your values
```

Required settings:
- `DATABASE_URL` - PostgreSQL connection string
- `ADMIN_SECRET_KEY` - Strong secret for admin API
- `WEBHOOK_BASE_URL` - Public HTTPS URL for webhooks (required for webhook mode)

### 2. Run with Docker Compose

```bash
docker-compose up -d
```

This starts:
- PostgreSQL database on port 5432
- Bot host server on port 8000

### 3. Add Your First Bot

```bash
# Login to get JWT token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"secret_key": "your-admin-secret-key"}'

# Add a bot (use the token from above)
curl -X POST http://localhost:8000/api/bots \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "token": "123456789:ABCDEF_YOUR_BOT_TOKEN",
    "username": "my_bot",
    "mode": "polling"
  }'

# Start the bot
curl -X POST http://localhost:8000/api/bots/BOT_ID/start \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## API Endpoints

### Authentication
- `POST /api/auth/login` - Get JWT token

### Bot Management
- `GET /api/bots` - List all bots
- `POST /api/bots` - Create new bot
- `GET /api/bots/{id}` - Get bot details
- `PUT /api/bots/{id}` - Update bot config
- `DELETE /api/bots/{id}` - Delete bot
- `POST /api/bots/{id}/start` - Activate bot
- `POST /api/bots/{id}/stop` - Deactivate bot
- `POST /api/bots/{id}/switch-mode` - Switch webhook/polling
- `GET /api/bots/{id}/logs` - Get bot logs

### Webhook
- `POST /webhook/{bot_token}` - Receive Telegram updates
- `GET /health` - Health check

## Webhook Setup

For webhook mode, you need:
1. A public HTTPS domain
2. Set `WEBHOOK_BASE_URL` in .env (e.g., `https://api.yourdomain.com`)
3. Telegram will send updates to `https://api.yourdomain.com/webhook/{bot_token}`

For local development, use ngrok:
```bash
ngrok http 8000
# Use the https URL in WEBHOOK_BASE_URL
```

## Project Structure

```
telegram-bot-host/
├── main.py                 # FastAPI app entry point
├── requirements.txt        # Python dependencies
├── .env.example           # Environment template
├── Dockerfile             # Container image
├── docker-compose.yml     # Multi-container deployment
├── alembic.ini            # Migration config
├── migrations/            # Database migrations
└── app/
    ├── config.py          # Settings management
    ├── database.py        # DB connection
    ├── models.py          # SQLAlchemy models
    ├── schemas.py         # Pydantic schemas
    ├── bot_manager.py     # Bot lifecycle management
    ├── webhook_handler.py # Webhook processing
    ├── polling_worker.py  # Polling background tasks
    └── routers/
        ├── webhook.py     # Webhook endpoints
        └── admin.py       # Admin API endpoints
```

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start server
uvicorn main:app --reload
```

## Bot Development

Create custom bots by extending the base handler in `bot_manager.py` or by adding handlers directly in the webhook/polling processing.

## License

MIT