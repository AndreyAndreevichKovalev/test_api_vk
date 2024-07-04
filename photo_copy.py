import os
import json
from datetime import datetime

import requests

from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()


class VK:
    def __init__(self, access_token, user_id, version='5.131'):
        self.token = access_token
        self.id = user_id
        self.version = version
        self.params = {'access_token': self.token, 'v': self.version}

    def get_photos(self, album_id='profile', count=5):
        url = 'https://api.vk.com/method/photos.get'
        params = {
            'owner_id': self.id,
            'album_id': album_id,
            'extended': 1,
            'photo_sizes': 1,
            'count': count
        }
        response = requests.get(url, params={**self.params, **params})
        response_json = response.json()
        print(response_json)
        if 'error' in response_json:
            raise Exception(
                f"Error fetching photos: {response_json['error']['error_msg']}"
            )
        return response_json.get('response', {}).get('items', [])


class YandexDisk:
    def __init__(self, token):
        self.token = token
        self.base_url = 'https://cloud-api.yandex.net/v1/disk'

    def upload_file(self, disk_file_path, file_url):
        headers = {'Authorization': f'OAuth {self.token}'}
        upload_url = f"{self.base_url}/resources/upload"
        params = {'path': disk_file_path, 'url': file_url}
        response = requests.post(upload_url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()

    def create_folder(self, folder_path):
        headers = {'Authorization': f'OAuth {self.token}'}
        url = f"{self.base_url}/resources"
        params = {'path': folder_path}
        response = requests.put(url, headers=headers, params=params)
        if response.status_code != 201 and response.status_code != 409:
            response.raise_for_status()
        return response.json()


def main():
    vk_token = os.getenv('VK_TOKEN')
    yandex_token = input("Введите токен доступа Яндекс.Диск: ")
    user_id = input("Введите id пользователя VK: ")
    num_photos = int(input("Введите количество фотографий для сохранения: "))

    vk = VK(vk_token, user_id)
    yandex = YandexDisk(yandex_token)

    folder_path = f'backup_vk_photos_{user_id}'
    try:
        yandex.create_folder(folder_path)
    except requests.exceptions.HTTPError as err:
        print(f"Error creating folder: {err}")
        return

    try:
        photos = vk.get_photos(count=num_photos)
    except Exception as err:
        print(f"Error getting photos: {err}")
        return

    if not photos:
        print("No photos to upload.")
        return

    photos_info = []
    file_names = {}

    for photo in tqdm(photos, desc="Uploading photos"):
        max_size_photo = max(photo['sizes'], key=lambda x: x['width'] * x['height'])
        likes_count = photo['likes']['count']
        date_uploaded = datetime.fromtimestamp(photo['date']).strftime('%Y%m%d')

        if likes_count in file_names:
            file_name = f"{likes_count}_{date_uploaded}.jpg"
        else:
            file_name = f"{likes_count}.jpg"
            file_names[likes_count] = 1

        disk_file_path = f"{folder_path}/{file_name}"

        try:
            yandex.upload_file(disk_file_path, max_size_photo['url'])
            photos_info.append({"file_name": file_name, "size": max_size_photo['type']})
        except requests.exceptions.HTTPError as err:
            print(f"Error uploading {file_name}: {err}")

    with open('photos_info.json', 'w') as file:
        json.dump(photos_info, file, ensure_ascii=False, indent=4)

    print("Photos and info file have been successfully uploaded.")


if __name__ == "__main__":
    main()
