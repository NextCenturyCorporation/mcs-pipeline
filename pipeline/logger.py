import logging
import os

logPath = "./logs/"
formatString = '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'


def configureBaseLogging(logFileName):
    mainLog = logging.getLogger('main')
    mainLog.setLevel(logging.INFO)

    # add a handler that prints to stdout
    stdout_handler = logging.StreamHandler()
    stdout_handler.setLevel(logging.INFO)
    stdout_handler.setFormatter(logging.Formatter(formatString))
    mainLog.addHandler(stdout_handler)

    # another handler that prints to file
    full_path = logPath + logFileName
    try:
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        file_handler = logging.FileHandler(full_path)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter(formatString))
        mainLog.addHandler(file_handler)
    except Exception as e:
        print("Unable to create path" + full_path)

    return mainLog


def configureLogging(logName, logFileName):
    """Configure a logger that is a child of the base logger.  It will be at debug and go to
    own file.  Because it is a child of the base, the base will also get the log.

    Only call this once for shared loggers since it calls addHandler, and you end up adding a new
    FileHandler each time"""
    logger = logging.getLogger('main.' + logName)
    logger.setLevel(logging.DEBUG)
    full_path = logPath + logFileName + '.log'
    try:
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        handler = logging.FileHandler(full_path)
        handler.setFormatter(logging.Formatter(formatString))
        logger.addHandler(handler)
    except Exception as e:
        print("Unable to create path" + full_path)

    return logger
