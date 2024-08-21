#!/bin/bash

# Создание виртуального окружения
python3 -m venv .venv
# Активация виртуального окружения
source .venv/bin/activate
# Установка зависимостей из файла requirements.txt
pip install -r requirements.txt
# Копирование шаблона .env файла
cp .env.template .env

echo "Установка завершена. Пожалуйста запишите  в файл .env ваши персональные параметры."
