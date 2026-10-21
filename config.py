from dotenv import load_dotenv
import os
load_dotenv()

DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = "iex_task_db"

IEX_API_URL = os.getenv("IEX_API_URL")
IEX_API_KEY = os.getenv("IEX_API_KEY")

JWT_SECRET_KEY=os.getenv("JWT_SECRET_KEY")
#generated from this  python -c "import secrets; print(secrets.token_hex(32))"
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120
