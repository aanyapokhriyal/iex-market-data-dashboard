#market_job.py
import uuid,requests
from config import (IEX_API_URL,IEX_API_KEY)
from mysql_connection import get_connection
from fastapi import Depends,Request, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from jose import jwt,JWTError
from datetime import datetime, timedelta, timezone
from config import JWT_SECRET_KEY, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login",auto_error=False)

def create_user_account(email, password):
      conn=get_connection()
      cursor=conn.cursor()
      query=""" select email from user_accounts where email= %s """
      cursor.execute(query,(email,))
      user = cursor.fetchone()
      if user:
        cursor.close()
        conn.close()
        return {"message": "Email Taken"}
      else:
        hashed_password = password_hash.hash(password)
        query=""" insert into user_accounts (email,hashed_password,role)
        values (%s,%s,%s) """
        values=(email,hashed_password,"user")
        print(values)
        cursor.execute(query,values)
        conn.commit()
        cursor.close()
        conn.close()
        return {"message": "Successful "}
      
def verify_user(email, password):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """ SELECT email, hashed_password, id, role FROM user_accounts
        WHERE email = %s """
        cursor.execute(query, (email,))
        user = cursor.fetchone()

        if not user:
            return {"message": "User not found", "message_type": "error"}
        if password_hash.verify(password, user["hashed_password"]):
            return {"message": "Login successful","id": user["id"],"message_type": "success","role": user["role"] }
        return {"message": "Invalid password","message_type": "error"}

    finally:
        cursor.close()
        conn.close()


IST = timezone(timedelta(hours=5, minutes=30))

def create_access_token(data: dict):
    print("data:",data)
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    #print("Expire (UTC):", expire)
    print("Expire (IST):", expire.astimezone(IST))
    to_encode.update({"exp": expire})
    #print(to_encode)
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def get_current_user(request: Request, token: str = Depends(oauth2_scheme)):
    #print("Header token:", token)
    if token is None:
        token = request.cookies.get("access_token")
        #print("Cookie token:", token)
    if token is None:
        #print("No token found anywhere — returning None")
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        #print("payload", payload)
        return {"sub":payload["sub"],"role":payload["role"]}
    except JWTError:
        return None

def required_role(required_role:str):
    print(required_role)
    def role_checker(current_user=Depends(get_current_user)):
        print("\ncuurent:",current_user)
        if current_user is None:
            return None
        print("user role:", current_user["role"], "required:", required_role)
        if current_user["role"] != required_role:
            raise HTTPException(status_code=403, detail="You are not authorised to access this page")
        return current_user
    return role_checker

    
