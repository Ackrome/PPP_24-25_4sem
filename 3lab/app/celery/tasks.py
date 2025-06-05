import asyncio
import base64
import itertools
import json
import logging # Добавлено для логирования
import os
import rarfile
import shutil
import subprocess
import uuid

import redis.asyncio as aioredis

from app.celery.celery_app import celery_app
from app.core.endpoints import FastApiServerInfo

# Настройка логгера
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO) # Простая конфигурация для вывода INFO и выше


TEMP_DIR_CELERY = r"app/temp_files"  # Временная директория для Celery воркера
os.makedirs(TEMP_DIR_CELERY, exist_ok=True)
os.chmod(TEMP_DIR_CELERY, 0o777)  # Дать полный доступ к файлу

rarfile.UNRAR_TOOL = FastApiServerInfo.UNRAR_TOOL


def extract_rar_hash_celery(archive_path):
    """
    Извлекает хеш RAR-архива с помощью утилиты rar2john.
    """
    try:
        process = subprocess.run(
            [FastApiServerInfo.RAR2JOHN_PATH, archive_path],
            capture_output=True,
            text=True,
            check=False  # Проверяем код возврата вручную для логирования stderr
        )

        if process.returncode != 0:
            logger.error(
                f"rar2john завершился с ошибкой для {archive_path}, код: {process.returncode}. "
                f"Stderr: {process.stderr.strip()}. Stdout: {process.stdout.strip()}"
            )
            return None

        lines = process.stdout.strip().splitlines()
        if not lines:
            logger.error(f"rar2john не вернул вывод для {archive_path}. Stderr: {process.stderr.strip()}")
            return None

        hash_value = None
        # Ищем строку, похожую на хеш
        for line in lines:
            # $RAR3$ и $RAR5$ - распространенные идентификаторы хешей RAR
            if "$RAR3$" in line or "$RAR5$" in line:
                hash_value = line.strip()
                break
        
        if not hash_value and lines: # Если специфический паттерн не найден, берем первую строку
            hash_value = lines[0].strip()
            logger.warning(f"Не найден типичный паттерн хеша RAR в выводе rar2john для {archive_path}. Используется первая строка: '{hash_value}'. Полный вывод: {process.stdout.strip()}")

        if not hash_value:
            logger.error(f"Вывод rar2john для {archive_path} не содержит распознаваемого хеша. Вывод: {process.stdout.strip()}. Stderr: {process.stderr.strip()}")
            return None

        return hash_value
    except FileNotFoundError:
        logger.error(f"Ошибка: rar2john не найден по пути {FastApiServerInfo.RAR2JOHN_PATH}")
        return None
    except Exception as e:
        logger.error(f"Ошибка извлечения хеша из архива {archive_path}: {e}", exc_info=True)
        return None


def generate_passwords_celery(charset, max_length, output_file):
    """
    Генерирует все возможные комбинации символов и записывает их в файл.
    Возвращает общее количество сгенерированных паролей.
    """
    count = 0
    with open(output_file, "w", encoding="utf-8") as f:
        for length in range(1, max_length + 1):
            for pwd_tuple in itertools.product(charset, repeat=length):
                password = ''.join(pwd_tuple)
                f.write(password + "\n")
                count += 1
    logger.info(f"Сгенерировано {count} паролей, записано в файл {output_file}")
    return count


async def brute_force_rar_celery(task_id, archive_path, passwords_file, total_passwords, redis_client, temp_task_dir_for_extraction):
    """
    Перебирает пароли из файла, пытаясь открыть архив. Отправляет прогресс через Redis.
    """
    extraction_target_dir = os.path.join(temp_task_dir_for_extraction, "extract_test_area")
    os.makedirs(extraction_target_dir, exist_ok=True)

    try:
        rf = rarfile.RarFile(archive_path)
    except Exception as e:
        await redis_client.publish("notifications", json.dumps({
            "task_id": task_id, "status": "error", "detail": f"Ошибка открытия архива: {e}"
        }))
        return None

    processed_count = 0
    with open(passwords_file, "r", encoding="utf-8") as f:
        for line in f:
            password = line.strip()
            processed_count += 1
            try:
                rf.extractall(path=extraction_target_dir, pwd=password.encode())
                await redis_client.publish("notifications", json.dumps({
                    "task_id": task_id, "status": "progress", "progress": 100, "detail": f"Найден пароль: {password}"
                }))
                return password
            except (rarfile.BadRarFile, rarfile.RarCRCError):
                progress = (processed_count / total_passwords) * 100 if total_passwords > 0 else 0
                await redis_client.publish("notifications", json.dumps({
                    "task_id": task_id, "status": "progress", "progress": int(progress), "detail": f"Проверка: {password[:1]}***{password[-1:] if len(password)>1 else ''} ({processed_count}/{total_passwords})"
                }))
            except Exception as e:
                # Можно логировать или отправлять специфические ошибки, если это необходимо
                logger.warning(f"Ошибка при проверке пароля '{password}': {e}")
                # Продолжаем перебор
    return None


# В name явно объявляю путь и имя "тяжелого" процесса
@celery_app.task(bind=True, name="app.celery.tasks.long_running_parse")
def long_running_parse(self):
    r = aioredis.Redis(host=FastApiServerInfo.REDIS_HOST, port=FastApiServerInfo.REDIS_PORT, db=0)
    result = {"task_id": self.request.id, "status": "in progress"}
    r.publish("notifications", json.dumps(result))
    asyncio.sleep(5)
    result = {"task_id": self.request.id, "status": "done"}
    r.publish("notifications", json.dumps(result))
    return result

