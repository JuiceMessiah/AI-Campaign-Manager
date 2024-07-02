import logging
import sys


# Note: This method should probably be moved into a singular file along with the contents of 'monitor.py'
# Doesn't make sense to have an entire file for just this method.
def get_logger(name):
    """ Logger method to be called across all files, to log specific events.
    :param name: The name of the current file. Usually '__name__' suffices.
    :returns: A Logger object."""

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    stream_handler = logging.StreamHandler(sys.stdout)
    log_formatter = logging.Formatter("[%(levelname)s] %(name)s: %(message)s")
    stream_handler.setFormatter(log_formatter)
    logger.addHandler(stream_handler)
    return logger