def insert_job_log(
    job_uuid,
    product_code,
    trade_date,
    step_name,
    status,
    message,
    rows_inserted=0
):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
    INSERT INTO job_logs
    (
        job_uuid,
        product_code,
        trade_date,
        step_name,
        status,
        message,
        rows_inserted
    )
    VALUES (%s,%s,%s,%s,%s,%s,%s)
    """

    values = (
        job_uuid,
        product_code,
        trade_date,
        step_name,
        status,
        message,
        rows_inserted
    )

    cursor.execute(query, values)
    conn.commit()
    cursor.close()
    conn.close()


def fetch_data(product_code,from_date,to_date,iex_token=None):

    from_date = datetime.strptime(from_date,"%Y-%m-%d").strftime("%d/%m/%Y")
    to_date = datetime.strptime(to_date,"%Y-%m-%d").strftime("%d/%m/%Y")

    payload = {
        "APITokenNo": iex_token or IEX_API_KEY,
        "Product_Code": product_code,
        "From_Date": from_date,
        "From_Token": 1,
        "To_Date": to_date,
        "To_Token": 96,
        "Date_Type": 2
    }
    response = requests.post(IEX_API_URL,json=payload,timeout=10)
    return response.json()

def transform_data(response_data,product_code,job_uuid):
    if not response_data.get("Delivery_Date_Details"):
        return []
    
    # print(product_code)
    # print(market_type_map)
    # print(market_type_map.keys())

    #market_type = market_type_map[product_code]

    final_data = []

    delivery_dates = response_data["Delivery_Date_Details"]

    for delivery in delivery_dates:

        date = delivery["DeliveryDate"]
        formatted_date = datetime.strptime(date,"%d/%m/%Y").strftime("%Y-%m-%d")
        tokens = delivery["Token_Wise"]

        for token in tokens:
            token_no = token["Token_NO"]
            market_data = token["All_India_DAM_GDAM_RTM"]

            total_minutes = (token_no - 1) * 15
            hours = total_minutes // 60
            minutes = total_minutes % 60
            timestamp = (f"{formatted_date} "f"{hours:02d}:{minutes:02d}")

            final_data.append({
                "trade_date": formatted_date,
                "product_code": product_code,
                "block_no": token_no,
                "timestamp": timestamp,
                "buy_vol": market_data["Buy_Volume"],
                "mcv": market_data["Cleared_Volume"],
                "mcp": market_data["Clearing_Price"],
                "sell_vol": market_data["Sell_Volume"],
                "area_code": "IN",
                "job_uuid":job_uuid
            })

            for area in token["Area_Details"]:

                area_codes = area["Area_Codes"]

                final_data.append({
                    "trade_date": formatted_date,
                    "product_code": product_code,
                    "block_no": token_no,
                    "timestamp": timestamp,
                    "buy_vol": area_codes["Buy_Volume"],
                    "mcv": None,
                    "mcp": area_codes["Area_Price"],
                    "sell_vol": area_codes["Sell_Volume"],
                    "area_code": area["Area_code"],
                    "job_uuid": job_uuid
                })

    return final_data


def delete_existing_data(product_code,trade_date):

    conn = get_connection()
    cursor = conn.cursor()

    query = """
    DELETE FROM exchange_data
    WHERE product_code=%s
    AND trade_date=%s
    """

    cursor.execute(query,(product_code,trade_date))

    conn.commit()
    cursor.close()
    conn.close()


def store_data(records):

    if len(records) == 0:
        return 0

    conn = get_connection()
    cursor = conn.cursor()

    query = """
    INSERT INTO exchange_data
    (
        trade_date,
        product_code,
        block_no,
        timestamp,
        buy_vol,
        mcv,
        mcp,
        sell_vol,
        area_code,
        job_uuid
    )
    VALUES
    (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """

    try:

        conn.start_transaction()

        for row in records:

            values = (
                row["trade_date"],
                row["product_code"],
                row["block_no"],
                row["timestamp"],
                row["buy_vol"],
                row["mcv"],
                row["mcp"],
                row["sell_vol"],
                row["area_code"],
                row["job_uuid"]
            )

            cursor.execute(query,values)

        conn.commit()

        return len(records)

    except Exception:

        conn.rollback()
        raise

    finally:

        cursor.close()
        conn.close()


def run_market_job(product_code,from_date,to_date,iex_token=None):

    job_uuid = str(uuid.uuid4())[-8:]

    #market_type = market_type_map[product_code]

    try:
        response_data = fetch_data(product_code,from_date,to_date,iex_token)
        #print(response_data) 
        if response_data.get("Status") is False:

            insert_job_log(
                job_uuid,
                product_code,
                from_date,
                "FETCH",
                "FAILED",
                response_data.get(
                    "Message",#message returned by api
                    "No data returned by IEX"
                )
            )

            return {
                "job_uuid": job_uuid,
                "market_type": product_code,
                "rows_inserted": 0,
                "status": "FAILED",
                "message": response_data.get("Message")
            }
        #print("ACTUAL RESPONSE:")
        #print(response_data)    

        insert_job_log(
            job_uuid,
            product_code,
            from_date,
            "FETCH",
            "SUCCESS",
            "Data fetched successfully"
        )

    except Exception as error:

        insert_job_log(
            job_uuid,
            product_code,
            from_date,
            "FETCH",
            "FAILED",
            str(error)
        )

        raise

    try:
        records = transform_data(response_data,product_code,job_uuid)

        insert_job_log(
            job_uuid,
            product_code,
            from_date,
            "TRANSFORM",
            "SUCCESS",
            f"{len(records)} records transformed"
        )

    except Exception as error:

        insert_job_log(
            job_uuid,
            product_code,
            from_date,
            "TRANSFORM",
            "FAILED",
            str(error)
        )

        raise

    try:

        trade_dates = {
            row["trade_date"]
            for row in records
}

        for trade_date in trade_dates:

            delete_existing_data(product_code,trade_date)

        rows_inserted = store_data(records)

        insert_job_log(
            job_uuid,
            product_code,
            from_date,
            "STORE",
            "SUCCESS",
            "Data stored successfully",
            rows_inserted
        )

    except Exception as error:

        insert_job_log(
            job_uuid,
            product_code,
            from_date,
            "STORE",
            "FAILED",
            str(error)
        )

        raise

    return {"job_uuid": job_uuid,"market_type": product_code,"rows_inserted": rows_inserted,"status": "SUCCESS"}

def view_data(product_code: int, from_date: str, to_date: str):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    # product_map = {1: "DAM", 2: "GDAM", 3: "RTM"}
    # market_type = product_map.get(product_code)

    query = """ SELECT trade_date,product_code,block_no,timestamp,buy_vol,mcv,mcp,sell_vol,area_code
    FROM exchange_data WHERE product_code = %s
    AND trade_date BETWEEN %s AND %s
    ORDER BY trade_date, block_no """
    try:
        cursor.execute(query, (product_code, from_date, to_date))
        records = cursor.fetchall()
        return records
    except Exception:
        raise
    finally:
        cursor.close()
        conn.close()
        
def view_data_national(product_code: int, from_date: str, to_date: str, y_field: str):
    #print("hello")
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    query= f""" select timestamp, {y_field} from exchange_data where product_code= %s 
    and trade_date between %s and %s and area_code= 'IN'  order by trade_date, block_no  

    """
    values= product_code,from_date, to_date
    
    # query= f""" select timestamp, {y_field} from exchange_data where product_code= {product_code} 
    # and trade_date between {from_date} and {to_date} and area_code= 'IN'  order by trade_date, block_no """
    #print(query)
    #print("query",query(product_code,from_date, to_date))
    
    try:
        cursor.execute(query,values)
        print("\nquery:",query)
        print("query values:",values)
        #cursor.execute(query,( product_code,from_date, to_date))
        #print(cursor.statement)
        records = cursor.fetchall()
        #print("records:",records[:2])
        return records
    except Exception:
        raise
    finally:
        cursor.close()
        conn.close()