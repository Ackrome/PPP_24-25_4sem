from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

# Создаём базовый класс для моделей
Base = declarative_base()

# Определяем модель User
class User(Base):
    __tablename__ = 'Users'  # Имя таблицы в базе данных
    # Колонки таблицы
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    # token = Column(String)
