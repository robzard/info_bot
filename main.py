import aiogram
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor, callback_data
import sys

from aiogram.utils.callback_data import CallbackData

TOKEN = sys.argv[1]
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

invite_callback = CallbackData("invite", "action", "group")
send_callback = CallbackData("invite", "action", "group")
group_callback = CallbackData("invite", "action", "group")


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


async def delete_id_in_file(chat_id, file_name='chat'):
    delete = False
    with open(f"{file_name}.txt", "r") as f:
        lines = f.readlines()
    with open(f"{file_name}.txt", "w") as f:
        for line in lines:
            if chat_id not in line.strip("\n"):
                f.write(line)
            delete = True
    if delete:
        return True
    return False


async def get_inline_buttons():
    await create_file_if_not_exists('chats.txt')
    keyboard = types.InlineKeyboardMarkup()
    with open("chats.txt", "r") as f:
        lines = f.readlines()
    list_groups = [el.split(';')[1] for el in lines if ';' in el]
    groups = list(dict.fromkeys(list_groups))
    for group in groups:
        keyboard.add(types.InlineKeyboardButton(group, callback_data=invite_callback.new(action='select_group',
                                                                                         group=group.replace('\n',
                                                                                                             ''))))
    keyboard.add(types.InlineKeyboardButton('Отправить всем',
                                            callback_data=invite_callback.new(action='select_group', group='')))
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
        types.BotCommand("start", "Запустить бота"),
        types.BotCommand("add", "Добавить чат"),
        types.BotCommand("delete", "Удалить чат из рассылки"),
        types.BotCommand("create_group", "Создать новую группу чатов"),
        types.BotCommand("delete_group", "Удалить группу чатов"),
    ])


@dp.message_handler(commands=['start'])
async def process_start_command(message: types.Message):
    await set_default_commands(dp)
    print(message)
    if 'admin_teyla' in message.text:
        await write_id(message.from_user.id.__str__(), 'users')
        await message.answer("Привет!\nОтправь мне любое сообщение и я отправлю его во все чаты!")


@dp.message_handler(commands=['add'])
async def process_start_command(message: types.Message):
    if await have_id(message.from_user.id.__str__(), 'users'):
        await message.reply("Выберите группу для добавления",
                            reply_markup=await get_inline_buttons_delete_groups('add_chat'))


@dp.callback_query_handler(invite_callback.filter(action=["add_chat"]))
async def send_random_value(call: types.CallbackQuery, callback_data: dict):
    if await have_id(call.message.reply_to_message.from_user.id.__str__(), 'users'):
        name_group = callback_data['group'].replace('\n', '')
        if await write_id(call.message.chat.id.__str__() + f";{name_group}" if name_group else '', 'chats'):
            await call.message.answer("Чат добавлен в рассылку!")
        else:
            await call.message.answer("Чат уже был добавлен в рассылку!")


@dp.message_handler(commands=['delete'])
async def process_start_command(message: types.Message):
    if await have_id(message.from_user.id.__str__(), 'users'):
        if await delete_id_in_file(message.chat.id.__str__(), 'chats'):
            await message.answer("Чат удалён!")
        else:
            await message.answer("Такого чата нет в списке рассылок.")


@dp.message_handler(commands=['create_group'])
async def process_start_command(message: types.Message):
    if await have_id(message.from_user.id.__str__(), 'users'):
        name_group = await get_group_chat_name(message.text.replace('\n', ''))
        if await write_id(name_group, 'groups'):
            await bot.send_message(message.chat.id, f'Группа {name_group} добавлена!')
        else:
            await bot.send_message(message.chat.id, f'Группа {name_group} уже присутствует.')


@dp.message_handler(commands=['delete_group'])  # ДОДЕЛАТЬ
async def process_start_command(message: types.Message):
    if await have_id(message.from_user.id.__str__(), 'users'):
        if not message.group_chat_created:
            await message.reply("Выберите группу для удаления",
                                reply_markup=await get_inline_buttons_delete_groups())


