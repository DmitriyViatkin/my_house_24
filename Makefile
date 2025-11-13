.PHONY: run migrate makemigrations createsuperuser shell collectstatic house m-migrate add-rolle docker-build docker-run docker-stop docker-logs docker-clean

# variables
PYTHON=python3
MANAGE=manage.py
IMAGE_NAME=my_house_24
CONTAINER_NAME=my_house_24_container
PORT=8000

# Django commands
run:
	$(PYTHON) $(MANAGE) runserver 127.0.0.1:$(PORT)

migrate:
	$(PYTHON) $(MANAGE) migrate
	@echo "---"
	@echo " Миграции успешно применены!"

makemigrations:
	$(PYTHON) $(MANAGE) makemigrations
	@echo "---"
	@echo " Макмиграции успешно созданы!"

createsuperuser:
	$(PYTHON) $(MANAGE) createsuperuser
	@echo "---"
	@echo " Суперпользователь успешно создан!"

shell:
	$(PYTHON) $(MANAGE) shell

collectstatic:
	$(PYTHON) $(MANAGE) collectstatic --noinput
	@echo "---"
	@echo " Статические файлы успешно собраны!"

add_rolle:
	$(PYTHON) $(MANAGE) add_rolle
	@echo "---"
	@echo " Роли успешно добавлены!"

m-migrate: makemigrations migrate

# venv
venv:
	python3 -m venv house
	. house/bin/activate && pip install -r requirements.txt

# Docker commands
docker-build:
	docker build -t $(IMAGE_NAME) .

docker-run:
	docker run  --name $(CONTAINER_NAME) -p $(PORT):$(PORT) $(IMAGE_NAME)

docker-stop:
	docker stop $(CONTAINER_NAME)
	docker rm $(CONTAINER_NAME)

docker-logs:
	docker logs -f $(CONTAINER_NAME)

docker-clean:
	docker stop $(CONTAINER_NAME) || true
	docker rm $(CONTAINER_NAME) || true
	docker rmi $(IMAGE_NAME) || true



start:
	python manage.py makemigrations
	python manage.py migrate
	python manage.py add-rolle
	python manage.py runserver 0.0.0.0:8000

start-gunicorn:
	@echo "🚀 Запуск Django через Gunicorn..."
	$(PYTHON) $(MANAGE) migrate --noinput
	$(PYTHON) $(MANAGE) collectstatic --noinput
	$(PYTHON) $(MANAGE) add_rolle || true
	gunicorn settings.wsgi:application --bind 0.0.0.0:8000 --workers 4
start-prod:
	@echo "🚀 Запуск в продакшн-режиме..."
	$(PYTHON) $(MANAGE) migrate --noinput
	$(PYTHON) $(MANAGE) collectstatic --noinput
	$(PYTHON) $(MANAGE) add_rolle || true
	gunicorn settings.wsgi:application --bind 0.0.0.0 --workers 4
