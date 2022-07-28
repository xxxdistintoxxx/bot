from random import randrange
import os
from dotenv import load_dotenv
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from tableSearch import find_user, insert_user, change_user
from addFoundUser import add_user, user_in_db

class Vk:
    def __init__(self):
        load_dotenv('tokens.env')
        self.interface_token = os.getenv('VK_COMMUNITY_TOKEN_FULL')
        self.search_token = os.getenv('USER_TOKEN')
        self.interface_vk = vk_api.VkApi(token=self.interface_token)
        self.search_vk = vk_api.VkApi(token=self.search_token)
        self.longpoll = VkLongPoll(self.interface_vk)
        self.vk_session = self.search_vk.get_api()
        self.age = False
        self.sex = False
        self.town = False
        self.stat = False



    def write_text_message(self, user_id, message):
        self.interface_vk.method('messages.send', {'user_id': user_id, 'message': message, 'random_id': randrange(10 ** 7)})


    def send_photo_message(self, user_id, name, surname, users_id, photos):
        text = f'Человек найден ✅\nИмя: {name}\nФамилия: {surname}\nСсылка на профиль: vk.com/id{users_id}'

        self.interface_vk.method("messages.send", {"user_id": user_id, "message": text, "attachment": photos, 'random_id': randrange(10 ** 7)})


    def normalize_request(self, string):
        string = string.lower()
        string = string.strip()
        return string


    def search(self):
        result = self.vk_session.users.search(sort=0, count=1000, fields='deactivated, is_closed, counters, sex', hometown=self.town, sex=self.sex, status=self.stat, age_from=self.age - 3, age_to=self.age + 3, has_photo=1, )
        for i in result['items']:
            if not i['is_closed']:
                nums = self.vk_session.users.get(user_ids=i['id'], fields='counters')[0]['counters']
                id = self.vk_session.users.get(user_ids=i['id'], fields='counters')[0]['id']
                photo_amount = nums['photos']
                if photo_amount >= 3 and not user_in_db(id):
                    photos = self.vk_session.photos.getProfile(owner_id=id)['items']
                    list_of_photos = []
                    result = []
                    name = i['first_name']
                    surname = i['last_name']
                    for i in photos:
                        list_of_photos.append(i['id'])
                    for i in list_of_photos:
                        information = self.vk_session.photos.getById(photos=f'{id}_{i}', extended=1)
                        amout_of_likes = information[0]['likes']
                        link = information[0]['orig_photo']['url']
                        result.append({'photo_id': i, 'user_id': id, 'likes': amout_of_likes['count'], 'link': link})
                    result.sort(key=lambda i: i['likes'], reverse=True)
                    result = result[0:3]
                    link_list = [i['link'] for i in result]
                    photo_string = f'photo{result[0]["user_id"]}_{result[0]["photo_id"]},photo{result[1]["user_id"]}_{result[1]["photo_id"]},photo{result[2]["user_id"]}_{result[2]["photo_id"]}'
                    return name, surname, photo_string, id, link_list
        return None, None, None, None, None

    def start(self):
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW:
                if event.to_me:
                    request = event.text
                    user_id = event.user_id
                    result = find_user(user_id)
                    if result == 1:
                        try:
                            age = int(request)
                            change_user(user_id, 2, 'age', age)
                            self.age = age
                            self.write_text_message(event.user_id, f'Второй вопрос:\nКакого ты пола?\n(1 - мужского\n2 - женского)')
                        except ValueError:
                            self.write_text_message(event.user_id, f'Напиши целое число')
                    elif result == 2:
                        if request == '1' or request == '2':
                            sex = int(request)
                            change_user(user_id, 3, 'sex', sex)
                            self.sex = sex
                            self.write_text_message(event.user_id, f'Третий вопрос:\nВ каком городе ты живешь?')
                        else:
                            self.write_text_message(event.user_id, f'введи 1 или 2')
                    elif result == 3:
                        town = request
                        change_user(user_id, 4, 'town', town)
                        self.town = town
                        self.write_text_message(event.user_id, f'Четвертый вопрос:\nКакое у тебя семейное положение?\n(1 - не в браке\n2 - встречаешься\n3 - помолвлен\n4 - в браке\n5 - всё сложно\n6 - в активном поиске\n7 - влюблен\n8 - в гражданском браке)')
                    elif result == 4:
                        try:
                            request = int(request)
                            if request >= 1 and request <= 8:
                                stat = request
                                change_user(user_id, -1, 'stat', stat)
                                self.stat = stat
                                self.write_text_message(event.user_id, f'Итак, результаты:')
                                name, surname, photos, users_id, links_list = self.search()
                                if name is None:
                                    self.write_text_message(event.user_id, 'К сожалению пользователи не найдены 😕\nДля следующего поиска введите любой символ')
                                else:
                                    self.send_photo_message(event.user_id, name, surname, users_id, photos)
                                    add_user(self.age, self.sex, self.town, self.stat, name, surname, links_list[0], links_list[1], links_list[2], users_id)

                                    self.write_text_message(event.user_id,'Для следующего поиска введите любой символ')
                            else:
                                self.write_text_message(event.user_id, f'Введи цифру от 1 до 8')
                        except ValueError:
                            self.write_text_message(event.user_id, f'Напиши целое число')

                    elif result == -1:
                        self.write_text_message(event.user_id, f'Тебе надо пройти небольшой опрос, для того, чтобы я смог осуществить поиск 🔍')
                        self.write_text_message(event.user_id, f'Первый вопрос:\nСколько тебе лет?')
                        change_user(user_id, 1, None, None)

                    else:
                        self.write_text_message(event.user_id, f'Привет 👋\nЯ бот, который находит похожих людей')
                        insert_user(user_id)
                        self.write_text_message(event.user_id, f'Тебе надо пройти небольшой опрос, для того, чтобы я смог осуществить поиск 🔍')
                        self.write_text_message(event.user_id, f'Первый вопрос:\nСколько тебе лет?')