@dp.callback_query_handler(invite_callback.filter(action=["select_group"]))
async def send_random_value(call: types.CallbackQuery, callback_data: dict):
    keyboard = types.InlineKeyboardMarkup()
    button_1 = types.InlineKeyboardButton(text="Отправить",
                                          callback_data=send_callback.new(
                                              action='send',
                                              group=callback_data['group'].replace('\n', ''))
                                          )
    button_2 = types.InlineKeyboardButton(text="Не отправлять", callback_data='no_send')
    keyboard.add(button_1).add(button_2)
    # await call.message.reply("Отправить сообщение во все чаты?", reply_markup=keyboard)
    await bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=keyboard)
    print(call.message)


@dp.callback_query_handler(invite_callback.filter(action=["delete_group"]))
async def send_random_value(call: types.CallbackQuery, callback_data: dict):
    keyboard = types.InlineKeyboardMarkup()
    button_1 = types.InlineKeyboardButton(text="Удалить",
                                          callback_data=send_callback.new(
                                              action='delete_group_in_files',
                                              group=callback_data['group'].replace('\n', ''))
                                          )
    button_2 = types.InlineKeyboardButton(text="Не удалять", callback_data='no_delete')
    keyboard.add(button_1).add(button_2)
    # await call.message.reply("Отправить сообщение во все чаты?", reply_markup=keyboard)
    await bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=keyboard)
    print(call.message)


@dp.callback_query_handler(invite_callback.filter(action=["send"]))
async def send_random_value(call: types.CallbackQuery, callback_data: dict):
    print(call)
    count_send_chats = 0
    for chat_id in await get_all_chats():
        if chat_id:
            if callback_data['group'] in chat_id:
                count_send_chats += 1
                group_id = int(chat_id.split(';')[0])
                # await bot.forward_message(group_id, call.message.chat.id, call.message.reply_to_message.message_id)
                await call.message.reply_to_message.send_copy(group_id)
    await bot.delete_message(call.message.chat.id, call.message.message_id)
    await call.message.reply_to_message.reply(
        f'Сообщение отправлено в группу "{callback_data["group"]}".\nКоличество чатов, в которые были направлены сообщения: {count_send_chats}')


@dp.callback_query_handler(invite_callback.filter(action=["delete_group_in_files"]))
async def send_random_value(call: types.CallbackQuery, callback_data: dict):
    print(call)
    if await delete_id_in_file(callback_data['group'], 'groups'):
        await delete_id_in_file(callback_data['group'], 'chats')
        await bot.delete_message(call.message.chat.id, call.message.message_id)
        await call.message.reply_to_message.reply(f"Группа {callback_data['group']} удалена!")
    else:
        await call.message.reply_to_message.reply(f"Группа для удаления {callback_data['group']} не найдена.")


@dp.callback_query_handler(text='no_send')
async def send_random_value(call: types.CallbackQuery):
    await bot.delete_message(call.message.chat.id, call.message.message_id)
    await call.message.reply_to_message.reply("Сообщение не будет отправлено")


@dp.callback_query_handler(text='no_delete')
async def send_random_value(call: types.CallbackQuery):
    await bot.delete_message(call.message.chat.id, call.message.message_id)
    await call.message.reply_to_message.reply("Сообщение не будет удалено")


@dp.message_handler(content_types=aiogram.types.ContentType.all(), from_chat=True)
async def process_start_command(message: types.__all__):
    if message.chat.type == 'private':
        if await have_id(message.from_user.id.__str__(), 'users'):
            if not message.group_chat_created:
                await message.reply("Выберите группу", reply_markup=await get_inline_buttons())


ADMINS = [601610220]


async def on_startup(db):
    print('-START-')
    for admin in ADMINS:
        await bot.send_message(chat_id=admin, text="Чат-бот запущен.")


async def on_shutdown(db):
    print('-END-')
    for admin in ADMINS:
        await bot.send_message(chat_id=admin, text="Я отключён!")
    await bot.close()


if __name__ == '__main__':
    executor.start_polling(dp, on_shutdown=on_shutdown, on_startup=on_startup)
