import calendar
import holidays
import pandas as pd
import numpy as np
import re
import datetime
import time
from textwrap import wrap as wrap_text




#+---------------------------------------------------------------------------+
# Freestanding functions
#+---------------------------------------------------------------------------+

def Date(arg=None, normalize=False, week_offset=0):
    '''
    Description
    ----------
    assigns new date instances to the correct class polymorphism

    Parameters
    ----------
    arg : str | object
        object to convert to DateBase object. Currently supported formats include:
            • None (the current date and time will be used)
            • pandas._libs.tslibs.timestamps.Timestamp
            • datetime.datetime
            • datetime.date
            • integer (in seconds)
            • string
                -> day of the week fully spelled out or first 3 letters (not case sensitive)
                  (e.g. 'Monday', 'monday', 'mon')
                -> quarter in #QYY or YYYYQ# format
                -> any string format supported by pd.to_datetime
            • DateBase object or DateBase polymorphism
    normalize : bool
        if True, only the year, month, and day are retained (hours, minutes, seconds, microseconds are set to zero)
    week_offset : int
        by default, if a day of the week is supplied (e.g. 'Monday') then the date returned will be that day of the week
        for the current week. This argument is used to override this behavior by shifting the week backwards or forwards
        (e.g. if arg='Monday' and week_offset=-1 then the Monday of last week will be returned).

    Returns
    ----------
    out : DateBase | DateBase polymorphism
        DateBase object or polymorphism
    '''

    qtr_map = {k: i for i,k in enumerate([(3,31), (6,30), (9,30), (12,31)], 1)}

    def qtr_label_to_dt(x):
        ''' attempts to convert quarter expressed as string to datetime. Suported formats include #QYY and YYYYQ# '''
        try:
            qtr, year = re.findall(r'(\d{1})Q(\d{2})', x)[0]
        except:
            try:
                year, qtr = re.findall(r'(\d{4})Q(\d{1})', x)[0]
            except:
                return

        inverse = {v: k for k,v in qtr_map.items()}
        month, day = inverse[int(qtr)]
        out = DateBase.to_datetime(f'{month}-{day}-{year}')
        return out


    if arg is None:
        dt = datetime.datetime.now()
    elif hasattr(arg, 'to_pydatetime'): # pandas
        dt = arg.to_pydatetime()
    elif isinstance(arg, datetime.datetime):
        dt = arg
    elif isinstance(arg, datetime.date):
        dt = datetime.datetime(arg.year, arg.month, arg.day)
    elif isinstance(arg, int): # is timestamp expressed in seconds
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

    if dt.day == n_days_in_month(dt.year, dt.month):
        qtr = qtr_map.get((dt.month, dt.day))
        return QuarterEnd(dt, qtr) if qtr else MonthEnd(dt)
    else:
        return DateBase(dt)



def add_border(text, width=75):
    ''' adds a border around text '''
    text = '\n '.join(wrap_text(' '.join(text.split()), width))
    out = '{0}{1}{0}\n {2}\n{0}{1}{0}'.format('+', width * '-', text)
    return out



def elapsed_time(seconds):
    '''
    Parameters
    ----------
    seconds : float
        seconds
    '''
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



def n_days_in_month(year, month):
    '''
    Description
    ----------
    Returns the # of days in a month for a given year.
    For example, if year=2024 and month=2, 29 days is returned since it's a leap year

    Parameters
    ----------
    year : int
        year in YYYY format
    month : int
        month

    Returns
    ----------
    out : int
        number of days
    '''
    out = calendar.monthrange(year, month)[1]
    return out



def last_day_of_month(year, month):
    '''
    Description
    ----------
    Returns date of the last day of the month for a given year and month

    Parameters
    ----------
    year : int
        year in YYYY format
    month : int
        month

    Returns
    ----------
    clockwork.{MonthEnd}|{QuarterEnd}
    '''
    day = n_days_in_month(year, month)
    return Date(datetime.datetime(year, month, day))



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



def day_of_week(day, delta=0):
    ''' see DateBase.first_last decorator for documentation '''
    return Date(normalize=True).last(day, delta)



def month_end(delta=0):
    '''
    Description
    ----------
    Returns month end date

    Parameters
    ----------
    delta : int
        Offset value +/- from the most recent month end (e.g. 0 is the most recent month end and -1 is the 2nd most recent month end).

    Returns
    ----------
    clockwork.MonthEnd object
    '''
    y, m = divmod(datetime.date.today().year * 12 + datetime.date.today().month + delta - 1, 12)
    if m == 0:
        y -= 1
        m = 12
    d = n_days_in_month(y, m)
    return MonthEnd(datetime.datetime(y, m, d))



