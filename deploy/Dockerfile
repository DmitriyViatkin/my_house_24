# используем context: .., значит корень проекта виден
FROM python:3.12-slim

WORKDIR /app

# Системные библиотеки
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libcairo2 libpango-1.0-0 libgdk-pixbuf-2.0-0 \
    libffi-dev libgobject-2.0-0 libglib2.0-0 gir1.2-pango-1.0 \
    shared-mime-info libjpeg62-turbo libpng16-16 libxml2 libxslt1.1 \
    libpq-dev fonts-liberation fonts-dejavu-core curl vim gettext \
    && rm -rf /var/lib/apt/lists/*

# Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry
RUN poetry config virtualenvs.create false
RUN poetry self add poetry-plugin-export

# Копируем зависимости **относительно корня проекта**
COPY pyproject.toml poetry.lock ./

RUN poetry export -f requirements.txt --without-hashes -o requirements.txt && \
    pip install --no-cache-dir -r requirements.txt && \
    rm requirements.txt

RUN sed -i 's/ugettext_lazy/gettext_lazy/g' /usr/local/lib/python3.12/site-packages/snowpenguin/django/recaptcha3/fields.py

# Копируем весь проект **относительно корня**
COPY . .


