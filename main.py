# -*- coding: utf-8 -*-
import asyncio
import logging
import sys
from datetime import datetime, timedelta

import aiogram.types
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.types import MediaGroup, ContentType
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import filters
from aiogram.dispatcher.filters import Command
from aiogram.types import ReplyKeyboardRemove, \
    ReplyKeyboardMarkup, KeyboardButton, \
    InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.callback_data import CallbackData
from aiogram.dispatcher.handler import CancelHandler
from aiogram.utils.exceptions import MessageToDeleteNotFound
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apschedulermiddleware import SchedulerMiddleware

# asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

invite_callback = CallbackData("invite", "action", "group")
send_callback = CallbackData("invite", "action", "group")
group_callback = CallbackData("invite", "action", "group")

logging.basicConfig(level=logging.INFO)

TOKEN = sys.argv[1]
bot = Bot(token=TOKEN)

dp = Dispatcher(bot, storage=MemoryStorage())
scheduler = AsyncIOScheduler(timezone="Asia/Yekaterinburg")

send_button = KeyboardButton('Отправить', callback_data='send')
cancel_button = KeyboardButton('Отмена', callback_data='cancel')
markup_send = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False).row(send_button, cancel_button)

send_message_button = KeyboardButton('Отправить сообщение', callback_data='send')
create_group_button = KeyboardButton('Создать группу чатов', callback_data='send')
delete_group_button = KeyboardButton('Удалить группу чатов', callback_data='cancel')
markup_menu = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False).add(send_message_button).row(
    create_group_button,
    delete_group_button)

send_now = KeyboardButton('Отправить сейчас', callback_data='send')
send_time = KeyboardButton('Указать время отправки', callback_data='read_time')
markup_choose_time = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False).add(send_now).row(send_time)


class MediaStates(StatesGroup):
    waiting_for_media = State()


class CreateGroupChat(StatesGroup):
    create_group_chat = State()


class DeleteGroupChat(StatesGroup):
    delete_group_chat = State()


class SelectGroup(StatesGroup):
    select_group = State()


class ReadTime(StatesGroup):
    read_time = State()
    read_time_message = State()
    read_time_read_text = State()
    read_time_buttons = State()


class MyMiddleware(BaseMiddleware):
    async def on_process_message(self, message: types.Message, data: dict):
        if 'command' in data.keys():
            if 'admin_teyla' in data['command'].text:
                return
        if not await have_id(message.from_user.id.__str__(), 'users'):
            raise CancelHandler()


async def send_message_time(bot: Bot, message: types.Message, data: dict, state: FSMContext, date_send: str):
    sended_messages = ''
    media_group = MediaGroup()
    media_group_docs = MediaGroup()
    groups = await get_chats_from_group(data['group'][0])
    if not groups:
        await message.answer(f'В группе "{data["group"][0]}" отсутствуют добавленые чаты.', reply_markup=markup_menu)
        raise CancelHandler
    for m in data['media']:
        if m['type'] in ('photo', 'video'):
            media_group.attach(m)
        elif m['type'] == 'document':
            media_group_docs.attach(m)
        elif m['type'] == 'caption':
            for group in groups:
                msg = await bot.send_message(chat_id=group, text=m['media'])
                sended_messages = await get_sended_messages(sended_messages, msg)
    if media_group.media:
        for group in groups:
            msg = await bot.send_media_group(chat_id=group, media=media_group)
            sended_messages = await get_sended_messages(sended_messages, msg)
    if media_group_docs.media:
        for group in groups:
            msg = await bot.send_media_group(chat_id=group, media=media_group_docs)
            sended_messages = await get_sended_messages(sended_messages, msg)
    await message.answer(
        f'Сообщение отправлено в группу "{data["group"][0]}".\nКоличество чатов, в которые были направлены сообщения: {len(groups)}\nУказанное время для отправки: {date_send}',
        reply_markup=markup_menu)
    text = data.get('msg_for_send') + ';' + sended_messages
    await write_line_to_file('sended_msg', text)

