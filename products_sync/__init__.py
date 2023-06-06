import logging

from decouple import config

logger = logging.getLogger(__name__)
logger.setLevel(config('DJANGO_LOG_LEVEL'))
