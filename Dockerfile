FROM prikid/python_psycopg2_pandas_orjson:3.10-alpine

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app/backend

COPY Pipfile Pipfile.lock ./
RUN pip install --upgrade pip && \
    pip install pipenv && \
    pipenv install --system --deploy

COPY . .

#CMD python manage.py runserver 0.0.0.0:8000
CMD "./run.sh"
