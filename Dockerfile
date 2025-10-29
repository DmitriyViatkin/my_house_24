FROM python:3.12-slim

WORKDIR /app

# Встановлення системних бібліотек, потрібних для WeasyPrint
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpango-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    libgobject-2.0-0 \
    libglib2.0-0 \
    gir1.2-pango-1.0 \
    shared-mime-info \
    libjpeg62-turbo \
    libpng16-16 \
    libxml2 \
    libxslt1.1 \
    libpq-dev \
    fonts-liberation \
    fonts-dejavu-core \
    curl \
    vim \
    gettext \
    && rm -rf /var/lib/apt/lists/*

# Встановлення Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# Не створювати віртуальне середовище
RUN poetry config virtualenvs.create false

# Копіюємо файли залежностей
COPY pyproject.toml poetry.lock ./

# Додаємо плагін для експорту requirements
RUN poetry self add poetry-plugin-export

# Експортуємо залежності в requirements.txt і встановлюємо їх
RUN poetry export -f requirements.txt --without-hashes -o requirements.txt && \
    pip install --no-cache-dir -r requirements.txt && \
    rm requirements.txt

# --- НОВИЙ КРОК ВИПРАВЛЕННЯ СУМІСНОСТІ З DJANGO 5.2 ---
# Виправлення несумісності: замінюємо ugettext_lazy на gettext_lazy
# у застарілій бібліотеці snowpenguin.django.recaptcha3, як це вимагає Django 4.0+.
RUN sed -i 's/ugettext_lazy/gettext_lazy/g' /usr/local/lib/python3.12/site-packages/snowpenguin/django/recaptcha3/fields.py
# --------------------------------------------------------

# Копіюємо решту коду
COPY . .

# Запуск Django
CMD ["poetry", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]