def quarter_end(delta=0, scheme=None):
    '''
    Description
    ----------
    Returns quarter end date

    Parameters
    ----------
    delta : int | str
        clockwork.date() -> 'date' argument.
        Integer values are treated as offsets +/- from the most recent quarter end (e.g. 0 is the most recent quarter
        end and -1 is the 2nd most recent quarter end).
        String values represent specific quarters. Acceptable formats include: '#QYY' or 'YYYYQ#'
    scheme : tuple
        Tuple listing the quarter end months. Defaults to calendar year-end.

    Returns
    ----------
    clockwork.QuarterEnd object
    '''
    if isinstance(delta, str): return Date(delta)
    if scheme is not None: raise NotImplementedError
    scheme = (3, 6, 9, 12)
    today = datetime.datetime.now()
    cy, cm, cd = today.year, today.month, today.day
    if cd <= n_days_in_month(cy, cm): cm -= 1
    candidates = [((cy * 12) + m) + (delta * 3) - 1 for m in scheme]
    candidates.insert(0,((cy - 1) * 12) + scheme[-1] + (delta * 3) - 1)
    y, m = divmod(candidates[np.digitize(((cy * 12) + cm + (delta * 3)), candidates, right=True) - 1], 12)
    m += 1
    d = n_days_in_month(y, m)
    quarter, quarter_date = scheme.index(m) + 1, datetime.datetime(y, m, d)
    return QuarterEnd(quarter_date, quarter)



def year_end(delta=0, **kwargs):
    ''' returns year end date as a QuarterEnd object '''
    quarter = quarter_end().qtr
    delta = (4 * delta) + (4 - quarter)
    return quarter_end(delta, **kwargs)



#+---------------------------------------------------------------------------+
# Classes
#+---------------------------------------------------------------------------+

