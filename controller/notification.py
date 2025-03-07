import asyncio
import re
from telegram import Bot
from telegram.error import TelegramError
#from config.settings import g_token, g_chat_id
from mylogger import *



def send_telegram_alert(token="7364825288:AAGA-xxXNJYMGxcxOy4MrmonyoSsA1USAtw", chat_id="5398524142", message="Hello World"):
    """
    Send an alert or a notification to a specified Telegram channel.

    Parameters:
    - token: str - The Telegram Bot token.
    - channel_id: str - The target channel ID.
    - message: str - The Markdown formatted message to send.
    """

    async def send_message():

        try:
            bot = Bot(token=token)
            await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
            logger.info(f"Alert sent to channel {chat_id}: {message}")

        except TelegramError as e:
            logger.error(f"Error sending Telegram message: {e}")
            raise

        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            raise

    try:
        asyncio.run(send_message())
    except Exception as e:
        logger.error(f"Error composing Markdown message: {e}")
        raise



def compose_markdown_message(title: str, text: str, details: dict = None, code_blocks: dict = None) -> str:
    """
    Compose a customized Markdown formatted message with minimal character escaping.

    Parameters:
    - title: str - The title of the message.
    - text: str - The main content of the message.
    - details: dict (optional) - Additional details to include in the message.
    - code_blocks: dict (optional) - Code blocks to include, where key is the language and value is the code.

    Returns:
    - A string with Markdown formatting.
    """
    def escape_markdown(text):
        """Escape special characters for Markdown."""
        #escape_chars = r'_*[]()~`>#+-=|{}.!'
        escape_chars = '_*[]()~`>#+-='
        return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', str(text))

    # Escape and format title and text
    safe_title = escape_markdown(title)
    safe_text = escape_markdown(text)
    
    message = f"*{safe_title}*\n\n{safe_text}\n"

    # Add details if provided
    message += "\n*Details:*\n"
    if details:
        for key, value in details.items():
            safe_key = escape_markdown(key)
            safe_value = escape_markdown(value)
            message += f"• *{safe_key}*: {safe_value}\n"

    # Add code blocks if provided
    if code_blocks:
        for language, code in code_blocks.items():
            # Code blocks don't need escaping
            message += f"\n```{language}\n{code}\n```\n"

    return message


