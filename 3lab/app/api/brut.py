import base64
import os

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.celery.tasks import brute_force_rar_task, long_running_parse
from app.core.endpoints import FastApiServerInfo

router = APIRouter()

# Вспомогательные функции (extract_rar_hash, generate_passwords, brute_force_rar)
# теперь являются частью Celery задачи или вызываются ей.
# Локальное управление задачами (tasks = {}) и TEMP_DIR больше не нужны здесь.


@router.post(FastApiServerInfo.BRUT_HASH)
async def brut_file(
    file: UploadFile = File(...),
    charset: str = Form(...),
    max_length: int = Form(...)
):
    if max_length > 8:
        raise HTTPException(status_code=400, detail="max_length не может превышать 8")
    
    try:
        content = await file.read()
        await file.close()

        # Кодируем содержимое файла в base64 для безопасной передачи через Celery (JSON-сериализуемый формат)
        content_b64 = base64.b64encode(content).decode('utf-8')

        # Отправляем задачу в Celery
        task = brute_force_rar_task.delay(
            file_content_b64=content_b64,
            original_filename=file.filename,
            charset=charset,
            max_length=max_length
        )
        
        return {
            "message": "Задача по подбору пароля запущена.",
            "task_id": task.id
        }
    except Exception as e:
        print(f"Ошибка в эндпоинте brut_file: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка запуска задачи: {str(e)}")