async def get_groups_list():
    with open("groups.txt", "r") as f:
        lines = f.readlines()
    list_groups = [el.replace('\n', '') for el in lines]
    groups = list(dict.fromkeys(list_groups))
    return groups


async def get_sended_msg(reply_message_id: str):
    with open("sended_msg.txt", "r") as f:
        lines = f.readlines()
    list_groups = [el.replace('\n', '') for el in lines]
    for el in list_groups:
        if reply_message_id in el:
            return el


async def get_chats_from_group(group):
    groups = []
    for chat_id in await get_all_chats():
        if chat_id:
            group_id = int(chat_id.split(';')[0])
            if group == 'Отправить всем' or (group in chat_id):
                groups.append(group_id)
    return groups


async def write_id(id, filename):
    if not await have_id(id, filename):
        with open(f"{filename}.txt", "a+") as f:
            f.write(id + '\n')
        return True
    return False


async def write_line_to_file(filename, text: str):
    with open(f"{filename}.txt", "a+") as f:
        f.write(text + '\n')


async def have_id(id, filename):
    await create_file_if_not_exists("chats.txt")
    await create_file_if_not_exists("users.txt")
    await create_file_if_not_exists("groups.txt")
    with open(f"{filename}.txt", "r+") as f:
        f_text = f.read()
    if id in f_text:
        return True
    return False


async def create_file_if_not_exists(filename):
    with open(filename, 'a+') as f:
        pass


async def get_all_chats():
    with open("chats.txt", "r+") as f:
        f_text = f.read()
    if f_text:
        return f_text.split('\n')
    else:
        return []


async def delete_id_in_file(chat_id, file_name='chat'):
    delete = False
    with open(f"{file_name}.txt", "r") as f:
        lines = f.readlines()
    with open(f"{file_name}.txt", "w") as f:
        for line in lines:
            if chat_id in line.strip("\n"):
                delete = True
            if chat_id not in line.strip("\n"):
                f.write(line)
    if delete:
        return True
    return False


async def get_inline_buttons(album=None):
    album = [el.photo[-1].file_id for el in album].__str__()
    if album is None:
        album = []
    await create_file_if_not_exists('chats.txt')
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    with open("chats.txt", "r") as f:
        lines = f.readlines()
    list_groups = [el.split(';')[1] for el in lines if ';' in el]
    groups = list(dict.fromkeys(list_groups))
    for group in groups:
        keyboard.add(types.KeyboardButton(group))
    keyboard.add(types.InlineKeyboardButton('Отправить всем'))
    return keyboard


async def get_keyboard_buttons_delete_groups(select_group_for_send_message=False):
    await create_file_if_not_exists('groups.txt')
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    with open("groups.txt", "r") as f:
        lines = f.readlines()
    list_groups = [el for el in lines]
    groups = list(dict.fromkeys(list_groups))
    for group in groups:
        keyboard.add(types.KeyboardButton(group))
    if select_group_for_send_message:
        keyboard.row(types.KeyboardButton('Отправить всем'))
    keyboard.row(types.KeyboardButton('Назад в меню'))
    return keyboard


async def get_inline_buttons_delete_groups(type_action='delete_group'):
    await create_file_if_not_exists('groups.txt')
    keyboard = types.InlineKeyboardMarkup()
    with open("groups.txt", "r") as f:
        lines = f.readlines()
    list_groups = [el for el in lines]
    groups = list(dict.fromkeys(list_groups))
    for group in groups:
        keyboard.add(types.InlineKeyboardButton(group, callback_data=invite_callback.new(action=type_action,
                                                                                         group=group.replace('\n',
                                                                                                             ''))))
    return keyboard


async def get_group_chat_name(text):
    split_text = text.split(' ')
    if len(split_text) > 0:
        return ' '.join(split_text[1:])
    return None


