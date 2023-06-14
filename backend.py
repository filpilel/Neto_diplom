from settings import community_token, access_token
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
import operator
import datetime
import time
from random import randint
import data_baze


class BotBack():
    def __init__(self, community_token, access_token):
        self.community_token = community_token
        self.access_token = access_token

        # Создаем объекты для работы с API и длинными запросами
        self.vk_com = vk_api.VkApi(token=self.community_token)
        self.vk_acc = vk_api.VkApi(token=self.access_token)
        self.long_poll = VkLongPoll(self.vk_com)


    """Для отправки сообщений."""

    def send_message(self, user_id, message):
        self.vk_com.method('messages.send',
                      {'user_id': user_id,
                       'message': message,
                       'random_id': 0,
                       })

    """Для отправки выбранных фото."""

    def send_photo(self, user_id, message, selected_user, photo_list):
        attachment = ''
        for photo_id in photo_list:
            attachment += f"photo{selected_user['id']}_{photo_id},"

        self.vk_com.method('messages.send',
                           {'user_id': user_id,
                            'message': message,
                            'attachment': attachment,
                            'random_id': 0
                            })

    """Для получения города."""

    def get_city(self, city):
        values = {
            'country_id': 1,
            'q': city,
            'count': 1
        }
        result = self.vk_acc.method('database.getCities', values=values)
        if result['items']:
            city_id = result['items'][0]['id']
            return city_id
        else:
            return False

    """Функция для расчета возраста."""

    def calculate_age(self, bdate):
        try:
            birth_date = datetime.datetime.strptime(bdate, '%d.%m.%Y')
            age = datetime.datetime.now().year - birth_date.year
            if (datetime.datetime.now().month, datetime.datetime.now().day) < (birth_date.month, birth_date.day):
                age -= 1
        except (TypeError, ValueError):
            return False
        return age

    """Функция для получения информации о пользователе."""

    def get_user_info(self, user_id):
        user_info_dict = {}
        result = self.vk_com.method('users.get',
                                    {'user_id': user_id,
                                     'fields': 'first_name, last_name, bdate, sex, city'
                                     })
        if result:
            res = result[0].items()
            for key, values in res:
                if key == 'is_closed' or key == 'can_access_closed':
                    break
                elif key == 'city':
                    user_info_dict[key] = values['id']
                else:
                    user_info_dict[key] = values
        return user_info_dict

    """Функция для получения дополнительной информации (возраста и города), если они не заполнены в профиле."""

    def get_additional_information(self, user_info):
        user_info = user_info
        for event in self.long_poll.listen():
            if 'bdate' not in user_info or user_info['bdate'].split('.') != 3:
                if 'bdate' in user_info:
                    user_info.pop('bdate')
                self.send_message(event.user_id, "Введите ваш возраст:")
                for event in self.long_poll.listen():
                    if event.type == VkEventType.MESSAGE_NEW:
                        if event.to_me:
                            request_age = event.text.lower().strip()
                            try:
                                user_info['age'] = int(request_age)
                                break
                            except Exception as exc:
                                print(exc)
                                self.send_message(event.user_id, "Неверный формат (введите только цифры):")
                                continue

            if 'city' not in user_info:
                self.send_message(event.user_id, "Введите ваш город:")
                for event in self.long_poll.listen():
                    if event.type == VkEventType.MESSAGE_NEW:
                        if event.to_me:
                            request_city = event.text.lower().strip()
                            if self.get_city(request_city):
                                user_info['city'] = self.get_city(request_city)
                                break
                            else:
                                self.send_message(event.user_id, 'Неверно указан город! Введите правильное полное название:')
                                continue

            return user_info

    """Функция для поиска пользователей."""

    def search_users(self, user_info):
        user_list = []
        search_age = user_info['age'] - 2

        while search_age <= user_info['age'] + 2:
            result = self.vk_acc.method('users.search',
                                        {'age_from': search_age,
                                         'age_to': search_age,
                                         'sex': 3 - user_info['sex'],
                                         'city': user_info['city'],
                                         'status': 1 or 6,
                                         'has_photo': 1,
                                         'count': 30,
                                         'offset': 1
                                         })

            if result and result.get('items'):
                for item in result['items']:
                    if item['is_closed']:
                        continue
                    else:
                        user_list.append(item)

                search_age += 1
                time.sleep(1)

                if len(user_list) >= 30:
                    break

            elif result:
                return 0, user_list
            else:
                return 0, user_list

        return len(user_list), user_list



    """Функция для выбора случайного пользователя из списка пользователей."""

    def get_random_user(self, users_list_range, users_list):
        selected_user = users_list[randint(0, users_list_range - 1)]
        return selected_user


    """Функция для получения топ-фотографий."""

    def get_top_photos(self, selected_user):
        result = self.vk_acc.method('photos.get',
                                    {'owner_id': selected_user['id'],
                                     'album_id': f'profile',
                                     'photo_sizes': 1,
                                     'count': 1000,
                                     'extended': 1
                                     })
        if result:
            return result
        else:
            return False

    """Функция подбора случайного пользователя."""

    def get_final_choice(self, compound, users_list, user_data_baze_id):
        while True:
            selected_user = self.get_random_user(len(users_list), users_list)
            photos_info = self.get_top_photos(selected_user)
            if photos_info.get('count') < 3:
                continue
            if data_baze.check_result_user(compound, selected_user.get('id'), user_data_baze_id):
                return selected_user, photos_info
            else:
                continue

    """Функция выбора 3-х топ-фотографий"""

    def get_most_popular_photo(self, photos_info):
        photo_info_dict = {}
        link_id_list = []

        for items in photos_info.get('items'):
            key = items.get('id')
            photo_info_dict[key] = items.get('likes').get('count') + items.get('comments').get('count')

        photo_info_dict = sorted(photo_info_dict.items(), key=operator.itemgetter(1), reverse=True)[:3]

        for key, values in photo_info_dict:
            link_id_list.append(key)

        return link_id_list


if __name__ == '__main__':
    bot = BotBack(community_token, access_token)