@celery_app.task(bind=True, name="app.celery.tasks.brute_force_rar_task")
def brute_force_rar_task(self, file_content_b64: str, original_filename: str, charset: str, max_length: int):
    task_id = self.request.id
    redis_client = None
    loop = asyncio.new_event_loop() # Создаем новый цикл событий для этой задачи
    asyncio.set_event_loop(loop)

    # Создаем уникальную временную директорию для этой задачи
    temp_task_dir = os.path.join(TEMP_DIR_CELERY, str(uuid.uuid4()))
    os.makedirs(temp_task_dir, exist_ok=True)

    temp_archive_path = os.path.join(temp_task_dir, original_filename)
    # Имя файла для хеша будет без расширения исходного файла + .txt
    base_name_for_outputs = os.path.splitext(original_filename)[0]
    temp_hash_file_path = os.path.join(temp_task_dir, base_name_for_outputs + '.txt')
    temp_passwords_file_path = os.path.join(temp_task_dir, base_name_for_outputs + '_passwords.txt')

    try:
        redis_client = aioredis.Redis(host=FastApiServerInfo.REDIS_HOST, port=FastApiServerInfo.REDIS_PORT, db=0)

        loop.run_until_complete(redis_client.publish("notifications", json.dumps({
            "task_id": task_id, "status": "starting", "progress": 0, "detail": "Задача запущена"
        })))

        try:
            file_content = base64.b64decode(file_content_b64)
            with open(temp_archive_path, "wb") as f:
                f.write(file_content)
        except Exception as e:
            loop.run_until_complete(redis_client.publish("notifications", json.dumps({
                "task_id": task_id, "status": "error", "detail": f"Ошибка сохранения файла: {e}"
            })))
            logger.error(f"Task {task_id}: Ошибка сохранения файла {original_filename}: {e}", exc_info=True)
            result_on_error = {"task_id": task_id, "status": "error", "detail": "File save error"}
            logger.info(f"Task {task_id} returning on file save error: {result_on_error}")
            return result_on_error

        loop.run_until_complete(redis_client.publish("notifications", json.dumps({
            "task_id": task_id, "status": "extracting_hash", "progress": 5, "detail": "Извлечение хеша..."
        })))
        
        hash_value = loop.run_until_complete(asyncio.to_thread(extract_rar_hash_celery, temp_archive_path))
        if not hash_value:
            loop.run_until_complete(redis_client.publish("notifications", json.dumps({
                "task_id": task_id, "status": "error", "detail": "Не удалось извлечь хеш."
            })))
            logger.warning(f"Task {task_id}: Не удалось извлечь хеш для {original_filename}.")
            result_on_error = {"task_id": task_id, "status": "error", "detail": "Hash extraction failed"}
            logger.info(f"Task {task_id} returning on hash extraction error: {result_on_error}")
            return result_on_error
        
        loop.run_until_complete(redis_client.publish("notifications", json.dumps({
            "task_id": task_id, "status": "generating_passwords", "progress": 10, "hash": hash_value, "detail": "Генерация паролей..."
        })))
        total_passwords = loop.run_until_complete(asyncio.to_thread(generate_passwords_celery, charset, max_length, temp_passwords_file_path))
        if total_passwords == 0:
            loop.run_until_complete(redis_client.publish("notifications", json.dumps({
                "task_id": task_id, "status": "error", "detail": "Не сгенерировано паролей (возможно, пустой charset или max_length=0)."
            })))
            logger.warning(f"Task {task_id}: Не сгенерировано паролей для {original_filename} с charset='{charset}', max_length={max_length}.")
            result_on_error = {"task_id": task_id, "status": "error", "detail": "No passwords generated"}
            logger.info(f"Task {task_id} returning on no passwords generated: {result_on_error}")
            return result_on_error

        loop.run_until_complete(redis_client.publish("notifications", json.dumps({
            "task_id": task_id, "status": "bruteforcing", "progress": 15, "detail": f"Начинаем подбор из {total_passwords} паролей..."
        })))
        
        found_password = loop.run_until_complete(brute_force_rar_celery(
            task_id, temp_archive_path, temp_passwords_file_path, total_passwords, redis_client, temp_task_dir
        ))

        if found_password:
            final_status = {"task_id": task_id, "status": "completed", "progress": 100, "result": found_password, "hash": hash_value, "detail": "Пароль найден!"}
            loop.run_until_complete(redis_client.publish("notifications", json.dumps(final_status)))
            logger.info(f"Task {task_id} returning: {final_status}")
            return final_status
        else:
            final_status = {"task_id": task_id, "status": "failed", "progress": 100, "result": None, "hash": hash_value, "detail": "Пароль не найден."}
            loop.run_until_complete(redis_client.publish("notifications", json.dumps(final_status)))
            logger.info(f"Task {task_id} returning: {final_status}")
            return final_status

    except Exception as e:
        error_detail = f"Произошла непредвиденная ошибка в задаче: {type(e).__name__} - {e}"
        logger.error(f"Task {task_id}: {error_detail}", exc_info=True)
        if redis_client:
            loop.run_until_complete(redis_client.publish("notifications", json.dumps({
                "task_id": task_id, "status": "error", "detail": error_detail
            })))
        result_on_error = {"task_id": task_id, "status": "error", "detail": error_detail}
        logger.info(f"Task {task_id} returning on general error: {result_on_error}")
        return result_on_error
    finally:
        if redis_client:
            loop.run_until_complete(redis_client.close())
        if os.path.exists(temp_task_dir):
            try:
                shutil.rmtree(temp_task_dir) # Рекурсивно удаляем временную директорию задачи
            except OSError as e:
                logger.error(f"Ошибка удаления временной директории {temp_task_dir}: {e}")
        loop.close()