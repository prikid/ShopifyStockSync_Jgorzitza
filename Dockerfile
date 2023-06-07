FROM prikid/python_psycopg2_pandas_orjson:3.11-alpine-wv

ENV WORKDIR=/app
ENV USER=app-user
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR $WORKDIR

COPY requirements.txt $WORKDIR

# make static files dirs in order to avoid error from collectstatic
RUN apk --update add --no-cache bash libstdc++ libpq \
    && pip install --upgrade pip \
    && mkdir $WORKDIR/static \
    && mkdir $WORKDIR/static/admin \
    && mkdir $WORKDIR/static/rest_framework \
    && mkdir $WORKDIR/media


RUN pip install -r requirements.txt \
    && adduser --disabled-password --no-create-home $USER \
    && chown -R $USER:$USER $WORKDIR

COPY . $WORKDIR
USER $USER

EXPOSE 8000