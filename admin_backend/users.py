import aiosqlite
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from typing import Optional

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class ManagerUser(BaseModel):
    id: int
    email: EmailStr
    hashed_password: str
    full_name: str
    is_active: bool = True

import os
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'bookai.db')

async def init_managers_db():
    # Эта функция больше не нужна, так как таблица создается в db.py
    pass

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

async def create_manager(email: str, password: str, full_name: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        hashed = get_password_hash(password)
        cursor = await db.execute(
            'INSERT INTO managers (email, hashed_password, full_name) VALUES (?, ?, ?)',
            (email, hashed, full_name)
        )
        await db.commit()
        return cursor.lastrowid

async def get_manager_by_email(email: str) -> Optional[ManagerUser]:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            async with db.execute('SELECT id, email, hashed_password, full_name, is_super_admin FROM managers WHERE email = ?', (email,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return ManagerUser(id=row[0], email=row[1], hashed_password=row[2], full_name=row[3] or "", is_active=True)
            return None
        except Exception as e:
            print(f"Ошибка получения менеджера: {e}")
            return None 