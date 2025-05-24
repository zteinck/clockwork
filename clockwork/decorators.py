from functools import wraps
from oddments import add_border
import time

from .utils import format_elapsed_seconds


def action_timer(func):

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        action = func.__name__
        header = add_border(action, width=75, fixed_width=True)
        print(header + '\n')
        out = func(*args, **kwargs)
        duration = format_elapsed_seconds(time.time() - start_time)
        trailer = add_border(f'{action} complete in {duration}.')
        print(trailer + '\n')
        return out

    return wrapper