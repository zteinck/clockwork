from functools import wraps
from time import perf_counter

from oddments import validate_value

from .utils import format_duration


def print_duration(indents=1, in_place=True):
    '''
    Description
    ------------
    Prints how long the decorated method ran for, with optional indentation
    and bullet styling. The method name must begin with a verb and leading
    underscores are ignored.

    Parameters
    ------------
    indents : int
        Indentation level (0 - n). If 0, the line(s) printed are not indented
        and no bullet point is used.
    in_place : bool
        If True, the initial line is overwritten in-place with a completed
        version that includes the duration.

    Returns
    ------------
    out : any
        The decorated method's return value.
    '''

    def decorator(func):

        @wraps(func)
        def wrapper(self, *args, **kwargs):

            def to_present(verb):
                suffix = 'ing'

                if verb in {'run','get','set'}:
                    return verb + verb[-1] + suffix

                if verb.endswith('e'):
                    return verb[:-1] + suffix

                return verb + suffix


            def to_past(verb):

                irregular = {
                    'run': 'ran',
                    'write': 'wrote',
                    'take': 'took',
                    'make': 'made',
                    'get': 'got',
                    'build': 'built',
                    'send': 'sent',
                    'find': 'found',
                    }

                for key in ['read', 'set']:
                    irregular[key] = key

                if verb in irregular:
                    return irregular[verb]

                if verb.endswith('e'):
                    return verb + 'd'

                return verb + 'ed'


            def print_status(duration=None):
                is_done = duration is not None
                verb = (to_past if is_done else to_present)(words[0])
                parts = [verb.title(), *words[1:]]

                if indents > 0:
                    symbols = ['•', '▸', '▪', '-']
                    symbol = symbols[(indents - 1) % len(symbols)]
                    parts = [''] * 4 * indents + [symbol] + parts

                if is_done:
                    parts.extend(['in', format_duration(duration)])

                line = ' '.join(parts)
                line += ('.' * (1 if is_done else 3))

                if is_done and in_place:
                    line += '\033[K'

                end = '\r' if not is_done and in_place else '\n'
                print(line, end=end)


            # validate decorator arguments
            validate_value(
                value=indents,
                name='indents',
                types=int,
                min_value=0,
                min_inclusive=True
                )

            validate_value(
                value=in_place,
                name='in_place',
                types=bool,
                )

            if self.verbose:
                words = [
                    word.lower()
                    for word in func.__name__.split('_')
                    if word
                    ]

                print_status()
                start_time = perf_counter()

            out = func(self, *args, **kwargs)

            if self.verbose:
                duration = perf_counter() - start_time
                print_status(duration)

            return out

        return wrapper

    return decorator