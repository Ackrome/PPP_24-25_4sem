import asyncio
import httpx
import websockets
from typing import Dict, Callable
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from app.core.endpoints import FastApiServerInfo
import json, shutil
import  sys, os

class AsyncClient:
    def __init__(self):
        self.base_url = f"http://{FastApiServerInfo.IP}:{FastApiServerInfo.PORT}"
        self.ws_url = f"ws://{FastApiServerInfo.IP}:{FastApiServerInfo.PORT}/ws/notifications"
        self.user_token: str = None
        self.user_email: str = None
        self.running = True
        
        self.session = PromptSession()
        
        self.commands: Dict[str, Callable] = {
            "login": self.login,
            "register": self.register,
            "task": self.create_task,
            "clear": self.clear_console,
            "brut": self.brut_rar_task, 
            "exit": self.exit
        }
        
        self.ws_task: asyncio.Task = None
        self.input_task: asyncio.Task = None
        self.active_tasks = list()

    async def notification_func(self, message: str):
        with patch_stdout():
            print(f"[Нотификация от сервера]: {message}")
            sys.stdout.flush()
    

    async def async_print(self, message: str):
        with patch_stdout():
            prefix = f"[Пользователь: {self.user_email.split('@')[0]}. С токеном: {self.user_token}]" if self.user_token else "[Некто анонимный]"
            print(f"{prefix} --> {message}\n", end="")
            sys.stdout.flush()


    async def listener(self):
        while self.running:
            try:

                async with websockets.connect(self.ws_url) as ws:
                    async for message in ws:
                        data = json.loads(message)

                        task_id_from_notification = data.get('task_id')
                        if task_id_from_notification and task_id_from_notification in self.active_tasks:
                            await self.notification_func(json.dumps(data, ensure_ascii=False, indent=4))
                            if data["status"] == "done":
                                self.active_tasks.remove(data['task_id'])

            except Exception as e:
                await self.async_print(f"WebSocket error: {str(e)}")
                await asyncio.sleep(5)
                
    async def login(self):
        email = await self.session.prompt_async("Email: ")
        password = await self.session.prompt_async("Password: ", is_password=True)
        self.session.is_password = False
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}{FastApiServerInfo.LOGIN_ENDPOINT}",
                    json={"email": email, "password": password}
                )
                if response.status_code == 200:
                    data = response.json()
                    self.user_token = data['token']
                    self.user_email = data['email']
                    await self.async_print("Успешная авторизация!")
                else:
                    await self.async_print(f"Ошибка: {response.text}")
                    
            except Exception as e:
                await self.async_print(f"Ошибка соединения: {str(e)}")

    async def register(self):
        email = await self.session.prompt_async("Email: ")
        password = await self.session.prompt_async("Password: ", is_password=True)
        self.session.is_password = False
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}{FastApiServerInfo.SIGN_UP_ENDPOINT}",
                    json={"email": email, "password": password}
                )
                if response.status_code == 200:
                    data = response.json()
                    self.user_token = data['token']
                    self.user_email = data['email']
                    await self.async_print("Регистрация успешна!")
                else:
                    await self.async_print(f"Ошибка: {response.text}")
                    
            except Exception as e:
                await self.async_print(f"Ошибка соединения: {str(e)}")

    async def create_task(self):
        async with httpx.AsyncClient() as client:
            try:
                if not self.user_token:
                    raise Exception("Необходима авторизация!") 

                response = await client.post(
                    f"{self.base_url}{FastApiServerInfo.LONG}", 
                    json = {}, 
                    headers={"Authorization": f"Bearer {self.user_token}"}
                )
                response.raise_for_status() 
                data = response.json()
                task_id = data.get('task_id')
                if task_id:
                    self.active_tasks.append(task_id)
                    await self.async_print(f"Задача {task_id} запущена.")
                else:
                    await self.async_print(f"Не удалось получить ID задачи: {data}")
                
            except Exception as e:
                await self.async_print(f"Ошибка: {str(e)}")

    async def brut_rar_task(self):
        file_path = await self.session.prompt_async("Путь к RAR файлу: ")
        charset = await self.session.prompt_async("Набор символов (например, abc123): ")
        try:
            max_length_str = await self.session.prompt_async("Максимальная длина пароля (до 8): ")
            max_length = int(max_length_str)
            if not 1 <= max_length <= 8:
                await self.async_print("Максимальная длина должна быть от 1 до 8.")
                return
        except ValueError:
            await self.async_print("Некорректная максимальная длина пароля.")
            return

        async with httpx.AsyncClient() as client:
            try:
                if not self.user_token:
                    raise Exception("Необходима авторизация!") 
                
                # Директория для временного хранения файла на стороне клиента
                CLIENT_TEMP_STORAGE_DIR = "client_temp_storage"
                os.makedirs(CLIENT_TEMP_STORAGE_DIR, exist_ok=True)

                if not os.path.exists(file_path):
                    await self.async_print(f"Файл не найден: {file_path}")
                    return

                with open(file_path, "rb") as f:
                    files = {"file": (os.path.basename(file_path), f, "application/x-rar-compressed")}
                    data = {"charset": charset, "max_length": max_length}
                    # Копируем файл в локальное временное хранилище клиента
                    # copied_file_name = os.path.basename(file_path) # Закомментировано, т.к. файл уже открыт как 'f'
                    # local_copied_path = os.path.join(CLIENT_TEMP_STORAGE_DIR, copied_file_name) # И не используется далее
                    # shutil.copy2(file_path, local_copied_path) # Эта копия не нужна, если файл читается напрямую
                    
                    response = await client.post(
                        f"{self.base_url}{FastApiServerInfo.BRUT_HASH}",
                        files=files,
                        data=data,
                        headers={"Authorization": f"Bearer {self.user_token}"}
                    )
                response.raise_for_status() # Проверка на HTTP ошибки
                resp_data = response.json()
                task_id = resp_data.get('task_id')
                if task_id:
                    self.active_tasks.append(task_id)
                    await self.async_print(f"Задача брутфорса {task_id} запущена.")
                else:
                    await self.async_print(f"Не удалось получить ID задачи: {resp_data}")
            except FileNotFoundError:
                await self.async_print(f"Файл не найден: {file_path}")
            except httpx.HTTPStatusError as e:
                await self.async_print(f"Ошибка HTTP: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                await self.async_print(f"Ошибка: {str(e)}")

    async def clear_console(self):
        os.system("cls" if os.name == "nt" else "clear")
        await self.async_print("Консоль очищена")

    async def exit(self):
        self.running = False
        if self.ws_task:
            self.ws_task.cancel()
        if self.input_task:
            self.input_task.cancel()
        await self.async_print("Завершение работы...")
        # Даем задачам время на завершение
        await asyncio.sleep(0.1)

    async def command_handler(self):
        while self.running:
            try:
                with patch_stdout():
                    command = await self.session.prompt_async(
                        "Введите команду: ",
                    )
                
                if not command: 
                    continue

                if command in self.commands:
                    await self.commands[command]()
                elif command == "help":
                    await self.async_print("Доступные команды: " + ", ".join(list(self.commands.keys()) + ['help']))
                else:
                    await self.async_print("Неизвестная команда. Введите 'help' для списка команд.")
            except (KeyboardInterrupt, EOFError): 
                await self.exit()
                break 
            except asyncio.CancelledError:
                break 
            except Exception as e:
                await self.async_print(f"Ошибка в обработчике команд: {str(e)}")

    async def run(self):
        self.ws_task = asyncio.create_task(self.listener())
        self.input_task = asyncio.create_task(self.command_handler())
        
        try:
            await asyncio.gather(
                self.ws_task,
                self.input_task,
            )
        except asyncio.CancelledError:
            await self.async_print("Клиент завершает работу...")
        finally:
            # Убедимся, что все задачи отменены при выходе
            if self.ws_task and not self.ws_task.done():
                self.ws_task.cancel()
            if self.input_task and not self.input_task.done():
                self.input_task.cancel()
            # Ожидаем завершения задач после отмены
            await asyncio.gather(self.ws_task, self.input_task, return_exceptions=True)

if __name__ == "__main__": 
    client = AsyncClient()
    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        print("\nКлиент принудительно завершен.")
    except Exception as e:
        print(f"Непредвиденная ошибка на верхнем уровне: {e}")