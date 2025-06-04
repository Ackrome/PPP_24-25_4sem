import os
from app.core.endpoints import FastApiServerInfo
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import secrets
import aiosqlite # Используем асинхронную библиотеку для SQLite
from app.schemas.schemas import User

DB_PATH = os.path.join('app','db','database.db')

router = APIRouter()

# Схема OAuth2 для получения токена из заголовка Authorization
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=FastApiServerInfo.LOGIN_ENDPOINT)

# Вспомогательная функция для получения асинхронного соединения с БД
async def get_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Убедимся, что таблица Users существует (можно вынести в миграции)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS Users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                token TEXT UNIQUE
            )
        """)
        await db.commit()
        yield db

# Добавление нового пользователя в бд и возврат токена
@router.post(FastApiServerInfo.SIGN_UP_ENDPOINT)
async def sign_up(user: User, db: aiosqlite.Connection = Depends(get_db)):
    # Проверяем, существует ли пользователь с таким email
    cursor = await db.execute("SELECT id FROM Users WHERE email = ?", (user.email,))
    existing_user = await cursor.fetchone()
    await cursor.close()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует"
        )

    # Генерируем токен и вставляем нового пользователя
    token = secrets.token_urlsafe(32) # Генерируем более длинный токен
    cursor = await db.execute(
        "INSERT INTO Users (email, password, token) VALUES (?, ?, ?)",
        (user.email, user.password, token) # В реальном приложении пароль должен быть хеширован!
    )
    await db.commit()
    user_id = cursor.lastrowid # Получаем ID только что вставленной записи
    await cursor.close()

    return {
        "id": user_id,
        "email": user.email,
        "token": token
    }

# Авторизация пользователя и возврат токена
@router.post(FastApiServerInfo.LOGIN_ENDPOINT)
async def login(user: User, db: aiosqlite.Connection = Depends(get_db)):
    # Ищем пользователя по email и паролю
    # В реальном приложении здесь должна быть проверка хешированного пароля
    cursor = await db.execute(
        "SELECT id, email, token FROM Users WHERE email = ? AND password = ?",
        (user.email, user.password)
    )
    user_data = await cursor.fetchone()
    await cursor.close()

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Некорректный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id, email, token = user_data

    return {
        "id": user_id,
        "email": email,
        "token": token
    }

# Вывод информации об авторизованном пользователе по токену
@router.post(FastApiServerInfo.USER_INFO_ENDPOINT)
async def get_user_info(token: str = Depends(oauth2_scheme), db: aiosqlite.Connection = Depends(get_db)):
    # Ищем пользователя по токену
    cursor = await db.execute(
        "SELECT id, email FROM Users WHERE token = ?",
        (token,)
    )
    user_data = await cursor.fetchone()
    await cursor.close()

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id, email = user_data
    return {
        "id": user_id,
        "email": email
    }