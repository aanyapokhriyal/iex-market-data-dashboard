#main.py
from fastapi import FastAPI, Request,Form,Depends,HTTPException,Header
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import market_job,requests
from config import ACCESS_TOKEN_EXPIRE_MINUTES,IEX_API_URL,IEX_API_KEY
from fastapi.responses import RedirectResponse
from pwdlib import PasswordHash


app = FastAPI()
password_hash = PasswordHash.recommended()
app.mount("/static", StaticFiles(directory="static"), name="static")    
templates = Jinja2Templates(directory="templates")

@app.get("/signup")
def show_signup_form(request:Request):
    return templates.TemplateResponse(request=request, name="signup.html")    

@app.post("/signup")
def signup_user(request:Request,email:str =Form(...),password:str= Form(...)):
    result = market_job.create_user_account(email, password)
    if result["message"] == "Email Taken":
        return templates.TemplateResponse(request=request, name="signup.html", context={"message": "Email already registered", "message_type": "error"})
    else:
        return templates.TemplateResponse(request=request, name="login.html", context={"message": "Signup successful! Please log in.", "message_type": "success"})
    
@app.get("/login")
def show_login_form(request:Request):
    return templates.TemplateResponse(request=request, name="login.html") 

@app.post("/login")
def login_user(request:Request,email:str =Form(...),password:str= Form(...)):
    result = market_job.verify_user(email, password)
    if result["message"] == "Login successful":
        access_token = market_job.create_access_token({"sub": str(result["id"]), "role":str(result["role"])})
        response = RedirectResponse("/get-details", status_code=303)
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,#JavaScript cannot read this cookie.Only the browser automatically sends it with future requests.
            max_age= ACCESS_TOKEN_EXPIRE_MINUTES * 60  # seconds, matches your expire time
        )
        return response                
    else:
        return templates.TemplateResponse(request=request, name="login.html", context={"message": result["message"], "message_type": result.get("message_type","")})
    
@app.get("/get-details")
def home(request:Request, current_user: str = Depends(market_job.get_current_user)):
    #print (current_user)
    #print(request)
    if current_user is None:
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(request=request, name="index.html",context={ "request": request,"result": None})

@app.post("/load-data")
def load_data(
    request:Request,product_code: int = Form(...),from_date: str = Form(...),to_date: str = Form(...),
    iex_token: str | None = Header(default=None, alias="X-IEX-Token"),
    current_user: str = Depends(market_job.get_current_user)):
    if current_user is None:
        return RedirectResponse("/login", status_code=303)
    result = market_job.run_market_job(product_code,from_date,to_date)
    return templates.TemplateResponse(request=request,name="index.html",context={ "request": request,"result": result,"product_code":product_code,"from_date":from_date,"to_date":to_date})

@app.get("/view-data")
def view_data_page(request:Request,product_code: int = None, from_date: str = None, to_date: str = None,
                   current_user: str = Depends(market_job.get_current_user)):
    if current_user is None:
        return RedirectResponse("/login", status_code=303)
    if product_code is None or from_date is None or to_date is None:
        return RedirectResponse("/get-details", status_code=303)
    records = market_job.view_data(product_code, from_date, to_date)
    #print(len(records), records[:2])
    for row in records:
        row['trade_date'] = str(row['trade_date'])
        row['timestamp'] = str(row['timestamp'])
        row['buy_vol'] = float(row['buy_vol']) if row['buy_vol'] is not None else None
        row['mcv'] = float(row['mcv']) if row['mcv'] is not None else None
        row['mcp'] = float(row['mcp']) if row['mcp'] is not None else None
        row['sell_vol'] = float(row['sell_vol']) if row['sell_vol'] is not None else None
            
    return templates.TemplateResponse(request=request,name="view.html",context={"request": request,"records": records,
        "product_code":product_code,"from_date":from_date,"to_date":to_date,
        "current_user_role":current_user["role"]
        })

@app.get("/visualize")
def visualize_page(request: Request, product_code: int = None, from_date: str = None, to_date: str = None, 
            y_field: str = None, chart_type: str = None, current_user: str = Depends(market_job.get_current_user), 
            role_checker:str=Depends(market_job.required_role("admin"))):
    if current_user is None:
        return RedirectResponse("/login", status_code=303)
    if product_code is None or from_date is None or to_date is None:
        return RedirectResponse("/get-details", status_code=303)

    labels, values = [], []

    if y_field:
        allowed_fields = {"mcp", "mcv", "buy_vol", "sell_vol"}
        if y_field not in allowed_fields:
            raise HTTPException(status_code=400, detail="Invalid field selection")

        filtered = market_job.view_data_national(product_code, from_date, to_date, y_field)
        print("filtered data:   ",filtered[:2])

        for row in filtered:
            labels.append(str(row["timestamp"]))
            if row[y_field] is not None:
                values.append(float(row[y_field]))
            else:
                values.append(None)
        print("labels:", labels[:2])
        # print("labels:",type(labels[1])) 
        #print("values:",type(values[1])) 
        print("values:", values[:2])

    return templates.TemplateResponse(request=request, name="visualize.html", context={
        "request": request, "product_code": product_code, "from_date": from_date, "to_date": to_date,
        "labels": labels, "values": values, "y_field": y_field, "chart_type": chart_type})

@app.get("/logout")                             
def logout_user():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("access_token")
    return response  
    
#for postman
@app.post("/token")
def login_for_token(request:Request,email:str =Form(...),password:str= Form(...)):
    result = market_job.verify_user(email, password)
    if result["message"] == "Login successful":
        access_token = market_job.create_access_token({"sub": str(result["id"]), "role":str(result["role"])})
        return {"access_token": access_token,"token_type": "bearer"}              
    else:
        raise HTTPException(status_code=401, detail=result["message"])
    
@app.post("/raw-response")
def raw_response(request:Request,
    product_code: int = Form(...),
    from_date: str = Form(...),
    to_date: str = Form(...),
    #iex_token: str | None = Header(default=None, alias="X-IEX-Token")
    ):
    return market_job.fetch_data(product_code, from_date, to_date, #iex_token
)