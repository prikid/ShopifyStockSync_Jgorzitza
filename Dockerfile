FROM prikid/python_psycopg2_pandas_orjson:3.11-alpine

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY requirements.txt ./tmp/

RUN apk --update add --no-cache libstdc++ libpq\
    && /py/bin/pip install --upgrade pip \
    && /py/bin/pip install -r /tmp/requirements.txt

COPY . /app
WORKDIR /app
ENV PATH="/py/bin:$PATH"

RUN rm -rf /tmp \
    && adduser \
      --disabled-password \
      --no-create-home \
      app-user
##    && chown -R app-user:app-user /app/backend/static \
##    && chmod -R 755 /app/backend/static \
##    && chmod -R +x /scripts

USER app-user


#CMD python manage.py runserver 0.0.0.0:8000
CMD "./run.sh"
