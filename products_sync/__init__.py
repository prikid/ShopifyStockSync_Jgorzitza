import logging

from haggis.logs import add_logging_level
from decouple import config

add_logging_level('NOTIFICATION', logging.INFO + 4, 'notify')

logger = logging.getLogger(__name__)
logger.setLevel(config('DJANGO_LOG_LEVEL'))
