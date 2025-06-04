import os

class FastApiServerInfo:
    SIGN_UP_ENDPOINT = "/sign-up/"
    LOGIN_ENDPOINT = "/login/"
    USER_INFO_ENDPOINT = "/users/me/"
    UNRAR_TOOL = os.path.join(os.path.expandvars(r'%PROGRAMFILES%'),'WinRAR','UnRAR.exe')
    BRUT_HASH = "/brut_hash/"
    
    # Рекомендуется использовать абсолютный путь или убедиться, что rar2john есть в PATH воркера Celery
    RAR2JOHN_PATH = "Johntheripper/run/rar2john.exe" # Пример, настройте по необходимости
    
    GET_STATUS = "/get_status/"
    LONG = "/long/"
    
    PORT = "8001"
    IP = '127.0.0.1'
    
    REDIS_HOST = 'redis'
    REDIS_PORT = 6379
    REDIS_DB = 0
    REDIS_PASSWORD = ''
    
    REDIS_BROKER = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
    REDIS_BACKEND =  f"redis://{REDIS_HOST}:{REDIS_PORT}/1"