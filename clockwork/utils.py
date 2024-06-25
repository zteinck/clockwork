import re
import time
from textwrap import wrap as wrap_text



#╭-------------------------------------------------------------------------╮
#| Functions                                                               |
#╰-------------------------------------------------------------------------╯

def elapsed_time(seconds):
    out = []
    for k,v in [('days', 86400), ('hours', 3600), ('minutes', 60)]:
        count = int(seconds / v)
        if count > 0:
            out.append(f'{count} {k}')
            seconds -= count * v
    out.append(f'{round(seconds, 2)} seconds')
    return ', '.join(out)


def action_timer(func):

    def wrapper(*args, **kwargs):
        start_time = time.time()
        print(add_border(func.__name__, width=75))
        print()
        out = func(*args, **kwargs)
        print(add_border(f'{func.__name__} complete in {elapsed_time(time.time() - start_time)}', width=75))
        print()
        return out

    return wrapper


def month_year_iter(start_month, start_year, end_month=None, end_year=None, rng=None, step=0):

    start = 12 * start_year + start_month - 1

    if not any((end_month, end_year, rng)):
        while True:
            y,m = divmod(start, 12)
            start += 1
            yield y, m + 1
    else:
        if all((end_month, end_year)):
            end = 12 * end_year + end_month
        elif rng:
            rng += (1 if rng > 0 else -1)
            end = start + rng
        else:
            raise ValueError('end_month and end_year arguments must both be provided.')

        if end < start:
            if step == 0: step = -1
            if step > 0: step *= -1

        month_range = range(start,end,step) if step else range(start, end)

        for x in month_range:
            y,m = divmod(x, 12)
            yield y, m + 1


def convert_date_format_to_regex(date_format, encase=False):
    '''
    Description
    ------------
    Converts string of datetime format codes to its regex counterpart.

    Examples:
    ------------
        • '%Y-%m-%d %I:%M:%S.%f %p' ➜ '\d{4}\-\d{2}\-\d{2}\ \d{2}:\d{2}:\d{2}\.\d{6}\ (?:AM|PM)'
        • '%m/%d/%y' ➜ \d{2}/\d{2}/\d{2}

    Parameters
    ------------
    date_format : str
        string of datetime format codes (e.g. '%Y-%m-%d')
    encase : bool
        if True, the output will be encased in parenthesis

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
        ('A', ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']),
        ('b', ['Jan','Feb','Mar','Apr','May','Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']),
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


def add_border(text, width=100, fixed_width=False, align='left'):
    '''
    Description
    ----------
    Adds a border around text.

    Parameters
    ----------
    text : str
        text to encase
    width : int
        wrap_text width argument. If width=1, the text is printed vertically.
    fixed_width : bool
        • True -> the width of the border will equal the 'width' argument value.
        • False -> the width of the border is capped at the length of the longest
                   line in the text.
    align : str
        • 'left' -> aligns text along the left margin
        • 'center' -> aligns text in the center between the left and right margins
        • 'right' -> aligns text along the right margin

    Returns
    ----------
    out : str
        text encased within a border
    '''
    lines = wrap_text(' '.join(text.split()), width)
    max_width = width if fixed_width else len(max(lines, key=len))
    border = ('-' * (max_width + 2)).join(['+'] * 2)

    if align in 'left':
        content = [('| ' + line + ''.join([' '] * (max_width - len(line))) + ' |') for line in lines]
    elif align == 'right':
        content = [('| ' + ''.join([' '] * (max_width - len(line))) + line + ' |') for line in lines]
    elif align == 'center':
        content = [('| ' + ''.join([' '] * ((max_width - len(line)) // 2)) + line +
                           ''.join([' '] * ((max_width - len(line) + 1) // 2)) + ' |') for line in lines]

    out = '\n'.join([border, '\n'.join(content), border])
    return out