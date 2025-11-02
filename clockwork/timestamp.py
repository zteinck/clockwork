from functools import wraps
import datetime
import calendar
import holidays as hd
import pandas as pd
import numpy as np
import oddments as odd
from copy import deepcopy
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse

from .constants import MONTHS_IN_YEAR


class Timestamp(object):
    '''
    Description
    --------------------
    Timestamp object

    Class Attributes
    --------------------
    business_hours : tuple[int]
        Business hours start and stop times (24-hour clock).
    weekday_map : dict | None
        Dictionary where keys are string representations of weekdays and
        values are their corresponding index values.
    holiday_calendar : holidays.UnitedStates | None
        Comprehensive list of U.S. holidays.
    _month_end_cls : MonthEnd | None
        Month end subclass. Cached at class level to prevent circular imports.
    _quarter_end_cls : QuarterEnd | None
        Quarter end subclass. Cached at class level to prevent circular imports.

    Instance Attributes
    --------------------
    _dt : datetime.datetime
        Wrapped datetime instance.
    '''

    #╭-------------------------------------------------------------------------╮
    #| Class Attributes                                                        |
    #╰-------------------------------------------------------------------------╯

    business_hours = (8, 17) # 8am - 5pm

    weekday_map = None
    holiday_calendar = None
    _month_end_cls = None
    _quarter_end_cls = None


    #╭-------------------------------------------------------------------------╮
    #| Initialize Instance                                                     |
    #╰-------------------------------------------------------------------------╯

    def __init__(self, arg=None, normalize=False, **kwargs):
        '''
        Parameters
        ------------
        arg : None | any
            See '_to_datetime()' documentation.
        normalize : bool
            If True, only the year, month, and day are retained (hours, minutes,
            seconds, and microseconds are set to zero).
        kwargs : dict
            Keyword arguments passed to '_to_datetime()'.
        '''
        self.dt = self._to_datetime(arg, **kwargs)
        if normalize: self.normalize(inplace=True)


    #╭-------------------------------------------------------------------------╮
    #| Classes                                                                 |
    #╰-------------------------------------------------------------------------╯

    class Decorators(object):

        @staticmethod
        def enable_inplace(func):
            ''' Enables in-place updates '''

            @wraps(func)
            def wrapper(self, **kwargs):
                inplace = kwargs.pop('inplace', False)
                dt = func(self, **kwargs)
                if inplace:
                    self.dt = dt
                else:
                    return self.__class__(dt)

            return wrapper


        @staticmethod
        def other_to_dt(func):
            ''' Converts the 'other' argument to a datetime object for use in
                magic methods. '''

            @wraps(func)
            def wrapper(self, other):
                return func(self, self._to_datetime(other))

            return wrapper


        @staticmethod
        def other_to_delta(func):
            ''' Converts the 'other' argument to a time delta object for use in
                magic methods. '''

            @wraps(func)
            def wrapper(self, other):
                # Subtracting a date-like 'other' returns a datetime.timedelta
                # object.
                if func.__name__.replace('_', '') == 'sub' and \
                    not isinstance(other, (dict, float, int)):
                    return func(self, self._to_datetime(other))

                # Otherwise, 'other' is assumed to be a delta and the resulting
                # Timestamp object is returned.
                delta = self._build_delta(other)
                return self._make_base(func(self, delta))

            return wrapper


        @staticmethod
        def skip_shift(func):
            ''' returns the nearest date that does not meet a condition in the
                specified direction '''

            @wraps(func)
            def wrapper(self, forward=True):
                delta = 1 if forward else -1
                attr = 'is_' + '_'.join(func.__name__.split('_')[1:])[:-1]
                obj = self.copy()

                while getattr(obj, attr):
                    obj = obj.shift(days=delta)

                return obj

            return wrapper


        @staticmethod
        def handle_next_last(func):
            ''' Facilitates shifting based on specific weekdays '''

            def wrapper(self, arg, offset=0):
                '''
                Description
                ------------
                Returns an instance representing the next or last day of the
                week relative to self. For example self.next('Mon') would
                return the date of the following Monday. Also supports offsets
                for additional shifting.

                Parameters
                ------------
                arg : str
                    Day of the week either fully spelled out or the first three
                    characters (e.g. 'Friday' or 'Fri') not case-sensitive. Also
                    supports period ends (e.g. 'QE', 'ME').
                offset : int
                    Offset value +/- indicating how many additional weeks to
                    shift. For example, self.next('Mon', offset=+1) would
                    return the Monday two weeks from self.

                Returns
                ------------
                shifted : Timestamp
                    Timestamp instance
                '''
                odd.validate_value(value=arg, name='arg', types=str)
                kind = func.__name__

                # try weekday
                target = self.get_weekday_index(arg)
                if target is not None:
                    actual = self.weekday_index
                    weeks = func(actual - target) + offset
                    return self.shift(days=-actual)\
                               .shift(days=target, weeks=weeks)

                # try period end
                pe_map = {
                    'qe': 'last_quarter_end',
                    'me': 'last_month_end',
                    }

                pe_attr = pe_map.get(arg.lower())

                if pe_attr is not None:
                    obj = getattr(self, pe_attr)
                    if kind == 'next':
                        offset += 1
                    return obj.offset(offset)

                raise ValueError(
                    f"'arg' not recognized: '{arg}'"
                    )

            return wrapper


        @staticmethod
        def to_period_end(func):
            ''' Attempts to convert self to a period end instance '''

            @wraps(func)
            def wrapper(self, strict=True):
                '''
                Description
                ------------
                Handles period end conversion.

                Parameters
                ------------
                strict : bool
                    If True, an exception is raised if self does not already
                             align with a period end date.
                    If False, self will be coerced to a period end date.

                Returns
                ------------
                period_end : MonthEnd | QuarterEnd
                    period end instance.
                '''
                kind = func.__name__.split('_')[1]

                if kind == 'quarter' and not strict:
                    raise NotImplementedError

                if strict and not getattr(self, f'is_{kind}_end'):
                    raise ValueError(
                        f"Conversion to {kind} end failed because "
                        f"{self.ymd!r} does not align with a {kind} "
                        "end date. To convert anyway, use 'strict=False'."
                        )

                pe_cls = getattr(self, f'_get_{kind}_end_cls')()
                return pe_cls(year=self.year, month=self.month)

            return wrapper


    #╭-------------------------------------------------------------------------╮
    #| Properties                                                              |
    #╰-------------------------------------------------------------------------╯

    @property
    def dt(self):
        ''' returns the underlying datetime.datetime object '''
        return self._dt


    @dt.setter
    def dt(self, value):
        if type(value) is datetime.datetime:
            self._dt = value
        else:
            raise TypeError(
                f'Value must be of type <datetime.datetime> when set '
                f'directly, got: {value!r} of type <{type(value).__name__}>.'
                )


    @property
    def datetime(self):
        ''' dt alias '''
        return self.dt


    @property
    def date(self):
        ''' to_date() alias '''
        return self.to_date()


    @property
    def d(self):
        ''' date alias '''
        return self.date


    @property
    def pd(self):
        ''' to_pandas_timestamp() alias '''
        return self.to_pandas_timestamp()


    @property
    def ymd(self):
        ''' string in YYYY-MM-DD format '''
        return self.to_string('%Y-%m-%d')


    @property
    def timestamp(self):
        ''' to_timestamp() alias '''
        return self.to_timestamp()


    @property
    def time(self):
        ''' to_time() alias '''
        return self.to_time()


    @property
    def month_name(self):
        ''' name of month (e.g. 'May') '''
        return self.to_string('%B')


    @property
    def yesterday(self):
        ''' return the date shifted one day earlier '''
        return self.shift(days=-1)


    @property
    def tomorrow(self):
        ''' return the date shifted one day later '''
        return self.shift(days=+1)


    @property
    def month_start(self):
        ''' return the date shifted to the first of the month '''
        return self.replace(day=1)


    @property
    def month_end(self):
        ''' return the last day of the month as a MonthEnd object '''
        return self.to_month_end(strict=False)


    @property
    def is_month_end(self):
        ''' returns True if date aligns with a month end date '''
        return self.is_last_day_of_month


    @property
    def is_quarter_end(self):
        ''' returns True if date aligns with a quarter end date '''
        return self.is_month_end and \
            self.month in self._get_quarter_end_cls().scheme


    @property
    def weekday_name(self):
        ''' weekday name (e.g. 'Monday') '''
        return self.to_string('%A')


    @property
    def weekday_abbr(self):
        ''' abbreviated weekday name (e.g. 'Mon') '''
        return self.to_string('%a')


    @property
    def weekday_index(self):
        ''' abbreviated weekday name (e.g. 'Mon') '''
        return self.dt.weekday()


    @property
    def is_weekend(self):
        ''' returns True if date falls on the weekend '''
        return self.weekday_name in {'Saturday','Sunday'}


    @property
    def is_holiday(self):
        ''' returns True if date is a U.S. holiday '''
        return self.holiday_name is not None


    @property
    def is_non_business_day(self):
        ''' returns True if date is a not a business day '''
        return self.is_weekend or self.is_holiday


    @property
    def is_business_day(self):
        ''' returns True if date is a business day '''
        return not self.is_non_business_day


    @property
    def is_business_hours(self):
        ''' returns True if date is within business hours '''
        if not self.is_business_day:
            return False

        kwargs = {
            k: getattr(self, k)
            for k in ['year','month','day']
            }

        start, stop = [
            datetime.datetime(hour=hour, **kwargs)
            for hour in self.business_hours
            ]

        return start <= self.dt <= stop


    @property
    def is_today(self):
        ''' returns True if date is the current day '''
        return self.date == datetime.date.today()


    @property
    def is_normalized(self):
        ''' returns True if date has no time component (i.e. 00:00:00) '''
        return self.time == datetime.time.min


    @property
    def last_day_of_month(self):
        ''' returns True if it is the last day of the month '''
        return self.days_in_month(self.year, self.month)


    @property
    def is_last_day_of_month(self):
        ''' returns True if it is the last day of the month '''
        return self.day == self.last_day_of_month


    @property
    def holiday_name(self):
        ''' returns the name of the current holiday, if applicable '''
        return self._get_holiday_calendar().get(self.ymd)


    @property
    def last_month_end(self):
        ''' returns most recent month end relative to self '''
        me_cls = self._get_month_end_cls()
        year, month = self.year, self.month
        if not self.is_month_end:
            year, month = self._get_prior_month(year, month)
        return me_cls(year=year, month=month)


    @property
    def last_quarter_end(self):
        ''' returns most recent quarter end relative to self '''
        qe_cls = self._get_quarter_end_cls()
        year, month = self.year, self.month
        if not self.is_quarter_end:
            year, month = qe_cls._backtrack_to_scheme(self.year, self.month)
        return qe_cls(year=year, month=month)


    #╭-------------------------------------------------------------------------╮
    #| Magic Methods                                                           |
    #╰-------------------------------------------------------------------------╯

    def __getattr__(self, name):
        return getattr(self.dt, name)


    def __copy__(self):
        return self.copy()


    def __deepcopy__(self, memo):
        return self.copy()


    def __repr__(self):
        return str(self)


    def __str__(self):
        parts = ['%Y-%m-%d']
        if not self.is_normalized:
            parts.append('%I:%M:%S.%f %p')
        return '{0}({1})'.format(
            self.__class__.__name__,
            self.to_string(' '.join(parts))
            )


    def __float__(self):
        return self.to_timestamp()


    def __int__(self):
        return int(float(self))


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


    @Decorators.other_to_delta
    def __add__(self, other):
        return self.dt + other


    @Decorators.other_to_delta
    def __sub__(self, other):
        ''' see add documentation '''
        return self.dt - other


    @Decorators.other_to_delta
    def __iadd__(self, other):
        self.dt += other
        return self


    @Decorators.other_to_delta
    def __isub__(self, other):
        self.dt -= other
        return self


    #╭-------------------------------------------------------------------------╮
    #| Instance Methods                                                        |
    #╰-------------------------------------------------------------------------╯

    def copy(self):
        ''' returns a deep copy of self '''
        dt = self.to_datetime()
        return self.__class__(dt)


    def to_base(self):
        ''' return a base-class version of this instance '''
        return self._make_base(self)


    def to_datetime(self):
        ''' returns a copy of the underlying datetime.datetime object '''
        return deepcopy(self.dt)


    def to_pandas_timestamp(self):
        ''' return as a pd.Timestamp object '''
        return pd.to_datetime(self.dt)


    def to_timestamp(self):
        ''' returns timestamp expressed in seconds '''
        return self.pd.timestamp()


    def to_date(self):
        ''' return the date component as a 'datetime.date' object '''
        return self.dt.date()


    def to_time(self):
        ''' returns the time component as a 'datetime.time' object '''
        return self.dt.time()


    def to_string(self, format):
        ''' strftime alias '''
        return self.strftime(format)


    @Decorators.skip_shift
    def skip_holidays():
        ''' returns the nearest non-holiday date by skipping holidays in the
            specified direction '''
        pass


    @Decorators.skip_shift
    def skip_weekends():
        ''' returns the nearest non-weekend date by skipping weekends in the
            specified direction '''
        pass


    @Decorators.skip_shift
    def skip_non_business_days():
        ''' returns the nearest business day date by skipping non-business
            days in the specified direction '''
        pass


    @Decorators.enable_inplace
    def normalize(self, **kwargs):
        return self._normalize(self)


    @Decorators.enable_inplace
    def replace(self, **kwargs):
        return self.dt.replace(**kwargs)


    def _build_delta(self, kwargs):
        ''' constructs a time delta object from keyword arguments '''
        if not isinstance(kwargs, dict):
            kwargs = dict(days=kwargs)

        relative = kwargs.pop('relative', False)

        if not kwargs:
            raise ValueError("'kwargs' is empty?")

        return (relativedelta if relative else
                datetime.timedelta)(**kwargs)


    def _shift(self, **kwargs):
        delta = self._build_delta(kwargs)
        return self._make_base(self.dt + delta)


    def shift(self, **kwargs):
        '''
        Description
        ------------
        Returns a Timestamp object representing self shifted by a delta.

        Parameters
        ------------
        kwargs : dict
            Keyword arguments for time delta construction. In addition to
            the standard parameters, several custom options are also
            available:

            relative : bool
                If True, kwargs are passed to 'relative_delta' instead of
                'datetime.timedelta'.
            biz_days : int
                Similar to the datetime.timedelta days argument, except
                weekends and holidays are excluded from the count.

        Returns
        ------------
        shifted : Timestamp
            Timestamp object representing self post-shift.
        '''
        biz_days = kwargs.pop('biz_days', None)
        obj = self._shift(**kwargs) if kwargs else self.copy()

        if biz_days is None:
            if kwargs: return obj
            raise ValueError("'kwargs' cannot be empty")

        delta = int(np.sign(biz_days))

        counter = 0
        while counter < abs(biz_days):
            obj = obj._shift(days=delta)
            if obj.is_business_day:
                counter += 1

        return obj


    @Decorators.handle_next_last
    def next(x):
        ''' see decorator for documentation '''
        return +1 if x >= 0 else 0


    @Decorators.handle_next_last
    def last(x):
        ''' see decorator for documentation '''
        return -1 if x <= 0 else 0


    @Decorators.to_period_end
    def to_month_end():
        pass


    @Decorators.to_period_end
    def to_quarter_end():
        pass


    #╭-------------------------------------------------------------------------╮
    #| Static Methods                                                          |
    #╰-------------------------------------------------------------------------╯

    @staticmethod
    def _make_base(*args, **kwargs):
        return Timestamp(*args, **kwargs)


    @staticmethod
    def days_in_month(year, month):
        '''
        Description
        ------------
        Returns the # of days in a month for a given year. For example, if
        year=2024 and month=2, 29 days is returned since it's a leap year.

        Parameters
        ------------
        year : int
            year
        month : int
            month

        Returns
        ------------
        out : int
            Number of days.
        '''
        return calendar.monthrange(year, month)[1]


    @staticmethod
    def _normalize(obj):
        ''' Sets the time attributes (hours, minutes, seconds, microseconds)
            all to zero (midnight) '''
        kwargs = {k: getattr(obj, k) for k in ['year','month','day']}
        return datetime.datetime(**kwargs)


    @staticmethod
    def _validate_month(month):
        if not (1 <= month <= MONTHS_IN_YEAR):
            raise ValueError(
                "'month' must be between 1 and "
                f"{MONTHS_IN_YEAR}, got: {month}."
                )


    @staticmethod
    def _total_months(years, months):
        ''' computes total number of months '''
        return MONTHS_IN_YEAR * years + months


    @staticmethod
    def _try_int(x):
        odd.validate_value(x, (int, str))

        if isinstance(x, str):
            if x.isdigit():
                return int(x)
            raise TypeError(
                "Failed to convert 'x' "
                f"to integer: {x!r}"
                )

        return x


    #╭-------------------------------------------------------------------------╮
    #| Class Methods                                                           |
    #╰-------------------------------------------------------------------------╯

    @classmethod
    def _get_prior_month(cls, year, month):
        cls._validate_month(month)
        month -= 1
        if month == 0:
            year -= 1
            month = 12
        return year, month


    @classmethod
    def _get_holiday_calendar(cls):
        if cls.holiday_calendar is None:
            cls.holiday_calendar = hd.UnitedStates()
        return cls.holiday_calendar


    @classmethod
    def _get_weekday_map(cls):
        if cls.weekday_map is None:
            out = {k: i for i, k in enumerate(calendar.day_name)}
            out.update({k[:3]: v for k, v in out.items()})
            cls.weekday_map = out

        return cls.weekday_map


    @classmethod
    def get_weekday_index(cls, weekday):
        return cls._get_weekday_map().get(weekday.title())


    @classmethod
    def _get_month_end_cls(cls):
        if cls._month_end_cls is None:
            from .month_end import MonthEnd
            cls._month_end_cls = MonthEnd
        return cls._month_end_cls


    @classmethod
    def _get_quarter_end_cls(cls):
        if cls._quarter_end_cls is None:
            from .quarter_end import QuarterEnd
            cls._quarter_end_cls = QuarterEnd
        return cls._quarter_end_cls


    @classmethod
    def _to_datetime(cls, arg, format=None, offset=0):
        '''
        Description
        ------------
        Converts a scalar to datetime.datetime instance.

        Parameters
        ------------
        arg : None | any
            Scalar to convert. Supported formats include:
                • None returns current datetime (i.e. now)
                • pd.Timestamp
                • cw.Timestamp or subclass
                • datetime.datetime
                • datetime.date
                • int or float (in seconds)
                • str
                    ► Day of the week fully spelled out or first 3 letters.
                      Not case sensitive (e.g. 'Monday', 'monday', 'mon').
                    ► Quarter end label (e.g. '2025Q1', '3Q25', 'Q4').
                    ► Any string format supported by pd.to_datetime().
        format : str | None
            if 'arg' is a string, this is argument is used to parse it
            (e.g. '%Y%m%d %H%S').
        offset : int
            If a day of the week is provided (e.g., 'Monday'), the current week
            is considered the reference point (offset = 0). Other offsets shift
            the result relative to this reference. For example, if arg='Monday'
            and offset=-1, the result will be the Monday of the previous week.
            In the case of quarter end labels, see the subclass documentation.

        Returns
        ------------
        dt : datetime.datetime
            Timestamp or subclass instance
        '''

        def try_weekday(arg, weeks):
            ''' check if arg is a weekday label '''
            weekday = cls.get_weekday_index(arg)
            if weekday is None: return
            now = datetime.datetime.now()
            days = weekday - now.weekday()
            dt = now + datetime.timedelta(days=days, weeks=weeks)
            return cls._normalize(dt)


        def try_quarter_end(arg, offset):
            ''' check if arg is a quarter end label '''
            qe_cls = cls._get_quarter_end_cls()
            parsed = qe_cls.parse_label(arg)
            if parsed is None: return
            year, quarter = parsed
            qe = qe_cls(year=year, quarter=quarter, offset=offset)
            return qe.dt


        if arg is None:
            return datetime.datetime.now()

        if pd.isna(arg):
            raise NotImplementedError

        if isinstance(arg, str):
            if format is not None:
                return datetime.datetime.strptime(arg, format)

            offset = cls._try_int(offset)
            for func in (try_weekday, try_quarter_end):
                result = func(arg, offset)
                if result is not None:
                    return result

            return parse(arg)

        # Timestamp instance (or subclass)
        if isinstance(arg, Timestamp):
            return arg.dt

        # pandas object
        if hasattr(arg, 'to_pydatetime'):
            return arg.to_pydatetime()

        if isinstance(arg, datetime.datetime):
            return arg

        if isinstance(arg, datetime.date):
            return cls._normalize(arg)

        # timestamp expressed in seconds
        if isinstance(arg, (float, int)):
            # local time zone by default
            return datetime.datetime.fromtimestamp(arg)

            # UTC by default
            # return pd.to_datetime(arg, unit='s').to_pydatetime()

        raise TypeError(
            f"'arg' of type <{type(arg).__name__}> "
            f"is not supported: {arg!r}."
            )