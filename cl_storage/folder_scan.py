import hashlib
import os
from typing import Optional, Dict

from config_data.config import logger

from cl_storage.disk_yandex import YandexDisk


class ScanFolder:

    def __init__(self, folder_path: str):
        self.storage = YandexDisk()
        self.folder_path = folder_path
        self.tracked_files: Dict[str, Optional[str]] = {}


    def __enter__(self):
        """
        Метод, вызываемый при входе в контекст менеджер. Возвращает текущий объект.

        :return: Self
        """
        return self


    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Метод, вызываемый при выходе из контекстного менеджера. Автоматически закрывает сессию.

        :param exc_type: Тип исключения, если возникло.
        :param exc_val: Значение исключения, если возникло.
        :param exc_tb: Объект трассировки, если возникло исключение.
        :return: None
        """
        self.storage.close()


    def scan_local_folder(self) -> Optional[Dict[str, str]]:
        """
        Получение хэша всех файлов для отслеживания изменений в директории пользователя.

        :return: Словарь, где ключи — имена файлов, а значения — их хэши (MD5).
        """
        try:
            local_files = {}
            for i_file in os.listdir(self.folder_path):
                full_path = self.storage.get_full_path(i_file)
                if os.path.isfile(full_path):
                    hasher = hashlib.md5()
                    with open(full_path, 'rb') as file:
                        for chunk in iter(lambda: file.read(4096), b""):
                            hasher.update(chunk)
                            local_files[i_file] = hasher.hexdigest()

            return local_files

        except (OSError, Exception) as exc:
            logger.error(exc)
            return


    def sync_with_cloud(self) -> None:
        """
        Проверка на наличие новых файлов в локальной директории и изменение существующих.
        Синхронизация локальных файлов с файлами в облачном хранилище.

        :return: None
        """
        current_files = self.scan_local_folder()
        if not current_files:
            logger.info('Локальная папка пуста.')
            return

        cloud_files = self.storage.get_all_files_cloud()
        for j_cloud_file in cloud_files:
            if j_cloud_file not in current_files:
                logger.info(f'Удаляется файл {j_cloud_file} в связи его отсутствием в локальной папке')
                self.storage.delete(j_cloud_file)
            else:
                self.tracked_files[j_cloud_file] = self.storage.get_hash_file(j_cloud_file)

        for i_name, i_hash in current_files.items():
            if i_name not in cloud_files:
                logger.info(f'Загрузка нового файла "{i_name}" в облако')
                self.storage.load(i_name)
            elif self.tracked_files[i_name] != i_hash:
                logger.info(f'Найден измененный файл "{i_name}". Синхронизация.')
                self.storage.load(i_name, True)
                logger.info(f'Синхронизация завершена. "{i_name}" перезаписан.')
            elif self.tracked_files[i_name] == i_hash:
                logger.info('Обновление не требуется.')
