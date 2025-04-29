import time

from .utils import elapsed_time, add_border


def action_timer(func):

    def wrapper(*args, **kwargs):
        start_time = time.time()
        print(add_border(func.__name__, width=75))
        print()
        out = func(*args, **kwargs)
        et = elapsed_time(time.time() - start_time)
        print(add_border(f'{func.__name__} complete in {et}', width=75))
        print()
        return out

    return wrapper