async def set_default_commands(dp):
    await dp.bot.set_my_commands([
        types.BotCommand("add", "Добавить чат"),
        types.BotCommand("delete", "Удалить чат из рассылки"),
        types.BotCommand("delete_message", "Удалить сообщение со всех чатов"),
    ])


async def get_menu_keyboard():
    return ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False).add(types.KeyboardButton('Назад в меню'))


@dp.message_handler(Command('start'))
async def send_welcome(message: types.Message):
    await set_default_commands(dp)
    if 'admin_teyla' in message.text:
        await write_id(message.from_user.id.__str__(), 'users')
        await message.answer("Привет!\nВыбери действие.", reply_markup=markup_menu)


@dp.message_handler(commands=['add'])
async def process_start_command(message: types.Message):
    if await have_id(message.from_user.id.__str__(), 'users'):
        await message.reply("Выберите группу для добавления",
                            reply_markup=await get_inline_buttons_delete_groups('add_chat'))


@dp.message_handler(commands=['delete_message'])
async def process_start_command(message: types.Message):
    if await have_id(message.from_user.id.__str__(), 'users'):
        if message.reply_to_message:
            reply_message_id = str(message.reply_to_message.message_id)
            reply_chat_id = str(message.reply_to_message.chat.id)
            data = await get_sended_msg(reply_chat_id + ':' + reply_message_id)
            try:
                data = data.split(';')
            except AttributeError:
                await message.answer('Не удаётся произвести удаление по данному сообщению.')
                return
            i = 0
            for el in data[1:-1]:
                msg = el.split(':')
                try:
                    await bot.delete_message(msg[0], msg[1])
                    i+=1
                except MessageToDeleteNotFound:
                    chat = await bot.get_chat(msg[0])
                    await message.answer(f'Сообщение уже было удалено с чата "{chat.full_name}".')
                    await asyncio.sleep(0.1)
            await message.reply_to_message.reply(f'Сообщений удалено: "{i}"')
        else:
            await message.answer('Выберите сообщение, которое необходимо удалить.')

@dp.message_handler(commands=['delete'])
async def process_start_command(message: types.Message):
    if await have_id(message.from_user.id.__str__(), 'users'):
        if await delete_id_in_file(message.chat.id.__str__(), 'chats'):
            await message.answer("Чат удалён!")
        else:
            await message.answer("Такого чата нет в списке рассылок.")


@dp.callback_query_handler(invite_callback.filter(action=["add_chat"]))
async def send_random_value(call: types.CallbackQuery, callback_data: dict):
    if await have_id(call.message.reply_to_message.from_user.id.__str__(), 'users'):
        name_group = callback_data['group'].replace('\n', '')
        if await write_id(call.message.chat.id.__str__() + f";{name_group}" if name_group else '', 'chats'):
            await call.message.answer("Чат добавлен в рассылку!")
        else:
            await call.message.answer("Чат уже был добавлен в рассылку!")


@dp.message_handler(lambda message: message.text == "Назад в меню",
                    state=[DeleteGroupChat.delete_group_chat,
                           DeleteGroupChat.delete_group_chat,
                           CreateGroupChat.create_group_chat,
                           MediaStates.waiting_for_media,
                           SelectGroup.select_group,
                           ReadTime.read_time_message,
                           ReadTime.read_time,
                           ReadTime.read_time_read_text,
                           ReadTime.read_time_buttons])
async def send_welcomes1(message: types.Message, state: FSMContext):
    await message.delete()
    msg = await message.answer("Отмена действия - возвращение в меню", reply_markup=markup_menu)
    await state.finish()


@dp.message_handler(lambda message: message.text == "Отправить сообщение")
async def send_welcomes(message: types.Message):
    await create_file_if_not_exists("sended_msg.txt")
    await message.delete()
    await message.answer("Выберите группу", reply_markup=await get_keyboard_buttons_delete_groups(True))
    # await SelectGroup.select_group.set()
    await ReadTime.read_time.set()


