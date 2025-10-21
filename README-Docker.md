# Deploying Task-Reminder-System with Docker

This repository can be packaged and run inside Docker. The container runs the scheduler (scripts/scheduler.py) which triggers the check daily at 15:30 Asia/Ho_Chi_Minh.

Build and run (local):

```bash
# build image
docker compose build --no-cache

# run
docker compose up -d

# view logs
docker compose logs -f
```

Environment variables

- Copy `.env.example` or your `.env` into the project root. The `docker-compose.yml` uses `env_file: .env` to pass variables into the container.

Notes

- The container's default command is the scheduler. If you prefer to run the check-once, override the command in `docker-compose.yml` to run `python src/main.py --days 1 --past-days 1`.
- The container mounts `./logs` to `/app/logs` so scheduled job output is persisted on the host.
