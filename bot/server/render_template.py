import re
from aiofiles import open as aiopen
from os import path as ospath

from bot import LOGGER
from bot.config import Telegram
from bot.helper.database import Database
from bot.helper.exceptions import InvalidHash
from bot.helper.file_size import get_readable_file_size
from bot.server.file_properties import get_file_ids
from bot.telegram import StreamBot
import logging
import urllib
import aiofiles
import aiohttp

db = Database()

admin_block = """
                    <style>
                        .admin-only {
                            display: none;
                        }
                    </style>"""

hide_channel = """
                    <style>
                        .hide-channel {
                            display: none;
                        }
                    </style>"""


async def render_page(id, secure_hash, is_admin=False, html='', playlist='', database='', route='', redirect_url='', msg='', chat_id=''):
    theme = await db.get_variable('theme')
    if theme is None or theme == '':
        theme = Telegram.THEME
    tpath = ospath.join('bot', 'server', 'template')
    if route == 'login':
        async with aiopen(ospath.join(tpath, 'login.html'), 'r') as f:
            html = (await f.read()).replace("<!-- Error -->", msg or '').replace("<!-- Theme -->", theme.lower()).replace("<!-- RedirectURL -->", redirect_url)
    elif route == 'home':
        async with aiopen(ospath.join(tpath, 'home.html'), 'r') as f:
            html = (await f.read()).replace("<!-- Print -->", html).replace("<!-- Theme -->", theme.lower()).replace("<!-- Playlist -->", playlist)
            if not is_admin:
                html += admin_block
                if Telegram.HIDE_CHANNEL:
                    html += hide_channel
    elif route == 'playlist':
        async with aiopen(ospath.join(tpath, 'playlist.html'), 'r') as f:
            html = (await f.read()).replace("<!-- Theme -->", theme.lower()).replace("<!-- Playlist -->", playlist).replace("<!-- Database -->", database).replace("<!-- Title -->", msg).replace("<!-- Parent_id -->", id)
            if not is_admin:
                html += admin_block
    elif route == 'index':
        async with aiopen(ospath.join(tpath, 'index.html'), 'r') as f:
            html = (await f.read()).replace("<!-- Print -->", html).replace("<!-- Theme -->", theme.lower()).replace("<!-- Title -->", msg).replace("<!-- Chat_id -->", chat_id)
            if not is_admin:
                html += admin_block
    
    else:
        file_data = await get_file_ids(StreamBot, chat_id=int(chat_id), message_id=int(id))
        if file_data.unique_id[:6] != secure_hash:
            LOGGER.info('Link hash: %s - %s', secure_hash,
                        file_data.unique_id[:6])
            LOGGER.info('Invalid hash for message with - ID %s', id)
            raise InvalidHash
        filename, tag, size = file_data.file_name, file_data.mime_type.split(
            '/')[0].strip(), get_readable_file_size(file_data.file_size)
        if filename is None:
            filename = "Proper Filename is Missing"
        filename = re.sub(r'[,|_\',]', ' ', filename)
        if tag == 'video':
            async with aiopen(ospath.join(tpath, 'video.html')) as r:
                poster = f"/api/thumb/{chat_id}?id={id}"
                html = (await r.read()).replace('<!-- Filename -->', filename).replace("<!-- Theme -->", theme.lower()).replace('<!-- Poster -->', poster).replace('<!-- Size -->', size).replace('<!-- Username -->', StreamBot.me.username)
        else:
            async with aiopen(ospath.join(tpath, 'dl.html')) as r:
                html = (await r.read()).replace('<!-- Filename -->', filename).replace("<!-- Theme -->", theme.lower()).replace('<!-- Size -->', size)
    return html

async def render_lazy_page(id, secure_hash):
    file_data=await get_file_ids(StreamBot, int(Telegram.STREAM_LOGS), int(id))
    if file_data.unique_id[:6] != secure_hash:
        logging.debug(f'link hash: {secure_hash} - {file_data.unique_id[:6]}')
        logging.debug(f"Invalid hash for message with - ID {id}")
        raise InvalidHash
    src = urllib.parse.urljoin(Telegram.LAZY_DOMAIN_NAME, f'{secure_hash}{str(id)}')
    if str(file_data.mime_type.split('/')[0].strip()) == 'video':
        async with aiopen('bot/server/template/lazystream.html') as r:
            heading = 'Watch {}'.format(file_data.file_name)
            tag = file_data.mime_type.split('/')[0].strip()
            html = (await r.read()).replace('tag', tag) % (heading, file_data.file_name, src)
    elif str(file_data.mime_type.split('/')[0].strip()) == 'audio':
        async with aiopen('bot/server/template/lazystream.html') as r:
            heading = 'Listen {}'.format(file_data.file_name)
            tag = file_data.mime_type.split('/')[0].strip()
            html = (await r.read()).replace('tag', tag) % (heading, file_data.file_name, src)
    else:
        async with aiopen('bot/server/template/dl.html') as r:
            async with aiohttp.ClientSession() as s:
                async with s.get(src) as u:
                    heading = 'Download {}'.format(file_data.file_name)
                    file_size = humanbytes(int(u.headers.get('Content-Length')))
                    html = (await r.read()) % (heading, file_data.file_name, src, file_size)
    return html

def humanbytes(size):
    if not size:
        return ""
    power = 2**10
    n = 0
    Dic_powerN = {0: ' ', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + 'B'
