import re
from bot import LOGGER
from bot.config import Telegram
from bot.helper.database import Database
from bot.helper.file_size import get_readable_file_size
from bot.helper.index import get_messages
from bot.helper.media import is_media
from bot.telegram import StreamBot
from pyrogram import filters, Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from os.path import splitext
from pyrogram.errors import FloodWait
from pyrogram.enums.parse_mode import ParseMode
from asyncio import sleep
from urllib.parse import quote_plus
from bot.telegram.plugins.lazydevprop import get_name, get_hash

db = Database()


@StreamBot.on_message(filters.command('start') & filters.private)
async def start(bot: Client, message: Message):
    if "file_" in message.text:
        try:
            usr_cmd = message.text.split("_")[-1]
            data = usr_cmd.split("-")
            message_id, chat_id = data[0], f"-{data[1]}"
            file = await bot.get_messages(int(chat_id), int(message_id))
            media = is_media(file)
            await message.reply_cached_media(file_id=media.file_id, caption=f'**{media.file_name}**')
        except Exception as e:
            print(f"An error occurred: {e}")


@StreamBot.on_message(filters.command('index'))
async def start(bot: Client, message: Message):
    channel_id = message.chat.id
    AUTH_CHANNEL = await db.get_variable('auth_channel')
    if AUTH_CHANNEL is None or AUTH_CHANNEL.strip() == '':
        AUTH_CHANNEL = Telegram.AUTH_CHANNEL
    else:
        AUTH_CHANNEL = [channel.strip() for channel in AUTH_CHANNEL.split(",")]
    if str(channel_id) in AUTH_CHANNEL:
        try:
            last_id = message.id
            start_message = (
                "🔄 Please perform this action only once at the beginning of Surf-Tg usage.\n\n"
                "📋 File listing is currently in progress.\n\n"
                "🚫 Please refrain from sending any additional files or indexing other channels until this process completes.\n\n"
                "⏳ Please be patient and wait a few moments."
            )

            wait_msg = await message.reply(text=start_message)
            files = await get_messages(message.chat.id, 1, last_id)
            await db.add_btgfiles(files)
            await wait_msg.delete()
            done_message = (
                "✅ All your files have been successfully stored in the database. You're all set!\n\n"
                "📁 You don't need to index again unless you make changes to the database."
            )

            await bot.send_message(chat_id=message.chat.id, text=done_message)
        except FloodWait as e:
            LOGGER.info(f"Sleeping for {str(e.value)}s")
            await sleep(e.value)
            await message.reply(text=f"Got Floodwait of {str(e.value)}s",
                                disable_web_page_preview=True, parse_mode=ParseMode.MARKDOWN)
    else:
        await message.reply(text="Channel is not in AUTH_CHANNEL")


@StreamBot.on_message(
    filters.channel
    & (
        filters.document
        | filters.video
    )
)
async def file_receive_handler(bot: Client, message: Message):
    channel_id = message.chat.id
    AUTH_CHANNEL = await db.get_variable('auth_channel')
    if AUTH_CHANNEL is None or AUTH_CHANNEL.strip() == '':
        AUTH_CHANNEL = Telegram.AUTH_CHANNEL
    else:
        AUTH_CHANNEL = [channel.strip() for channel in AUTH_CHANNEL.split(",")]
    if str(channel_id) in AUTH_CHANNEL:
        try:
            file = message.video or message.document
            title = file.file_name or message.caption or file.file_id
            title, _ = splitext(title)
            title = re.sub(r'[.,|_\',]', ' ', title)
            msg_id = message.id
            hash = file.file_unique_id[:6]
            size = get_readable_file_size(file.file_size)
            type = file.mime_type
            await db.add_tgfiles(str(channel_id), str(msg_id), str(hash), str(title), str(size), str(type))
        except FloodWait as e:
            LOGGER.info(f"Sleeping for {str(e.value)}s")
            await sleep(e.value)
            await message.reply(text=f"Got Floodwait of {str(e.value)}s",
                                disable_web_page_preview=True, parse_mode=ParseMode.MARKDOWN)
    else:
        await message.reply(text="Channel is not in AUTH_CHANNEL")

@StreamBot.on_message(
        filters.private & (filters.document | filters.video | filters.audio) & ~filters.command(['start','users','broadcast','batch','genlink','stats'])
        )
async def lazymsg(client: Client, message: Message):
    try:
        txtLazyDeveloper = await message.reply_text("Please Wait...!", quote = True)

        reply_markup = InlineKeyboardMarkup(
            [
            [InlineKeyboardButton("📂 ᴅᴏᴡɴʟᴏᴀᴅ / sᴛʀᴇᴀᴍ 🍿", callback_data=f'generate_stream_link')],
            ]
            )

        await txtLazyDeveloper.edit(f"<b>📂 ᴛᴇʟᴇɢʀᴀᴍ ғɪʟᴇ:</b>", reply_markup=reply_markup, disable_web_page_preview = True)
    except Exception as LazyDeveloper:
        LOGGER.info(LazyDeveloper)

@StreamBot.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
   try:
        data = query.data
        if data.startswith("generate_stream_link"):
            try:
                xo = await query.message.reply_text(f'🔐')
                user_id = query.from_user.id
                username =  query.from_user.mention
                file = getattr(query.message.reply_to_message, query.message.reply_to_message.media.value)
                file_id = file.file_id
                lazy_msg = await client.send_cached_media(
                    chat_id=Telegram.STREAM_LOGS, 
                    file_id=file_id,
                )

                fileName = {quote_plus(get_name(lazy_msg))}
                lazy_stream = f"{Telegram.LAZY_DOMAIN_NAME}play/{str(lazy_msg.id)}/{quote_plus(get_name(lazy_msg))}?hash={get_hash(lazy_msg)}"
                lazy_download = f"{Telegram.LAZY_DOMAIN_NAME}lazy/{str(lazy_msg.id)}/{quote_plus(get_name(lazy_msg))}?hash={get_hash(lazy_msg)}"

                
                await sleep(1)
                await xo.delete()

                await lazy_msg.reply_text(
                    text=f"🍿 ʟɪɴᴋ ɢᴇɴᴇʀᴀᴛᴇᴅ  🧩\n\n<blockquote>⏳Direct Download link:\n{lazy_download}</blockquote>\n<blockquote>📺Watch Online\n{lazy_stream}</blockquote>\n🧩User Id: {user_id} \n👮‍♂️ UserName: {username}",
                    quote=True,
                    disable_web_page_preview=True,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("web Download", url=lazy_download),  # we download Link
                                                        InlineKeyboardButton('▶Stream online', url=lazy_stream)]])  # web stream Link
                )
                
                await query.message.edit_text(
                    text=f"🍿 ʟɪɴᴋ ɢᴇɴᴇʀᴀᴛᴇᴅ 🧩\n\n<blockquote>⏳Direct Download link:\n{lazy_download}</blockquote>\n<blockquote>📺Watch Online\n{lazy_stream}</blockquote>",
                    disable_web_page_preview=True,
                    reply_markup=InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton("web Download", url=lazy_download),  # we download Link
                            InlineKeyboardButton('▶Stream online', url=lazy_stream)
                        ],
                        ])  # web stream Link
                )
            except Exception as LazyDeveloper:
                await query.answer(f"☣something went wrong sweetheart\n\n{LazyDeveloper}", show_alert=True)
                return 
    
   except Exception as LazyDeveloper:
       LOGGER.info(LazyDeveloper)