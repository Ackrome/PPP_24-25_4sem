# Обновляем все библиотеки
import subprocess
import sys
import os
import time
from app.api.manager import ConnectionManager
import redis
from app.core.endpoints import FastApiServerInfo
import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect,Depends, status
import uvicorn
from app.api import auth
from app.api import brut
import redis.asyncio as aioredis





def update_library(library_name):
    try:
        # Выполняем команду pip install --upgrade для обновления библиотеки
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", library_name])
        
        print(f"\033[32mБиблиотека '{library_name}' успешно обновлена!\033[0m")
    except subprocess.CalledProcessError as e:
        print(f"\033[31mОшибка при обновлении библиотеки '{library_name}': {e}\033[0m")
    except Exception as e:
        print(f"\033[33mПроизошла непредвиденная ошибка: {e}\033[0m")

if 0:#input('Update required libraries [y/n]?').lower() == 'y':
    
    with open('requirements.txt') as f:
        requirements = f.read().splitlines()
        
        libraries = {}
        for i in requirements:
            print(i.split('=='))
            libraries[i.split('==')[0]] = i.split('==')[1]
        for i in libraries:
            update_library(i) 


app = FastAPI(title="Практикум по программированию")

@app.get("/")
async def root():
    return {"message": "Hello World"}

manager = ConnectionManager()


@app.on_event("startup")
async def on_startup():
    global redis_
    redis_ = aioredis.Redis(host = 'redis', port = '6379', db = 0, decode_responses=True)
    asyncio.create_task(notify_loop())

async def notify_loop():
    global redis_
    sub = redis_.pubsub()
    await sub.subscribe('notifications')
    while True:
        msg = await sub.get_message(ignore_subscribe_messages=True, timeout=None)
        if msg and msg["data"]:
            data = json.loads(msg["data"])
            await manager.broadcast(data)
        await asyncio.sleep(0.01)
        
@app.websocket(f"/ws/notifications")
async def ws_notifications(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)



app.include_router(auth.router, tags=["Authentication"])
app.include_router(brut.router, tags=["BrutForce"])



if __name__ == "__main__":
    subprocess.run(['alembic', 'upgrade','head'])
    #subprocess.run(['alembic', 'upgrade','head'])
    print(f'http://{FastApiServerInfo.IP}:{FastApiServerInfo.PORT}/docs#')
    #uvicorn.run(app, host=FastApiServerInfo.IP, port=FastApiServerInfo.PORT)
    
# docker run -d --name redis-container -p 6379:6379 redis
# celery -A "app.celery.celery_app" worker --loglevel=info --pool=solo