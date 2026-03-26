include .env
export

INIT_SQL = ./app/database/init.sql

setup:
	python3 -m venv .venv
	source .venv/bin/activate && pip install -r requirements.txt

database:
	sudo -u postgres psql -v DB_NAME=${DB_NAME} -v DB_USERNAME=${DB_USERNAME} -v DB_PASSWORD=${DB_PASSWORD} -v DB_HOST=${DB_HOST} -f ${INIT_SQL} 

fetcher:
	python3 background-service/main.py 

list-fetcher:
	ps aux | grep "python3 background-service/vt_data_fetcher.service.py"

app-service:
	fastapi dev app/main.py