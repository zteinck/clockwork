import logging
import datetime
from pathpilot import Folder


#╭-------------------------------------------------------------------------╮
#| Classes                                                                 |
#╰-------------------------------------------------------------------------╯

class CustomLogFormatter(logging.Formatter):
    ''' the default implementation of logging.Formatter does not allow
        timestamps to be formatted how I want '''

    converter = datetime.datetime.fromtimestamp

    def formatTime(self, record, datefmt=None):
        if datefmt is not None:
            raise TypeError('datefmt argument must be None')
        return self.converter(record.created)\
                   .strftime('%Y-%m-%d %I:%M:%S.{} %p')\
                   .format('%03d' % record.msecs)



class Logger(object):

    #╭-------------------------------------------------------------------------╮
    #| Class Attributes                                                        |
    #╰-------------------------------------------------------------------------╯

    instances = {}


    #╭-------------------------------------------------------------------------╮
    #| Class Methods                                                           |
    #╰-------------------------------------------------------------------------╯

    @classmethod
    def load(cls, name, *args, **kwargs):
        if name not in cls.instances:
            cls.instances[name] = cls(name, *args, **kwargs)
        return cls.instances[name]


    #╭-------------------------------------------------------------------------╮
    #| Initialize Instance                                                     |
    #╰-------------------------------------------------------------------------╯

    def __init__(self, name, clear=False, stream_handler=False):
        self.name = name

        # create logger
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)

        # create custom formatter
        # https://docs.python.org/3/library/logging.html#logrecord-attributes
        formatter = CustomLogFormatter(fmt='%(asctime)s %(levelname)s %(message)s')
        #formatter = CustomLogFormatter(fmt='%(asctime)s %(name)s %(levelname)s %(message)s')

        # create file handler which logs even debug messages
        self.file = Folder().parent\
            .join('Data', 'Logger', read_only=False)\
            .join(f'{name}.log').path
        if clear: self.clear()
        fh = logging.FileHandler(self.file)
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        logger.addHandler(fh) # add handler to the logger

        # create console handler with a higher log level
        if stream_handler:
            ch = logging.StreamHandler()
            ch.setLevel(logging.ERROR)
            ch.setFormatter(formatter)
            logger.addHandler(ch) # add handler to the logger

        # disable logging to console
        logger.propagate = False

        self.logger = logger


    #╭-------------------------------------------------------------------------╮
    #| Magic Methods                                                           |
    #╰-------------------------------------------------------------------------╯

    def __getitem__(self, name):
        return self.__dict__[name].logger

    def __repr__(self):
        return self.file

    def __str__(self):
        return self.file

    def clear(self):
        open(self.file, 'w').close()


#╭-------------------------------------------------------------------------╮
#| Functions                                                               |
#╰-------------------------------------------------------------------------╯

def log(logger=None):
    ''' Logs decorated function using the passed logging.Logger object.
    If None, a logger object is created (or loaded if already exists)
    using the decorated function's name. '''

    def decorator(func):

        def wrapper(*args, **kwargs):
            nonlocal logger
            logger = logger or Logger.load(func.__name__).logger
            logger.info('start')

            try:
                out = func(*args, **kwargs)
                logger.info('complete')
                return out
            except Exception as e:
                logger.exception('exception')
                return e

        return wrapper

    return decorator