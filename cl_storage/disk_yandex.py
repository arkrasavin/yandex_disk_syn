import os
from typing import Dict, List, Optional

import requests
from requests import RequestException
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from loader import path_to_dir_disk, api_key, path_to_local_dir
from config_data.config import logger


class BaseSession:

    def __init__(self, retries: int = 3, backoff_factor: float = 1, headers: Optional = None):
        """
        Инициализация BaseSession.

        :param retries : Количество повторных попыток запроса в случае неудачи.
        :param backoff_factor : Фактор обратного отката, определяющий интервал между повторными попытками запросов.
        :param headers : Дополнительные заголовки, которые будут использоваться по умолчанию для всех запросов.
        """
        self.session = self.session_with_request(retries, backoff_factor)
        self.headers = headers or {}


    def session_with_request(self, retries: int = 3, backoff_factor: float = 1) -> requests.Session:
        """
        Создание сессии с настройками для повторных попыток запроса.

        :param retries: Количество повторных попыток.
        :param backoff_factor: Фактор обратного отката при повторных попытках.
        :return: Настроенная сессия Session.
        """
        session = requests.session()
        retry = Retry(connect=retries, backoff_factor=backoff_factor)
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('https://', adapter)
        return session


    def request(self, method: str, url: str, **kwargs):
        """
        Универсальный метод для выполнения HTTP-запросов с использованием созданной сессии.

        :param method: HTTP-метод (GET, POST, PUT, DELETE и т.д.).
        :param url: URL для запроса.
        :param kwargs: Дополнительные параметры для requests.request.
        :return: Ответ сервера.
        """
        kwargs.setdefault('headers', self.headers)
        return self.session.request(method, url, **kwargs)


    def close(self):
        """Закрытие сессии."""
        self.session.close()


class YandexDisk(BaseSession):

    def __init__(self, token: str = api_key, folder_backup: str = path_to_local_dir):
        """
        Инициализация YandexDisk класса.

        :param token: Токен для доступа к Яндекс диску.
        :param folder_backup: Путь к бэкап папке.
        """
        super().__init__()
        self.token: str = token
        self.folder_backup: str = folder_backup
        # self.session_adapter: requests.Session = self.session_with_request()
        self.base_url: str = 'https://cloud-api.yandex.net/v1/disk/resources'
        self.headers.update({'Authorization': f'OAuth {self.token}'})
        self.list_files_cloud: List[str] = []


    def get_full_path(self, path_file: str) -> str:
        """
        Получение полного пути к локальному файлу.

        :param path_file: Имя файла.
        :return: Полный путь к файлу в локальной файловой системе.
        """
        return os.path.abspath(os.path.join(self.folder_backup, path_file))


    def get_all_files_cloud(self) -> List[str]:
        """
        Получение списка всех файлов в облачном хранилище.

        :return: Список строк с именами файлов, хранящихся в облаке.
        """
        params: Dict[str, str] = {
            'path': path_to_dir_disk,
            'fields': 'items',
        }
        try:
            response = self.request('GET', self.base_url, params=params)
            response.raise_for_status()
            json_response = response.json().get("_embedded").get("items")
            self.list_files_cloud = [item.get("name") for item in json_response]
            return self.list_files_cloud

        except RequestException as error:
            logger.error(f'Ошибка при получении списка файлов облачного хранилища: {error}')
            return []


    def get_hash_file(self, file_name: str) -> Optional[str]:
        """
        Получение MD5-хэша файла из облачного хранилища.

        :param file_name: Имя файла.
        :return: Строка с хэшом MD5 файла, если успешно; иначе None.
        """
        params: Dict[str, str] = {
            'path': f'{path_to_dir_disk}/{file_name}',
            'fields': 'md5',
        }
        try:
            response = self.request('GET', self.base_url, params=params)
            response.raise_for_status()
            return response.json().get('md5')

        except RequestException as error:
            logger.error(f'Ошибка при получении хэша файла {file_name}: {error}')
            return None


    def check_exists_file_storage(self, file_name: str) -> bool:
        """
        Проверка, существует ли файл в облачном хранилище.

        :param file_name: Имя файла.
        :return: True, если файл существует в облаке; иначе False.
        """
        params: Dict[str, str] = {
            'path': f'{path_to_dir_disk}/{file_name}'
        }
        try:
            response = self.request('GET', self.base_url, params=params)
            return response.status_code == 200

        except RequestException as error:
            logger.error(f'Возникла ошибка при проверке существования файла {file_name}: {error}')
            return False


    def load(self, name_file: str, flag: bool = False) -> None:
        """
        Загрузка и перезапись файла в облачный диск.

        :param name_file: Имя файла загрузки.
        :param flag: Указывает, нужно ли перезаписывать файл в облаке ('true' или 'false').
        :return: None
        """
        full_local_path = self.get_full_path(name_file)
        if not os.path.isfile(full_local_path):
            logger.info(f'Файл {name_file} по пути {full_local_path} не существует')
            return

        url_upload = f'{self.base_url}/upload'
        params: Dict[str, str] = {
            'path': f'{path_to_dir_disk}/{name_file}',
            'overwrite': f'{flag}',
        }
        try:
            response = self.request('GET', url_upload, params=params)
            response.raise_for_status()
            link_upload = response.json().get('href')
            logger.info(f'Ссылка для загрузки получена: {link_upload}')

            with open(full_local_path, 'rb') as file:
                result = self.request('PUT', link_upload, data=file)
                logger.info(f'Загрузка {name_file} завершена с кодом {result}.')

        except RequestException as error:
            logger.error(f'Ошибка HTTP: {error}')


    def delete(self, name_file: str) -> None:
        """
        Удаление файла безвозвратно из облачного хранилища.

        :param name_file: Имя файла для удаления.
        :return: None
        """
        params: Dict[str, str] = {
            'path': f'{path_to_dir_disk}/{name_file}',
            'permanently': 'true',
        }
        try:
            response = self.request('DELETE', self.base_url, params=params)
            response.raise_for_status()
            if response.status_code == 204:
                logger.info('Удаление прошло успешно.')
            elif response.status_code == 202:
                logger.info('Удаление ресурса начато и займет некоторое время.')
            else:
                logger.info('Что-то пошло не так при удалении файла')
        except RequestException as error:
            logger.error(f'Ошибка при удалении файла : {error}')
