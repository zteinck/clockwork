import re


def format_elapsed_seconds(seconds, n_digits=2):
    '''
    Description
    ------------
    Converts a duration in seconds to a human-readable string.

    Parameters
    ------------
    seconds : float | int
        Total number of seconds to format.
    n_digits : int
        Number of decimal places to round the seconds to.

    Returns
    ------------
    text : str
        Formatted elapsed time string.
        (e.g. '5 minutes, 5.51 seconds')
    '''
    units = {'second': 1}

    build_order = {
        'minute': 60,
        'hour': 60,
        'day': 24,
        'year': 365,
        }

    for k, v in build_order.items():
        units[k] = v * next(reversed(units.values()))

    parts = []
    for k in reversed(units):
        v = units[k]
        if k == 'second':
            count = round(seconds, n_digits)
        else:
            count = int(seconds // v)

        if count > 0:
            label = k if count == 1 else k + 's'
            parts.append(f'{count} {label}')
            seconds -= (count * v)

    return ', '.join(parts)


def date_format_to_regex(date_format, encase=False):
    '''
    Description
    ------------
    Converts string of datetime format codes to its regex counterpart.

    Examples:
    ------------
        • '%m/%d/%y' ➜ \d{2}/\d{2}/\d{2}

        • '%Y-%m-%d %I:%M:%S.%f %p' ➜
          '\d{4}\-\d{2}\-\d{2}\ \d{2}:\d{2}:\d{2}\.\d{6}\ (?:AM|PM)'

    Parameters
    ------------
    date_format : str
        String of datetime format codes (e.g. '%Y-%m-%d').
    encase : bool
        If True, the output will be encased in parenthesis.

    Returns
    ------------
    pattern : str
        regex pattern
    '''
    mapping = {}

    digit_pattern = lambda x: r'\d{%d}' % x

    for k, v in [('w', 1), ('j', 3), ('Y', 4), ('f', 6)]:
        mapping['%' + k] = digit_pattern(v)

    for k in ['d','m','y','H','I','M','S','U','W']:
        mapping['%' + k] = digit_pattern(2)

    for k, v in [
        ('p', ['AM','PM']),
        ('a', ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']),
        ('A', ['Monday','Tuesday','Wednesday','Thursday',
               'Friday','Saturday','Sunday']),
        ('b', ['Jan','Feb','Mar','Apr','May','Jun',
               'Jul','Aug','Sep','Oct','Nov','Dec']),
        ('B', ['January','February','March','April','May','June','July',
               'August','September','October','November','December']),
        ]:
        mapping['%' + k] = r'(?:%s)' % '|'.join(v)

    for k in ['z','Z','c','x','X']:
        if '%' + k in date_format:
            raise NotImplementedError

    pattern = re.escape(date_format)

    for k, v in mapping.items():
        pattern = pattern.replace(re.escape(k), v)

    return f'({pattern})' if encase else pattern