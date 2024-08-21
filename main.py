import os
import sys
import time

from cl_storage.folder_scan import ScanFolder
from config_data.config import logger
from loader import path_to_local_dir, check_interval


def main():

    if not os.path.exists(path_to_local_dir):
        logger.error(f'Папка {path_to_local_dir} не существует.')
        raise FileNotFoundError(f'Папка {path_to_local_dir} не найдена.')

    logger.info(f'Начало работы программы. Синхронизируемая папка: {path_to_local_dir}')

    try:
        with ScanFolder(path_to_local_dir) as monitor_folder:
            while True:
                try:
                    logger.info('Начался цикл синхронизации')
                    monitor_folder.sync_with_cloud()
                    logger.info('Синхронизация завершена')
                except Exception as exception:
                    logger.error(exception)

                time.sleep(check_interval)
    finally:
        logger.info('Программа завершена.')
        sys.exit(0)


if __name__ == '__main__':
    main()
