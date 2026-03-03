INIT_SQL = ./app/database/init.sql

setup:
	python3 -m venv .venv
	source .venv/bin/activate

database:
	sudo -u postgres psql -f ${INIT_SQL}

run:
	fastapi dev app/main.py