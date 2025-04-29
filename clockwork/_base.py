import datetime
import calendar
import time
from dateutil.relativedelta import relativedelta
import holidays as hd
import pandas as pd
import numpy as np


class DateBase(object):
    '''
    Description
    --------------------
    date base class

    Class Attributes
    --------------------
    factory : func
        initializes new instances as the correct subclass
    weekdays : dict
        dictionary where keys are the days of the week and values
        are the corresponding index values
    holidays : holidays.countries.united_states.UnitedStates
        comprehensive list of U.S. holidays

    Instance Attributes
    --------------------
    datetime : datetime.datetime
        date and time (if applicable)
    '''

    #╭-------------------------------------------------------------------------╮
    #| Class Attributes                                                        |
    #╰-------------------------------------------------------------------------╯

    holidays = hd.UnitedStates()
    weekdays = {k: i for i, k in enumerate(calendar.day_name)}
    weekdays.update({k[:3]: v for k, v in weekdays.items()})


    #╭-------------------------------------------------------------------------╮
    #| Initialize Instance                                                     |
    #╰-------------------------------------------------------------------------╯

    def __init__(self, arg=None):
        self.datetime = arg


    #╭-------------------------------------------------------------------------╮
    #| Static Methods                                                          |
    #╰-------------------------------------------------------------------------╯

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


    @staticmethod
    def n_days_in_month(year, month):
        '''
        Description
        ----------
        Returns the # of days in a month for a given year.
        For example, if year=2024 and month=2, 29 days is returned since
        it's a leap year.

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


    #╭-------------------------------------------------------------------------╮
    #| Class Methods                                                           |
    #╰-------------------------------------------------------------------------╯

    @classmethod
    def spawn(cls, *args, **kwargs):
        ''' Spawn a new instance. The factory function assigns the correct subclass '''
        return cls.factory(*args, **kwargs)


    @classmethod
    def last_day_of_month(cls, year, month):
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
        day = cls.n_days_in_month(year, month)
        return cls.spawn(datetime.datetime(year, month, day))


    #╭-------------------------------------------------------------------------╮
    #| Classes                                                                 |
    #╰-------------------------------------------------------------------------╯

    class Decorators(object):

        @classmethod
        def spawn(cls, func):
            ''' spawn new date instance '''

            def wrapper(self, *args, **kwargs):
                return self.spawn(func(self, *args, **kwargs))

            return wrapper


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
                    return self.spawn(func(self, other))
                except:
                    other = self.spawn(other).dt
                    return func(self, other)

            return wrapper


        @classmethod
        def next_last(cls, func):
            ''' decorator performs next/last logic '''

            def wrapper(self, weekday, delta=0):
                '''
                returns DateBase object representing the next or last day of
                the week relative to self. For example self.next('Mon')
                would return the date of the following monday.

                Attributes
                -----------------------
                weekday : str
                    Day of the week either fully spelled out or the first three
                    characters (e.g. 'Friday' or 'Fri') not case-sensitive.
                delta : int
                    Offset value +/- from the current week (e.g. 0 is the current
                    week and -1 is last week).
                '''
                day, desired_day = self.dt.weekday(), self.weekdays[weekday.title()]
                delta += func(self, day - desired_day)
                return self.minus(days=day).plus(days=desired_day, weeks=delta)

            return wrapper


    #╭-------------------------------------------------------------------------╮
    #| Properties                                                              |
    #╰-------------------------------------------------------------------------╯

    @property
    def date(self):
        ''' returns normalized instance '''
        return self.normalize()


    @property
    def d(self):
        ''' converts datetime.datetime to datetime.date '''
        return self.datetime.date()


    @property
    def dt(self):
        ''' datetime alias '''
        return self.datetime


    @property
    def pandas(self):
        ''' pandas format '''
        return pd.to_datetime(self.dt)


    @property
    def ymd(self):
        ''' string in YYYY-MM-DD format '''
        return self.str('%Y-%m-%d')


    @property
    def sql_server(self):
        ''' ymd alias '''
        return self.ymd


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
        return self.spawn(datetime.datetime(self.year, self.month, 1))


    @property
    def month_end(self):
        ''' last day of the month as a MonthEnd instance '''
        return self.last_day_of_month(self.year, self.month)


    @property
    def is_month_end(self):
        ''' returns True if date aligns with a month-end date '''
        return self.ymd == self.month_end.ymd


    @property
    def last_business_day_of_month(self):
        dt = self.month_end
        dt -= {'Saturday': 1, 'Sunday': 2}.get(dt.weekday, 0)
        return dt


    @property
    def weekday(self):
        return self.str('%A')


    @property
    def weekday_short(self):
        return self.str('%a')


    @property
    def is_weekend(self):
        ''' returns True if date does not fall on a weekend '''
        return self.weekday in ('Saturday','Sunday')


    @property
    def is_holiday(self):
        ''' returns True if date is a U.S. holiday '''
        return self.ymd in self.holidays


    @property
    def is_business_day(self):
        ''' returns True if date does not fall on a weekend '''
        return not (self.is_weekend or self.is_holiday)


    @property
    def is_business_hours(self):
        ''' returns True if date is within business hours (8am - 9pm) '''
        set_hour = lambda hour: datetime.datetime(self.year, self.month, self.day, hour)
        out = self.is_business_day and self.dt >= set_hour(8) and self.dt <= set_hour(21)
        return out


    @property
    def is_today(self):
        ''' returns True if date is the current day '''
        return self.ymd == self.spawn().ymd


    @property
    def holiday(self):
        ''' returns the current holiday, if applicable '''
        return self.holidays.get(self.ymd)


    #╭-------------------------------------------------------------------------╮
    #| Magic Methods                                                           |
    #╰-------------------------------------------------------------------------╯

    def __repr__(self):
        return str(self)


    def __str__(self):
        components = ['%Y-%m-%d']
        if self.dt.hour + self.dt.second + self.dt.microsecond > 0:
            components.append('%I:%M:%S.%f %p')
        return self.__class__.__name__ + '(%s)' % self.str(' '.join(components))


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
        ''' if other is date-like then implements default behavior for adding
            datetimes otherwise other is treated as timedelta '''
        return self.dt + other


    @Decorators.arithmetic_other
    def __sub__(self, other):
        ''' if other is date-like then implements default behavior for subtracting
            datetimes otherwise other is treated as timedelta '''
        return self.dt - other


    @Decorators.other_to_dt
    def __contains__(self, item):
        return self.normalize(item).dt <= self.dt < (self.normalize(item) + 1).dt


    #╭-------------------------------------------------------------------------╮
    #| Instance Methods                                                        |
    #╰-------------------------------------------------------------------------╯

    def skip_weekend(self, forward=True):
        x = 2 if forward else -1
        if self.weekday == 'Saturday':
            return self + x
        elif self.weekday == 'Sunday':
            return self + (x - 1)
        else:
            return self


    def business_day_delta(self, delta):
        out = self.spawn(self.dt)
        sign = np.sign(delta)

        counter = 0
        while counter < abs(delta):
            out += sign
            while not out.is_business_day:
                out += sign
            counter += 1

        return out


    def skip_holiday(self, forward=True):
        if self.is_holiday:
            return (self + (1 if forward else -1)).skip_holiday(forward=forward)
        else:
            return self


    def str(self, fmt):
        ''' strftime shortcut '''
        return self.dt.strftime(fmt)


    @Decorators.spawn
    def shift(self, **kwargs):
        return self.dt + relativedelta(**kwargs)


    @Decorators.spawn
    def replace(self, **kwargs):
        return self.dt.replace(**kwargs)


    @Decorators.spawn
    def plus(self, **kwargs):
        ''' timedelta kwargs = weeks, days, hours, minutes, seconds, seconds, etc '''
        return self.dt + datetime.timedelta(**kwargs)


    @Decorators.spawn
    def minus(self, **kwargs):
        ''' timedelta kwargs = weeks, days, hours, minutes, seconds, seconds, etc '''
        return self.dt - datetime.timedelta(**kwargs)


    @Decorators.next_last
    def next(self, x):
        ''' see decorator for documentation '''
        return +1 if x >= 0 else 0


    @Decorators.next_last
    def last(self, x):
        ''' see decorator for documentation '''
        return -1 if x <= 0 else 0


    @Decorators.spawn
    def normalize(self):
        ''' the time component (hours, minutes, seconds, microseconds) is set to
            zero (midnight) '''
        return datetime.datetime(self.year, self.month, self.day)