class DateBase(object):
    '''
    Description
    --------------------
    user-friendly object-oriented representation of a date

    Class Attributes
    --------------------
    weekdays : dict
        dictionary where keys are the days of the week and values are the corresponding index values
    holidays : holidays.countries.united_states.UnitedStates
        comprehensive list of U.S. holidays

    Instance Attributes
    --------------------
    datetime : datetime.datetime
        date and time (if applicable)
    '''

    weekdays = {'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3, 'Friday': 4, 'Saturday': 5, 'Sunday': 6}
    weekdays.update({k[:3]: v for k,v in weekdays.items()})
    holidays = holidays.UnitedStates()


    def __init__(self, arg=None):
        self.datetime = arg


    #+---------------------------------------------------------------------------+
    # Static Methods
    #+---------------------------------------------------------------------------+

    @staticmethod
    def to_timestamp(arg, **kwargs):
        ''' converts date in any format to timestamp '''
        if not isinstance(arg, datetime.datetime):
            arg = DateBase.to_datetime(arg, **kwargs)
        return int(time.mktime(arg.timetuple()))


    @staticmethod
    def to_datetime(arg, **kwargs):
        ''' converts date in any format to datetime.datetime '''
        return pd.to_datetime(arg, **kwargs).to_pydatetime()



    #+---------------------------------------------------------------------------+
    # Classes
    #+---------------------------------------------------------------------------+

    class Decorators(object):

        @classmethod
        def other_to_dt(cls, func):
            ''' decorator converts other argument used in magic methods to datetime '''
            def wrapper(self, other):
                if hasattr(other, 'dt'):
                    other = other.dt
                else:
                    other = DateBase.to_datetime(other)
                return func(self, other)
            return wrapper

        @classmethod
        def arithmetic_other(cls, func):
            ''' decorator converts other argument used in magic methods to datetime '''
            def wrapper(self, other):
                try:
                    other = datetime.timedelta(float(other))
                    return Date(func(self, other))
                except:
                    other = Date(other).dt
                    return func(self, other)

            return wrapper


        @classmethod
        def next_last(cls, func):
            ''' decorator performs next/last logic '''
            def wrapper(self, weekday, delta=0):
                '''
                returns DateBase object representing the next or last day of the week relative to self. For example self.next('Mon')
                would return the date of the following monday.

                Attributes
                -----------------------
                weekday : str
                    Day of the week either fully spelled out or the first three characters (e.g. 'Friday' or 'Fri') not case-sensitive.
                delta : int
                    Offset value +/- from the current week (e.g. 0 is the current week and -1 is last week).
                '''
                day, desired_day = self.dt.weekday(), self.weekdays[weekday.title()]
                delta += func(self, day - desired_day)
                return self.minus(days=day).plus(days=desired_day, weeks=delta)
            return wrapper



    #+---------------------------------------------------------------------------+
    # Class Methods
    #+---------------------------------------------------------------------------+
    # None


    #+---------------------------------------------------------------------------+
    # Properties
    #+---------------------------------------------------------------------------+

    @property
    def dt(self):
        ''' datetime alias '''
        return self.datetime

    @property
    def pandas(self):
        ''' pandas format '''
        return pd.to_datetime(self.dt)

    @property
    def sql_server(self):
        ''' string in YYYY-MM-DD format '''
        return self.str('%Y-%m-%d')

    @property
    def sqlsvr(self):
        ''' sql_server alias '''
        return self.sql_server

    @property
    def oracle(self):
        ''' string in DD-%b-YY (e.g. 30-Sep-19) format '''
        return self.str('%d-%b-%y')

    @property
    def timestamp(self):
        ''' integer '''
        return self.to_timestamp(self.dt)

    @property
    def year(self):
        return self.dt.year

    @property
    def month(self):
        return self.dt.month

    @property
    def month_name(self):
        return self.dt.strftime('%B')

    @property
    def day(self):
        return self.dt.day

    @property
    def yesterday(self):
        return self - 1

    @property
    def tomorrow(self):
        return self + 1

    @property
    def month_start(self):
        ''' return date object representing the first day of the month '''
        return Date(datetime.datetime(self.year, self.month, 1))

    @property
    def month_end(self):
        ''' last day of the month as a MonthEnd instance '''
        return last_day_of_month(self.year, self.month)

    @property
    def last_business_day_of_month(self):
        dt = self.month_end
        dt -= {'Saturday': 1, 'Sunday': 2}.get(dt.weekday, 0)
        return dt

    @property
    def weekday(self):
        out = {
            0: 'Monday',
            1: 'Tuesday',
            2: 'Wednesday',
            3: 'Thursday',
            4: 'Friday',
            5: 'Saturday',
            6: 'Sunday'
            }[self.dt.weekday()]
        return out


    @property
    def is_business_day(self):
        ''' returns True if date does not fall on a weekend '''
        return self.weekday not in ('Saturday','Sunday')

    @property
    def is_business_hours(self):
        ''' returns True if date is within business hours (8am - 9pm) '''
        set_hour = lambda hour: datetime.datetime(self.year, self.month, self.day, hour)
        out = self.is_business_day and self.dt >= set_hour(8) and self.dt <= set_hour(21)
        return out

    @property
    def is_holiday(self):
        ''' returns True if date is a U.S. holiday '''
        return self.sqlsvr in self.holidays


    @property
    def is_today(self):
        ''' returns True if date is the current day '''
        return self.sqlsvr == Date().sqlsvr


    @property
    def holiday(self):
        ''' returns the current holiday, if applicable '''
        return self.holidays.get(self.sqlsvr)


    @property
    def is_quarter_end(self):
        ''' returns True if the date is a quarter end date '''
        return isinstance(Date(self.sqlsvr), QuarterEnd)

    @property
    def is_month_end(self):
        '''' returns True if the date is a month end date '''
        return isinstance(Date(self.sqlsvr), MonthEnd)



    #+---------------------------------------------------------------------------+
    # Magic Methods
    #+---------------------------------------------------------------------------+

    def __repr__(self):
        return str(self)

    def __str__(self):
        components = ['%Y-%m-%d']
        if self.dt.hour + self.dt.second + self.dt.microsecond > 0:
            components.append('%I:%M:%S.%f %p')
        return self.str(' '.join(components))

    def __int__(self):
        return self.timestamp

    @Decorators.other_to_dt
    def __eq__(self, other):
        return self.dt == other

    @Decorators.other_to_dt
    def __ne__(self, other):
        return self.dt != other

    @Decorators.other_to_dt
    def __lt__(self, other):
        return self.dt < other

    @Decorators.other_to_dt
    def __gt__(self, other):
        return self.dt > other

    @Decorators.other_to_dt
    def __le__(self, other):
        return self.dt <= other

    @Decorators.other_to_dt
    def __ge__(self, other):
        return self.dt >= other

    @Decorators.arithmetic_other
    def __add__(self, other):
        ''' if other is date-like then implements default behavior for adding datetimes otherwise
        other is treated as timedelta '''
        return self.dt + other

    @Decorators.arithmetic_other
    def __sub__(self, other):
        ''' if other is date-like then implements default behavior for subtracting datetimes otherwise
        other is treated as timedelta '''
        return self.dt - other

    @Decorators.other_to_dt
    def __contains__(self, item):
        return self.normalize(item).dt <= self.dt < (self.normalize(item) + 1).dt



    #+---------------------------------------------------------------------------+
    # Instance Methods
    #+---------------------------------------------------------------------------+

    def skip_weekend(self, forward=True):
        x = 2 if forward else -1
        if self.weekday == 'Saturday':
            return self + x
        elif self.weekday == 'Sunday':
            return self + (x - 1)
        else:
            return self


    def business_day_delta(self, delta):
        forward = True if delta >= 0 else False
        if forward:
            start, stop, step = 1, delta + 1, 1
        else:
            start, stop, step = -1, delta - 1, -1

        weekend_days = 0
        for x in range(start, stop, step):
            if (self.dt + datetime.timedelta(x)).weekday() in (5, 6):
                weekend_days += 1
        out = self.skip_weekend(self.dt + datetime.timedelta(delta + (weekend_days * step)), forward)
        return out


    def skip_holiday(self, forward=True):
        if self.is_holiday:
            return (self + (1 if forward else -1)).skip_holiday(forward=forward)
        else:
            return self



    def month_shift(self, n_months=0, month_end='', day=None):
        '''
        Description
        ----------
        returns Date instance representing current instance shifted by a specified number of months.
        Note: If you want to shift by days use +/- operators. You could also achieve the same result
        by using the plus and minus methods.

        Parameters
        ----------
        n_months : int
            number of months to shift. Positive values shift forward and negative shift backwards
        month_end : bool
            if True, the day is set equal to the last day of the month that was shifted to.
            This cannot be set to True if a day argument is passed.
        day : int
            day of the month once the the shift takes place. Must be None if a month_end is True.

        Returns
        ----------
        out : DateBase | DateBase polymorphism
            date object
        '''
        if month_end and day is not None:
            raise ValueError("cannot set 'month_end' to True and pass a 'day' argument simultaneously")
        if n_months == 0:
            y, m = self.year, self.month
        else:
            y, m = list(month_year_iter(start_month=self.month, start_year=self.year, rng=n_months))[-1]

        d = n_days_in_month(y, m)
        if day is not None:
            if day > d or day < 1:
                raise ValueError("day argument out of bounds")
            else:
                d = day

        out = Date(datetime.datetime(y, m, d))
        return out

    def str(self, fmt):
        ''' strftime shortcut '''
        return self.dt.strftime(fmt)

    def plus(self, **kwargs):
        ''' timedelta kwargs = weeks, days, hours, minutes, seconds, seconds, etc '''
        return Date(self.dt + datetime.timedelta(**kwargs))

    def minus(self, **kwargs):
        ''' timedelta kwargs = weeks, days, hours, minutes, seconds, seconds, etc '''
        return Date(self.dt - datetime.timedelta(**kwargs))

    @Decorators.next_last
    def next(self, x):
        ''' see decorator for documentation '''
        return +1 if x >= 0 else 0


    @Decorators.next_last
    def last(self, x):
        ''' see decorator for documentation '''
        return -1 if x <= 0 else 0


    def normalize(self, inplace=False):
        ''' the time component (hours, minutes, seconds, microseconds) is set to zero (midnight) '''
        out = Date(datetime.datetime(self.year, self.month, self.day))
        if inplace:
            self = out
        else:
            return out



class MonthEnd(DateBase):

    def __init__(self, dt):
        super().__init__(dt)

    @property
    def label(self):
        return self.str('%Y%b')

    @property
    def short(self):
        return self.str('%b-%y')

    @property
    def mid(self):
        return self.str('%b%y')

    @property
    def last_qtr(self):
        ''' returns most recent quarter end '''
        delta = 0
        while True:
            dt = self.shift(delta=delta)
            if isinstance(dt, QuarterEnd): break
            delta -= 1
        return dt



class QuarterEnd(MonthEnd):

    def __init__(self, dt, qtr, *args, **kwargs):
        super().__init__(dt)
        self.qtr = qtr

    @property
    def label(self):
        return f'{self.year}Q{self.qtr}'

    @property
    def strqtr(self):
        return self.label

    @property
    def quarter(self):
        return self.qtr

    @property
    def short(self):
        return f'Q{self.qtr}'

    @property
    def mid(self):
        return f'{self.qtr}Q{str(self.year)[2:]}'










if __name__ == '__main__':
    pass