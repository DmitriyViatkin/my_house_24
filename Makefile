.PHONY: run migrate makemigrations createsuperuser shell collectstatic  house m-migrate
# variables



PYTHON=python3
MANAGE=manage.py

# Command

run:
	$(PYTHON) $(MANAGE) runserver

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

m-migrate: makemigrations migrate

# Для створення віртуального середовища (опціонально)
venv:
	python3 -m venv house
	. house/bin/activate && pip install -r requirements.txt
