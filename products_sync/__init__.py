import logging

from haggis.logs import add_logging_level

add_logging_level('NOTIFICATION', logging.INFO + 4, 'notify')
logger = logging.getLogger(__name__)
