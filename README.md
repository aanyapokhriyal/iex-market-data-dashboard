# IEX Task 2

A FastAPI web application to fetch, store, view, and visualize exchange market data using an IEX India API endpoint and MySQL.

## Features

- User signup and login with hashed password storage
- JWT access token authentication via cookies and OAuth2 form login
- Data fetch from IEX API and insertion into MySQL
- View exchange data in a table
- Visualize selected market fields with Chart.js

## Project Structure

- `main.py` - FastAPI application routes and page rendering
- `market_job.py` - API fetch, transform, database insert, auth, and JWT helpers
- `mysql_connection.py` - MySQL connection helper
- `config.py` - environment config and constants
- `templates/` - Jinja2 HTML templates
- `static/` - CSS and JavaScript assets
- `iex_task.sql` - database schema and sample SQL statements
- `.env` - local secrets (not included in source control)

## Requirements

- Python 3.14+ (project venv uses Python 3.14.4)
- MySQL server
- A MySQL database named `iex_task_db`

## Installation

1. Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Create the database schema:

```sql
mysql -u root -p < iex_task.sql
```

4. Create a `.env` file in the project root with:

```env
DB_PASSWORD=<your_mysql_password>
JWT_SECRET_KEY=<your_jwt_secret>
```

5. Start the app:

```powershell
uvicorn main:app --reload
```

6. Visit `http://127.0.0.1:8000/signup` to create an account.

## User Flow

1. **Sign up** at `/signup` with an email and password. The password is hashed before the account is stored.
2. **Log in** at `/login`. On successful authentication, the app issues a JWT in an HTTP-only cookie and redirects to the data selection page.
3. **Select market data** on the home page: choose a product code (1 = DAM, 2 = GDAM, 3 = RTM) and a date range, then submit the form.
4. **Review the load result**, including the job status, number of inserted rows, and job UUID.
5. **View the data** for the selected product and date range in a table.
6. **Visualize data** by selecting a field (MCP, MCV, buy volume, or sell volume) and chart type (line, bar, or scatter). This page is restricted to users with the `admin` role.
7. **Log out** to clear the authentication cookie and return to the login page.

## Backend Flow

1. FastAPI validates the submitted form fields and checks the JWT cookie for protected pages and actions.
2. When data is loaded, the app creates a job UUID and sends a request to the configured IEX API. The selected dates are formatted for the API, which is queried for the product's 15-minute tokens.
3. The response is transformed into database rows: national (`IN`) records and any area-level records, with a timestamp calculated from each token number.
4. The app logs fetch and transform outcomes in `job_logs`.
5. Before storing the fetched data, existing rows for the same product and returned trade dates are deleted. New rows are inserted into `exchange_data` in a database transaction, then the store result is logged.
6. The table page queries `exchange_data` by product and date range. The visualization page queries national (`IN`) records for the requested metric and returns the data to the browser, where Chart.js renders the chart.

## Configuration

- `config.py` loads environment variables from `.env`
- `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` are used for MySQL
- `IEX_API_URL`, `IEX_API_KEY` configure the external API request
- `JWT_SECRET_KEY` and `JWT_ALGORITHM` secure JWT tokens
- `ACCESS_TOKEN_EXPIRE_MINUTES` controls cookie expiration

## Notes

- The app uses `pwdlib` for password hashing.
- Chart rendering is done with Chart.js included from CDN in templates.
- The MySQL schema includes `user_accounts`, `job_logs`, and `exchange_data`.
- `visualize` is restricted to users with role `admin`.