@dp.message_handler(state=ReadTime.read_time)
async def send_welcomes(message: types.Message, state: FSMContext):
    await message.answer('Укажите тип отправки', reply_markup=markup_choose_time)
    await ReadTime.read_time_message.set()
    await state.update_data(group=message.text)


@dp.message_handler(lambda message: message.text == "Указать время отправки", state=ReadTime.read_time_message)
async def send_welcomes(message: types.Message, state: FSMContext):
    # await message.delete()
    if message.text != 'Отправить сейчас':
        await message.answer("Укажите время в формате.\nПример - '19.03.2023 18:00'",
                             reply_markup=await get_menu_keyboard())
    data = await state.get_data()
    await state.finish()
    await SelectGroup.select_group.set()
    await state.update_data(group=data['group'])


# @dp.message_handler(state=ReadTime.read_time_read_text)
# async def send_welcomes(message: types.Message, state: FSMContext):
#     await state.finish()
#     await SelectGroup.select_group.set()
#     await state.update_data(qwer='qwe')


@dp.message_handler(state=[SelectGroup.select_group, ReadTime.read_time_message])
async def send_welcomes(message: types.Message, state: FSMContext):
    data = await state.get_data()
    group = data['group']
    if group in await get_groups_list():
        await message.answer(f'Отправьте сообщения, которые необходимо переслать в группу "{group}"',
                             reply_markup=await get_menu_keyboard())
    elif group == 'Отправить всем':
        await message.answer(f'Отправьте сообщения, которые необходимо переслать во все группы',
                             reply_markup=await get_menu_keyboard())
    else:
        await message.answer(f'Группа "{group}" не найдена!', reply_markup=markup_menu)
        await state.finish()
        raise CancelHandler

    await state.finish()
    current_media = await MediaStates.waiting_for_media.set()
    current_media = await Dispatcher.get_current().current_state().get_data()
    current_media = current_media.get('group', [])
    current_media.append(group)
    if message.text == 'Отправить сейчас':
        await state.update_data(group=current_media)
    else:
        await state.update_data(group=current_media, date_send=message.text)


@dp.message_handler(lambda message: message.text == "Создать группу чатов")
async def send_welcomes(message: types.Message):
    await message.delete()
    await message.answer('Напишите название группы:', reply_markup=await get_menu_keyboard())
    await CreateGroupChat.create_group_chat.set()


@dp.message_handler(state=CreateGroupChat.create_group_chat)
async def send_welcomes(message: types.Message, state: FSMContext):
    name_group = message.text
    if await write_id(name_group, 'groups'):
        await bot.send_message(message.chat.id, f'Группа {name_group} добавлена!', reply_markup=markup_menu)
    else:
        await bot.send_message(message.chat.id, f'Группа {name_group} уже присутствует.', reply_markup=markup_menu)
    await state.finish()


@dp.message_handler(lambda message: message.text == "Удалить группу чатов")
async def send_welcomes(message: types.Message):
    await message.delete()
    if not message.group_chat_created:
        await message.answer("Выберите группу для удаления",
                             reply_markup=await get_keyboard_buttons_delete_groups())
    await DeleteGroupChat.delete_group_chat.set()


@dp.message_handler(state=DeleteGroupChat.delete_group_chat)
async def send_welcomes(message: types.Message, state: FSMContext):
    group = message.text
    if await delete_id_in_file(group, 'groups'):
        await delete_id_in_file(group, 'chats')
        await message.answer(f"Группа {group} удалена!", reply_markup=markup_menu)
    else:
        await message.answer(f"Группа для удаления {group} не найдена.", reply_markup=markup_menu)
    await state.finish()


