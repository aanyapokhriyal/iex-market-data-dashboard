from dotenv import load_dotenv
import os
load_dotenv()

DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = "iex_task_db"

IEX_API_URL = ("https://www.iexindia.com/IEXPublish/AppServices.svc/IEXGetTradeData")
IEX_API_KEY = "NCLIEXHkl7900@8Uyhkj"

JWT_SECRET_KEY=os.getenv("JWT_SECRET_KEY")
#generated from this  python -c "import secrets; print(secrets.token_hex(32))"
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120
