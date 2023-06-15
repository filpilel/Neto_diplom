from vk_api.longpoll import VkEventType

from backend import BotBack
from settings import community_token, access_token, compound

from data_baze import get_user_data_baze_id, insert_user
import psycopg2

bot_back = BotBack(community_token, access_token)

def handle_search_request(event):
    user_info = bot_back.get_user_info(event.user_id)
    if not user_info:
        return

    if len(user_info) != 6 or len(user_info['bdate'].split('.')) != 3:
        bot_back.send_message(event.user_id, "Недостаточно информации, пожалуйста, дайте ответы на вопросы ниже...")
        user_info = bot_back.get_additional_information(user_info)
    else:
        user_info['age'] = bot_back.calculate_age(user_info['bdate'])
        user_info.pop('bdate', None)

    if not user_info:
        return

    try:
        user_data_baze_id = insert_user(compound, user_info)
    except psycopg2.errors.UniqueViolation:
        compound.rollback()
        user_data_baze_id = get_user_data_baze_id(compound, str(user_info['id']))
    except Exception as exc:
        user_data_baze_id = False
        print(exc)

    if not user_data_baze_id:
        return

    bot_back.send_message(event.user_id, "Отлично, ищу кандидата. Подождите секундочку...")

    try:
        search_users_range, search_users_list = bot_back.search_users(user_info)
        if not search_users_range:
            bot_back.send_message(event.user_id, "К сожалению я не нашел кандидатов, подходящих под ваши параметры, попробуйте выбрать другой город.")
            return

        bot_back.send_message(event.user_id, f"По вашим параметрам я нашел {search_users_range} потенциальных страниц, ищу наилучший профиль...")

        selected_user, photos_info = bot_back.get_final_choice(compound, search_users_list, user_data_baze_id)

        try:
            insert_user(compound, user_data_baze_id)
        except Exception as exc:
            print(exc)

        photos_link = bot_back.get_most_popular_photo(photos_info)
        bot_back.send_photo(event.user_id, f"Кандидат на знакомство - {selected_user.get('first_name')} {selected_user.get('last_name')}\n"
                                           f"Ссылка: https://vk.com/id{selected_user.get('id')}\n"
                                           f"Топ-3 популярные фотографии:", selected_user, photos_link)
    except Exception as exc:
        print(exc)
        bot_back.send_message(event.user_id, "Произошла ошибка при поиске пользователя, попробуйте еще раз.")

def handle_new_message(event):
    if event.text.lower().strip() == "поиск":
        handle_search_request(event)
    else:
        bot_back.send_message(event.user_id, f"Я подберу вам анкету. Введите 'поиск', чтобы начать искать анкету.")

def botfront():
    for event in bot_back.long_poll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            handle_new_message(event)

if __name__ == '__main__':
    botfront()