@dp.message_handler(lambda message: message.text == "Отправить", state=MediaStates.waiting_for_media)
async def send_welcomesw(message: types.Message, state: FSMContext):
    sended_messages = ''
    await message.delete()
    data = await state.get_data()
    if data.get('date_send', None):
        try:
            date_send = datetime.strptime(data.get('date_send'), '%d.%m.%Y %H:%M')
        except Exception as ex:
            await message.answer('Указан неверный формат даты, попробуйте снова.', reply_markup=markup_menu)
            await state.finish()
        scheduler.add_job(send_message_time, trigger='date', run_date=date_send,
                          kwargs={'bot': bot, 'message': message, 'data': data, 'state': state,
                                  'date_send': date_send.strftime('%d.%m.%Y %H:%M')})
        await message.answer(
            f'Сообщение будет отправлено в группу "{data["group"][0]}" в {date_send.strftime("%d.%m.%Y %H:%M")}',
            reply_markup=markup_menu)
        await state.finish()
    else:
        media_group = MediaGroup()
        media_group_docs = MediaGroup()
        groups = await get_chats_from_group(data['group'][0])
        if not groups:
            await message.answer(f'В группе "{data["group"][0]}" отсутствуют добавленые чаты.',
                                 reply_markup=markup_menu)
            await state.finish()
            raise CancelHandler
        for m in data['media']:
            if m['type'] in ('photo', 'video'):
                media_group.attach(m)
            elif m['type'] == 'document':
                media_group_docs.attach(m)
            elif m['type'] == 'caption':
                for group in groups:
                    msg = await bot.send_message(chat_id=group, text=m['media'])
                    sended_messages = await get_sended_messages(sended_messages, msg)
        if media_group.media:
            for group in groups:
                msg = await bot.send_media_group(chat_id=group, media=media_group)
                sended_messages = await get_sended_messages(sended_messages, msg)
        if media_group_docs.media:
            for group in groups:
                msg = await bot.send_media_group(chat_id=group, media=media_group_docs)
                sended_messages = await get_sended_messages(sended_messages, msg)
        await state.finish()
        await message.answer(
            f'Сообщение отправлено в группу "{data["group"][0]}".\nКоличество чатов, в которые были направлены сообщения: {len(groups)}',
            reply_markup=markup_menu)
        text = data.get('msg_for_send') + ';' + sended_messages
        await write_line_to_file('sended_msg', text)


async def get_sended_messages(sended_messages, msg: types.Message):
    try:
        sended_messages += str(msg.chat.id) + ':' + str(msg.message_id) + ';'
    except AttributeError:
        for el in msg:
            sended_messages += str(el.chat.id) + ':' + str(el.message_id) + ';'
    return sended_messages

@dp.message_handler(lambda message: message.text == "Отмена", state=MediaStates.waiting_for_media)
async def send_welcomes(message: types.Message, state: FSMContext):
    await message.delete()
    await state.finish()
    await message.answer('Отправка отменена', reply_markup=markup_menu)


@dp.message_handler(content_types=[ContentType.PHOTO, ContentType.VIDEO, ContentType.DOCUMENT, ContentType.TEXT],
                    state=MediaStates.waiting_for_media)
async def handle_media(message: types.Message, state: FSMContext):
    current_media = await state.get_data()
    group = current_media['group']
    current_media = current_media.get('media', [])

    if message.text:
        current_media.append({"media": message.text, "type": "caption"})

    if message.photo:
        current_media.append({"media": message.photo[-1].file_id, "type": "photo"})
    elif message.video:
        current_media.append({"media": message.video.file_id, "type": "video"})
    elif message.document:
        current_media.append({"media": message.document.file_id, "type": "document"})
    if message.caption:
        current_media.append({"media": message.caption, "type": "caption"})

    msg_for_send = f'{message.chat.id}:{message.message_id}'

    await state.update_data(media=current_media, group=group, msg_for_send=msg_for_send)
    await message.reply(f"Добавлено в сообщение для рассылки", reply_markup=markup_send)


if __name__ == '__main__':
    dp.middleware.setup(MyMiddleware())
    dp.middleware.setup(SchedulerMiddleware(scheduler))
    scheduler.start()
    executor.start_polling(dp, skip_updates=True)
