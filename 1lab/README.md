# Сервер и клиент для управления запуском программ

## Описание проекта

Данный проект представляет собой систему, состоящую из серверной и клиентской частей, предназначенную для управления запуском программ. Сервер принимает команды от клиента, выполняет указанные программы с заданными интервалами, сохраняет их вывод в файлы и предоставляет возможность получения объединённого вывода всех запусков указанной программы.

### Функциональность сервера:

1. **Приём аргументов при запуске**: Сервер может принимать названия программ в качестве аргументов командной строки.
2. **Создание директорий**: Для каждой переданной программы создаётся отдельная папка с соответствующим именем.
3. **Циклический запуск программ**: Каждая программа запускается циклически с интервалом в 10 секунд (интервал можно изменить).
4. **Запись вывода программ**: Стандартный вывод каждой запущенной программы записывается в новый файл внутри соответствующей папки.
5. **Загрузка/сохранение данных**: При запуске сервер загружает информацию о ранее запущенных программах из JSON-файла, а перед завершением работы сохраняет актуальные данные.
6. **Обработка запросов клиента**:
   - Добавление новых программ в список запускаемых.
   - Получение объединённого вывода всех запусков указанной программы.
   - Возможность остановки и возобновления выполнения программ.
   - Изменение интервала запуска программ.
7. **Graceful shutdown**: Корректное завершение работы при получении сигнала `SIGINT` или `SIGTERM`.

### Функциональность клиента:

1. **Подключение к серверу**: Клиент устанавливает сетевое соединение с сервером.
2. **Пользовательский интерфейс**: Предоставляет текстовый интерфейс для отправки команд серверу.
3. **Отправка команд**:
   - Добавление новых программ.
   - Получение объединённого вывода для указанной программы.
   - Остановка и возобновление выполнения программ.
   - Изменение интервала запуска программ.
4. **Отображение результатов**: Полученные от сервера данные выводятся пользователю в удобном формате.

---

## Установка и настройка

### Требования

1. Python версии 3.8 или выше.

---

## Запуск проекта

python main.py

---

## Команды клиента

Клиент предоставляет следующие команды для взаимодействия с сервером:

1. **ADD `<program>`** Добавляет новую программу в список запускаемых.Пример:

   ```bash
   ADD script3.py
   ```
2. **GET `<program>`** Запрашивает объединённый вывод всех запусков указанной программы.Пример:

   ```bash
   GET script1.py
   ```
3. **STOP `<program>`** Останавливает выполнение указанной программы.Пример:

   ```bash
   STOP script1.py
   ```
4. **RESUME `<program>`**Возобновляет выполнение остановленной программы.Пример:

   ```bash
   RESUME script1.py
   ```
5. **CHANGE `<program> <interval>`**

   Изменяет интервал запуска указанной программы (в секундах).Пример:

   ```bash
   CHANGE script1.py 20
   ```
6. **SHOW** Отображает таблицу всех зарегистрированных программ с информацией о количестве запусков и директориях вывода.
7. **EXIT**
   Завершает работу клиента.

---

## Структура проекта

```
1lab/
├── main.py          # Главный скрипт для запуска сервера и клиента
├── server.py        # Логика работы сервера
├── client.py        # Логика работы клиента
├── programs_info.json # Файл для хранения данных о программах
└── README.md        # Документация проекта
```

---

## Особенности реализации

1. **Многопоточность**: Сервер использует потоки для параллельного выполнения программ и обработки клиентских запросов.
2. **Graceful shutdown**: При получении сигнала завершения (`SIGINT` или `SIGTERM`) сервер корректно завершает все потоки и сохраняет данные.
3. **Управление интервалами**: Интервал запуска программ можно изменять через клиентский интерфейс.
4. **Логирование**: Все действия сервера и клиента логируются для удобства отладки и анализа.
