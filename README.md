# Telegram Utility Bot (Txt-to-Html + File Tools)

A Telegram bot with these commands:

| Command | What it does |
|---|---|
| `/start` | Show help |
| `/t2h` | Convert a `.txt` file you send into a `.html` file |
| `/fp` | Send text or a `.txt` file with links; get back only the PDF links as a `.txt` file |
| `/fv` | Same as above, but filters video links (mp4, mkv, avi, mov, webm, etc.) |
| `/mp` | Start collecting PDF files to merge |
| `/smp` | Stop collecting and merge the PDFs you sent into one PDF |
| `/mt` | Start collecting `.txt` files to merge |
| `/smt` | Stop collecting and merge the `.txt` files into one file |
| `/id` | Get your Telegram user ID and chat ID |
| `/t2t` | Send any text and get it back as a `.txt` file |

No database is used — everything is handled in memory per chat, so it's simple and stateless between restarts.

---

## 1. Get a bot token

1. Open Telegram, message **@BotFather**.
2. Send `/newbot`, follow the prompts, and pick a name/username.
3. BotFather will give you a token that looks like `123456789:ABCdefGhIJKlmNoPQRstuVWXyz`. Copy it — you'll need it below. **Never share this token publicly.**

---

## 2. Put the code on GitHub

Render deploys from a Git repository (it doesn't support uploading a zip directly for Web Services). Steps:

1. Create a new **public or private** repository on GitHub (e.g. `telegram-utility-bot`).
2. Upload all the files from this folder to that repo:
   - `bot.py`
   - `app.py`
   - `requirements.txt`
   - `render.yaml`
   - `README.md`

   Easiest way: on GitHub, click **Add file → Upload files**, drag in all the files, and commit.

---

## 3. Deploy on Render

### Option A — one-click Blueprint (recommended, uses `render.yaml`)

1. Go to [render.com](https://render.com) and sign in (free account is fine).
2. Click **New +** → **Blueprint**.
3. Connect your GitHub account and select the repo you just created.
4. Render reads `render.yaml` automatically and shows you the `txt-to-html-bot` service.
5. It will ask you to fill in the `BOT_TOKEN` environment variable — paste the token from BotFather.
6. Click **Apply** / **Create**. Render will build and deploy automatically.

### Option B — manual Web Service

1. Click **New +** → **Web Service**.
2. Connect the same GitHub repo.
3. Settings:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python app.py`
   - **Instance Type**: Free
4. Under **Environment**, add a variable:
   - Key: `BOT_TOKEN`
   - Value: *(paste your token from BotFather)*
5. Click **Create Web Service**.

---

## 4. Confirm it's working

- Watch the **Logs** tab in Render — you should see `Starting bot in polling mode...`.
- Open Telegram, find your bot by its username, and send `/start`.
- Note: Render's free tier spins the service down after ~15 minutes of no HTTP traffic and spins it back up on the next request (this can cause a ~30–60s delay before the bot responds after being idle). This is a free-tier limitation, not a bug in the code.

---

## How it technically works

- The bot uses **long-polling** (it repeatedly asks Telegram for new messages), so it doesn't need a public webhook URL or HTTPS certificate — simpler and avoids Render URL configuration.
- Because Render's free Web Service tier requires something to be listening on a port for health checks, `app.py` starts a one-line Flask server in a background thread solely to satisfy that requirement; all the actual bot logic runs in `bot.py`.
- PDF merging uses the `pypdf` library.
- Files sent/received are handled in temporary files and cleaned up after use — nothing is stored permanently.

## Customizing

- Add more video/PDF extensions: edit `VIDEO_EXTENSIONS` in `bot.py`.
- Change the HTML template: edit `txt_to_html()` in `bot.py`.
- Add new commands: add a handler function and register it near the bottom of `bot.py` in `build_application()`.
