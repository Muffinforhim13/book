from datetime import datetime, timedelta
from jose import jwt
from typing import Optional
from admin_backend.users import get_manager_by_email, verify_password, ManagerUser

SECRET_KEY = "supersecretkey"  # Замените на свой ключ
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 дней

async def authenticate_manager(email: str, password: str) -> Optional[ManagerUser]:
    print(f"Попытка аутентификации для: {email}")
    user = await get_manager_by_email(email)
    if not user:
        print(f"Пользователь не найден: {email}")
        return None
    if not verify_password(password, user.hashed_password):
        print(f"Неверный пароль для: {email}")
        return None
    print(f"Успешная аутентификация для: {email}")
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt 