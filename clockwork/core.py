import datetime
import re
import numpy as np

from ._base import DateBase
from ._quarter_end import QuarterEnd
from ._month_end import MonthEnd



#╭-------------------------------------------------------------------------╮
#| Functions                                                               |
#╰-------------------------------------------------------------------------╯

def Date(arg=None, normalize=False, format=None, week_offset=0):
    '''
    Description
    ------------
    assigns new date instances to the correct class polymorphism

    Parameters
    ------------
    arg : str | object
        object to convert to DateBase object. Currently supported formats include:
            • None (the current date and time will be used)
            • pandas._libs.tslibs.timestamps.Timestamp
            • datetime.datetime
            • datetime.date
            • integer or float (in seconds)
            • string
                ► day of the week fully spelled out or first 3 letters (not case sensitive)
                  (e.g. 'Monday', 'monday', 'mon')
                ► quarter in #QYY, YYYYQ#, or Q# format
                ► any string format supported by pd.to_datetime
            • DateBase object or DateBase polymorphism
    normalize : bool
        if True, only the year, month, and day are retained (hours, minutes, seconds, microseconds are set to zero)
    format : str
        if 'arg' is a string, this format is used to parse it (e.g. '%Y%m%d %H%S').
    week_offset : int
        by default, if a day of the week is supplied (e.g. 'Monday') then the date returned will be that day of the week
        for the current week. This argument is used to override this behavior by shifting the week backwards or forwards
        (e.g. if arg='Monday' and week_offset=-1 then the Monday of last week will be returned).

    Returns
    ------------
    out : DateBase | DateBase polymorphism
        DateBase object or polymorphism
    '''

    qtr_map = {k: i for i,k in enumerate([(3,31), (6,30), (9,30), (12,31)], 1)}

    def qtr_label_to_dt(x):
        ''' attempts to convert quarter expressed as string to datetime.
            Suported formats include #QYY and YYYYQ# '''
        x = x.upper()
        try:
            qtr, year = re.findall(r'^(\d{1})Q(\d{2})$', x)[0]
        except:
            try:
                year, qtr = re.findall(r'^(\d{4})Q(\d{1})$', x)[0]
            except:
                try:
                    qtr = re.findall(r'^Q(\d{1})$', x)[0]
                    year = datetime.datetime.now().year
                except:
                    return

        inverse = {v: k for k, v in qtr_map.items()}
        month, day = inverse[int(qtr)]
        out = DateBase.to_datetime(f'{month}-{day}-{year}')
        return out


    if format is not None:
        if not isinstance(arg, str):
            raise TypeError(f"When 'format' argument is not None, 'arg' must be a string, not {type(arg)}.")
        arg = DateBase.to_datetime(arg, format=format)
        return Date(arg, normalize=normalize)

    if arg is None:
        dt = datetime.datetime.now()
    elif hasattr(arg, 'to_pydatetime'): # pandas
        dt = arg.to_pydatetime()
    elif isinstance(arg, datetime.datetime):
        dt = arg
    elif isinstance(arg, datetime.date):
        dt = datetime.datetime(arg.year, arg.month, arg.day)
    elif (isinstance(arg, float) and not np.isnan(arg)) or isinstance(arg, int):
        # timestamp expressed in seconds
        dt = datetime.datetime.fromtimestamp(arg)
    elif isinstance(arg, str):
        desired_day = DateBase.weekdays.get(arg.title())
        if desired_day is None:
            dt = qtr_label_to_dt(arg) or DateBase.to_datetime(arg)
        else:
            normalize, now = True, datetime.datetime.now()
            dt = now - datetime.timedelta(days=now.weekday()) + \
                       datetime.timedelta(days=desired_day, weeks=week_offset)
    elif isinstance(arg, DateBase):
        dt = arg.dt
    else:
        raise ValueError(f'date argument {arg} of type {type(arg)} is not supported.')

    if normalize: dt = datetime.datetime(dt.year, dt.month, dt.day)

    if dt.day == DateBase.n_days_in_month(dt.year, dt.month):
        qtr = qtr_map.get((dt.month, dt.day))
        return QuarterEnd(dt, qtr) if qtr else MonthEnd(dt)
    else:
        return DateBase(dt)



def day_of_week(day, delta=0):
    ''' see DateBase.first_last decorator for documentation '''
    return Date(normalize=True).last(day, delta)



def month_end(delta=0):
    '''
    Description
    ------------
    Returns month end date

    Parameters
    ------------
    delta : int | str | DateBase
        Offset value +/- from the most recent month end (e.g. 0 is the most recent month end and -1 is the 2nd most recent month end).

    Returns
    ------------
    clockwork.MonthEnd object
    '''
    if isinstance(delta, (DateBase, str)): return Date(delta)
    y, m = divmod(datetime.date.today().year * 12 + datetime.date.today().month + delta - 1, 12)
    if m == 0:
        y -= 1
        m = 12
    return MonthEnd(datetime.datetime(y, m, 1))



def quarter_end(delta=0, scheme=None):
    '''
    Description
    ------------
    Returns quarter end date

    Parameters
    ------------
    delta : int | str | DateBase
        clockwork.date() -> 'date' argument.
        Integer values are treated as offsets +/- from the most recent quarter end (e.g. 0 is the most recent quarter
        end and -1 is the 2nd most recent quarter end).
        String values represent specific quarters. Acceptable formats include: '#QYY' or 'YYYYQ#'
    scheme : tuple
        Tuple listing the quarter end months. Defaults to calendar year-end.

    Returns
    ------------
    clockwork.QuarterEnd object
    '''
    if isinstance(delta, (DateBase, str)): return Date(delta)
    if scheme is not None: raise NotImplementedError
    scheme = (3, 6, 9, 12)
    today = datetime.datetime.now()
    cy, cm, cd = today.year, today.month, today.day
    if cd <= DateBase.n_days_in_month(cy, cm): cm -= 1
    candidates = [((cy * 12) + m) + (delta * 3) - 1 for m in scheme]
    candidates.insert(0,((cy - 1) * 12) + scheme[-1] + (delta * 3) - 1)
    y, m = divmod(candidates[np.digitize(((cy * 12) + cm + (delta * 3)), candidates, right=True) - 1], 12)
    m += 1
    return QuarterEnd(dt=datetime.datetime(y, m, 1), qtr=scheme.index(m) + 1)



def year_end(delta=0, **kwargs):
    ''' returns year end date as a QuarterEnd object '''
    quarter = quarter_end().qtr
    delta = (4 * delta) + (4 - quarter)
    return quarter_end(delta, **kwargs)



#╭-------------------------------------------------------------------------╮
#| Assign Class Attribute                                                  |
#╰-------------------------------------------------------------------------╯

DateBase.factory = Date