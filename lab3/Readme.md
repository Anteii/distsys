# Торрент клиент

## Задание
1. Разработать модуль парсинга торрент файла
В данном файле хранится ряд значений, которые необходимы для успешной 
реализации клиента:
    - Имя файла для загрузки
    - Размер файла
    - URL трекера, к которому необходимо подключиться

    Все эти свойства хранятся в бинарном формате Bencode.

2. Разработать механизм осуществления HTTP соединений с трекером для получения 
информации о состоянии сети. Цель – получение списка пиров для конкретного файла.
3. Убедиться в возможности установления асинхронных HTTP соединений.
4. Реализовать протокол пиров (рукопожатие – handshake, скачивание фрагмента, 
реализация отдачи файла после полного его получения (работа в роли сидера) – по 
желанию - бонус)
5. Реализовать сбор файла из скачанных фрагментов
6. Убедиться, что скачанный файл соответствует ожидаемому и он корректен

## Отчет
Для выполнения данной работы был исопльзован язык программирования Python 3 и библиотек requests и pypubsub (для асинхронности).

Торрент файл и скачанный файл находятся в репозитории.
