import asyncio
import re
from telegram import Bot
from telegram.error import TelegramError
from config.settings import g_token, g_chat_id
from logger import *


# TODO: Integrate TeleGram Bot to send alerts and notifications
#   - Use TeleGram Bot API to send alerts to configured channels using Channel ID.
#   - Handle network errors, invalid channel IDs, and other exceptions.


def send_telegram_alert(token=g_token, chat_id=g_chat_id, message="Hello World"):
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
            print("Alert sent successfully")
            log_info(f"Alert sent to channel {chat_id}", message)

        except TelegramError as e:
            print(f"Telegram API error: {e}")
            log_error(f"Error sending Telegram message: ", e)
            raise

        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            log_error(f"Error sending Telegram message: ", e)
            raise

    try:
        asyncio.run(send_message())
    except Exception as e:
        print(f"Error sending Telegram message: {e}")
        log_error(f"Error composing Markdown message: ", e)
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
    if details:
        message += "\n*Details:*\n"
        for key, value in details.items():
            safe_key = escape_markdown(key)
            safe_value = escape_markdown(value)
            message += f"• *{safe_key}*: {safe_value}\n"

    # Add code blocks if provided
    if code_blocks:
        message += "\n*Code Blocks:*\n"
        for language, code in code_blocks.items():
            # Code blocks don't need escaping
            message += f"\n```{language}\n{code}\n```\n"

    return message


