# -*- coding: utf-8 -*-
import logging
import sys

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

invite_callback = CallbackData("invite", "action", "group")
send_callback = CallbackData("invite", "action", "group")
group_callback = CallbackData("invite", "action", "group")

logging.basicConfig(level=logging.INFO)

TOKEN = sys.argv[1]
bot = Bot(token=TOKEN)

dp = Dispatcher(bot, storage=MemoryStorage())


send_button = KeyboardButton('Отправить', callback_data='send')
cancel_button = KeyboardButton('Отмена', callback_data='cancel')
markup_send = ReplyKeyboardMarkup(resize_keyboard=True).row(send_button, cancel_button)

send_message_button = KeyboardButton('Отправить сообщение', callback_data='send')
create_group_button = KeyboardButton('Создать группу чатов', callback_data='send')
delete_group_button = KeyboardButton('Удалить группу чатов', callback_data='cancel')
markup_menu = ReplyKeyboardMarkup(resize_keyboard=True).add(send_message_button).row(create_group_button,
                                                                                     delete_group_button)


class MediaStates(StatesGroup):
    waiting_for_media = State()


class CreateGroupChat(StatesGroup):
    create_group_chat = State()


class DeleteGroupChat(StatesGroup):
    delete_group_chat = State()


class SelectGroup(StatesGroup):
    select_group = State()


class MyMiddleware(BaseMiddleware):
    async def on_process_message(self, message: types.Message, data: dict):
        if 'command' in data.keys():
            if 'admin_teyla' in data['command'].text:
                return
        if not await have_id(message.from_user.id.__str__(), 'users'):
            raise CancelHandler()


async def get_groups_list():
    with open("groups.txt", "r") as f:
        lines = f.readlines()
    list_groups = [el.replace('\n', '') for el in lines]
    groups = list(dict.fromkeys(list_groups))
    return groups

async def get_chats_from_group(group):
    groups = []
    for chat_id in await get_all_chats():
        if chat_id:
            if group in chat_id:
                group_id = int(chat_id.split(';')[0])
                groups.append(group_id)
    return groups


async def write_id(id, filename):
    if not await have_id(id, filename):
        with open(f"{filename}.txt", "a+") as f:
            f.write(id + '\n')
        return True
    return False


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
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    with open("chats.txt", "r") as f:
        lines = f.readlines()
    list_groups = [el.split(';')[1] for el in lines if ';' in el]
    groups = list(dict.fromkeys(list_groups))
    for group in groups:
        keyboard.add(types.KeyboardButton(group))
    keyboard.add(types.InlineKeyboardButton('Отправить всем'))
    return keyboard


async def get_keyboard_buttons_delete_groups():
    await create_file_if_not_exists('groups.txt')
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    with open("groups.txt", "r") as f:
        lines = f.readlines()
    list_groups = [el for el in lines]
    groups = list(dict.fromkeys(list_groups))
    for group in groups:
        keyboard.add(types.KeyboardButton(group))
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
    ])


async def get_menu_keyboard():
    return ReplyKeyboardMarkup(resize_keyboard=True).add(types.KeyboardButton('Назад в меню'))


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
                           SelectGroup.select_group])
async def send_welcomes1(message: types.Message, state: FSMContext):
    await message.delete()
    await message.answer("Отмена действия - возвращение в меню", reply_markup=markup_menu)
    await state.finish()


@dp.message_handler(lambda message: message.text == "Отправить сообщение")
async def send_welcomes(message: types.Message):
    await message.delete()
    await message.answer("Выберите группу", reply_markup=await get_keyboard_buttons_delete_groups())
    await SelectGroup.select_group.set()


@dp.message_handler(state=SelectGroup.select_group)
async def send_welcomes(message: types.Message, state: FSMContext):
    group = message.text
    if message.text in await get_groups_list():
        await message.answer(f'Отправьте сообщения, которые необходимо переслать в группу "{group}"',
                             reply_markup=await get_menu_keyboard())
    else:
        await message.answer(f'Группа "{message.text}" не найдена!', reply_markup=markup_menu)
        await state.finish()
        raise CancelHandler

    await state.finish()
    current_media = await MediaStates.waiting_for_media.set()
    current_media = await Dispatcher.get_current().current_state().get_data()
    current_media = current_media.get('group', [])
    current_media.append(message.text)
    await state.update_data(group=current_media)


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
async def send_welcomes(message: types.Message, state: FSMContext):
    await message.delete()
    data = await state.get_data()
    media_group = MediaGroup()
    media_group_docs = MediaGroup()
    groups = await get_chats_from_group(data['group'])
    if not groups:
        await message.answer(f'В группе "{data["group"]}" отсутствуют добавленые чаты.', reply_markup=markup_menu)
        await state.finish()
        raise CancelHandler
    for m in data['media']:
        if m['type'] in ('photo', 'video'):
            media_group.attach(m)
        elif m['type'] == 'document':
            media_group_docs.attach(m)
        elif m['type'] == 'caption':
            for group in groups:
                await bot.send_message(chat_id=group, text=m['media'])
    if media_group.media:
        for group in groups:
            await bot.send_media_group(chat_id=group, media=media_group)
    if media_group_docs.media:
        for group in groups:
            await bot.send_media_group(chat_id=group, media=media_group_docs)
    await state.finish()
    await message.answer(f'Сообщение отправлено в группу "{data["group"]}".\nКоличество чатов, в которые были направлены сообщения: {len(groups)}', reply_markup=markup_menu)


@dp.message_handler(lambda message: message.text == "Отмена", state=MediaStates.waiting_for_media)
async def send_welcomes(message: types.Message, state: FSMContext):
    await message.delete()
    await state.finish()
    await message.answer('Отправка отменена', reply_markup=markup_menu)


@dp.message_handler(content_types=[ContentType.PHOTO, ContentType.VIDEO, ContentType.DOCUMENT, ContentType.TEXT],
                    state=MediaStates.waiting_for_media)
async def handle_media(message: types.Message, state: FSMContext):
    current_media = await state.get_data()
    group = current_media['group'][0]
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

    await state.update_data(media=current_media, group=group)
    await message.reply(f"Добавлено в сообщение для рассылки", reply_markup=markup_send)


if __name__ == '__main__':
    dp.middleware.setup(MyMiddleware())
    executor.start_polling(dp, skip_updates=True)
