import os
import re
import html
import logging
import tempfile

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from pypdf import PdfWriter

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

VIDEO_EXTENSIONS = (
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv",
    ".webm", ".m3u8", ".3gp", ".ts", ".mpg", ".mpeg",
)

URL_REGEX = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def reset_mode(context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = None


def txt_to_html(text: str, title: str = "Converted Document") -> str:
    escaped = html.escape(text)
    body = escaped.replace("\n", "<br>\n")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{html.escape(title)}</title>
<style>
body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; line-height: 1.6; }}
</style>
</head>
<body>
<p>{body}</p>
</body>
</html>
"""


def extract_urls(text: str):
    return URL_REGEX.findall(text)


def filter_pdf_urls(text: str):
    urls = extract_urls(text)
    return [u for u in urls if u.split("?")[0].lower().endswith(".pdf")]


def filter_video_urls(text: str):
    urls = extract_urls(text)
    return [u for u in urls if u.split("?")[0].lower().endswith(VIDEO_EXTENSIONS)]


async def send_text_as_file(update: Update, content: str, filename: str, caption: str = None):
    with tempfile.NamedTemporaryFile(mode="w", suffix=os.path.splitext(filename)[1] or ".txt",
                                      delete=False, encoding="utf-8") as f:
        f.write(content)
        path = f.name
    try:
        with open(path, "rb") as f:
            await update.message.reply_document(document=f, filename=filename, caption=caption)
    finally:
        os.remove(path)


# ------------------------------------------------------------------
# Command handlers
# ------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_mode(context)
    await update.message.reply_text(
        "👋 Hi! I'm your file utility bot.\n\n"
        "Available commands:\n"
        "/t2h - Create HTML file from a TXT file\n"
        "/fp - Filter PDF urls and make a TXT file\n"
        "/fv - Filter video urls and make a TXT file\n"
        "/mp - Merge PDF files\n"
        "/smp - Stop PDF merge process\n"
        "/mt - Merge TXT files\n"
        "/smt - Stop TXT merge process\n"
        "/id - Get your Telegram ID\n"
        "/t2t - Create a .txt file of any text\n"
    )


async def t2h_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "await_t2h_file"
    await update.message.reply_text("📂 Send me the .txt file you want converted to HTML.")


async def fp_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "await_fp_input"
    await update.message.reply_text(
        "📄 Send me text or a .txt file containing links. "
        "I'll pull out only the PDF links and give you a .txt file."
    )


async def fv_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "await_fv_input"
    await update.message.reply_text(
        "🎞️ Send me text or a .txt file containing links. "
        "I'll pull out only the video links and give you a .txt file."
    )


async def mp_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "collecting_pdfs"
    context.user_data["pdf_files"] = []
    await update.message.reply_text(
        "📕 Send me the PDF files you want merged, one by one.\n"
        "When you're done, send /smp to merge and receive the result."
    )


async def smp_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    paths = context.user_data.get("pdf_files", [])
    if context.user_data.get("mode") != "collecting_pdfs" or len(paths) < 2:
        await update.message.reply_text(
            "⚠️ You need to start with /mp and send at least 2 PDF files first."
        )
        _cleanup_paths(context.user_data.get("pdf_files", []))
        reset_mode(context)
        context.user_data["pdf_files"] = []
        return

    await update.message.reply_text("⏳ Merging your PDFs...")
    writer = PdfWriter()
    try:
        for p in paths:
            writer.append(p)
        out_path = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False).name
        with open(out_path, "wb") as f:
            writer.write(f)
        with open(out_path, "rb") as f:
            await update.message.reply_document(document=f, filename="merged.pdf")
        os.remove(out_path)
    except Exception as e:
        logger.exception("PDF merge failed")
        await update.message.reply_text(f"❌ Failed to merge PDFs: {e}")
    finally:
        writer.close()
        _cleanup_paths(paths)
        context.user_data["pdf_files"] = []
        reset_mode(context)


async def mt_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "collecting_txts"
    context.user_data["txt_contents"] = []
    await update.message.reply_text(
        "📓 Send me the .txt files you want merged, one by one.\n"
        "When you're done, send /smt to merge and receive the result."
    )


async def smt_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contents = context.user_data.get("txt_contents", [])
    if context.user_data.get("mode") != "collecting_txts" or len(contents) < 2:
        await update.message.reply_text(
            "⚠️ You need to start with /mt and send at least 2 TXT files first."
        )
        context.user_data["txt_contents"] = []
        reset_mode(context)
        return

    merged = "\n\n".join(contents)
    await send_text_as_file(update, merged, "merged.txt", caption="✅ Here's your merged TXT file.")
    context.user_data["txt_contents"] = []
    reset_mode(context)


async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    await update.message.reply_text(
        f"🆔 Your user ID: `{user.id}`\n💬 This chat ID: `{chat.id}`",
        parse_mode="Markdown",
    )


async def t2t_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "await_t2t_text"
    await update.message.reply_text("✍️ Send me the text you want saved as a .txt file.")


def _cleanup_paths(paths):
    for p in paths:
        try:
            os.remove(p)
        except OSError:
            pass


# ------------------------------------------------------------------
# Message handlers (text / documents), routed by current mode
# ------------------------------------------------------------------

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("mode")
    text = update.message.text or ""

    if mode == "await_fp_input":
        urls = filter_pdf_urls(text)
        if not urls:
            await update.message.reply_text("No PDF links found in that text.")
        else:
            await send_text_as_file(update, "\n".join(urls), "pdf_urls.txt",
                                     caption=f"✅ Found {len(urls)} PDF link(s).")
        reset_mode(context)

    elif mode == "await_fv_input":
        urls = filter_video_urls(text)
        if not urls:
            await update.message.reply_text("No video links found in that text.")
        else:
            await send_text_as_file(update, "\n".join(urls), "video_urls.txt",
                                     caption=f"✅ Found {len(urls)} video link(s).")
        reset_mode(context)

    elif mode == "await_t2t_text":
        await send_text_as_file(update, text, "text.txt", caption="✅ Here's your .txt file.")
        reset_mode(context)

    elif mode == "collecting_pdfs":
        await update.message.reply_text("Please send a PDF document, or /smp to finish.")

    elif mode == "collecting_txts":
        await update.message.reply_text("Please send a TXT document, or /smt to finish.")

    else:
        await update.message.reply_text(
            "I didn't understand that. Send /start to see available commands."
        )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("mode")
    doc = update.message.document
    filename = doc.file_name or ""

    if mode == "await_t2h_file":
        if not filename.lower().endswith(".txt"):
            await update.message.reply_text("Please send a .txt file.")
            return
        tg_file = await doc.get_file()
        raw = await tg_file.download_as_bytearray()
        text = raw.decode("utf-8", errors="replace")
        html_content = txt_to_html(text, title=os.path.splitext(filename)[0])
        out_name = os.path.splitext(filename)[0] + ".html"
        await send_text_as_file(update, html_content, out_name, caption="✅ Here's your HTML file.")
        reset_mode(context)

    elif mode in ("await_fp_input", "await_fv_input"):
        tg_file = await doc.get_file()
        raw = await tg_file.download_as_bytearray()
        text = raw.decode("utf-8", errors="replace")
        if mode == "await_fp_input":
            urls = filter_pdf_urls(text)
            out_name = "pdf_urls.txt"
            label = "PDF"
        else:
            urls = filter_video_urls(text)
            out_name = "video_urls.txt"
            label = "video"
        if not urls:
            await update.message.reply_text(f"No {label} links found in that file.")
        else:
            await send_text_as_file(update, "\n".join(urls), out_name,
                                     caption=f"✅ Found {len(urls)} {label} link(s).")
        reset_mode(context)

    elif mode == "collecting_pdfs":
        if not filename.lower().endswith(".pdf"):
            await update.message.reply_text("Please send a PDF file, or /smp to finish.")
            return
        tg_file = await doc.get_file()
        path = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False).name
        await tg_file.download_to_drive(path)
        context.user_data.setdefault("pdf_files", []).append(path)
        count = len(context.user_data["pdf_files"])
        await update.message.reply_text(f"✅ Got it ({count} so far). Send more or /smp to merge.")

    elif mode == "collecting_txts":
        if not filename.lower().endswith(".txt"):
            await update.message.reply_text("Please send a TXT file, or /smt to finish.")
            return
        tg_file = await doc.get_file()
        raw = await tg_file.download_as_bytearray()
        text = raw.decode("utf-8", errors="replace")
        context.user_data.setdefault("txt_contents", []).append(text)
        count = len(context.user_data["txt_contents"])
        await update.message.reply_text(f"✅ Got it ({count} so far). Send more or /smt to merge.")

    else:
        await update.message.reply_text(
            "I received a file, but I'm not sure what to do with it. "
            "Send /start to see available commands."
        )


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

def build_application() -> Application:
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN environment variable is not set. "
            "Set it in your Render service's Environment tab."
        )

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("t2h", t2h_start))
    application.add_handler(CommandHandler("fp", fp_start))
    application.add_handler(CommandHandler("fv", fv_start))
    application.add_handler(CommandHandler("mp", mp_start))
    application.add_handler(CommandHandler("smp", smp_stop))
    application.add_handler(CommandHandler("mt", mt_start))
    application.add_handler(CommandHandler("smt", smt_stop))
    application.add_handler(CommandHandler("id", get_id))
    application.add_handler(CommandHandler("t2t", t2t_start))

    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    return application


def run_bot():
    application = build_application()
    logger.info("Starting bot in polling mode...")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    run_bot()
