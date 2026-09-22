import datetime
import calendar
from copy import deepcopy

import holidays as hd
import pandas as pd
import numpy as np
from oddments import Validator, UNSET
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse

from ..constants import MONTHS_IN_YEAR
from ._decorators import *


class Timestamp:
    '''
    Description
    --------------------
    A thin wrapper around 'datetime.datetime' that provides a convenient
    interface for manipulating date and/or time values.

    Class Attributes
    --------------------
    repr_format : str
        String of datetime format codes used to render the object's string
        representation.
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

    repr_format = '%Y-%m-%d %I:%M:%S.%f %p'
    business_hours = (8, 17) # 8am - 5pm
    weekday_map = None
    holiday_calendar = None

    _month_end_cls = None
    _quarter_end_cls = None


    #╭-------------------------------------------------------------------------╮
    #| Initialize Instance                                                     |
    #╰-------------------------------------------------------------------------╯

    def __init__(
        self,
        source=None,
        *,
        source_format=None,
        source_tz=UNSET,
        target_tz=UNSET,
        offset=0,
        **kwargs
        ):

        # validate source format
        (
        Validator(
            types=str,
            allow_none=True,
            )
        .validate(
            source_format=source_format
            )
        )

        # resolve source & target time zones
        source_tz, target_tz = (
            self._resolve_time_zone(v, k)
            for k, v in {
                'source_tz': source_tz,
                'target_tz': target_tz,
                }.items()
            )

        # normalize offset
        offset = self._ensure_int(
            value=offset,
            name='offset',
            )

        # initialize datetime
        self._init_dt(
            source=source,
            source_format=source_format,
            source_tz=source_tz,
            target_tz=target_tz,
            offset=offset,
            **kwargs
            )


    #╭-------------------------------------------------------------------------╮
    #| Properties                                                              |
    #╰-------------------------------------------------------------------------╯

    @property
    def dt(self):
        ''' the underlying datetime.datetime instance '''
        return self._dt


    @property
    def datetime(self):
        ''' alias for 'dt' '''
        return self.dt


    @property
    def date(self):
        return self.to_date()


    @property
    def d(self):
        return self.to_date()


    @property
    def time_zone(self):
        return self.dt.tzinfo


    @property
    def tz(self):
        ''' alias for 'time_zone' '''
        return self.time_zone


    @property
    def ymd(self):
        ''' Date string in ISO 8601 format (i.e. YYYY-MM-DD) '''
        return self.to_string('%Y-%m-%d')


    @property
    def timestamp(self):
        return self.to_timestamp()


    @property
    def time(self):
        return self.to_time()


    @property
    def month_name(self):
        ''' full name of the month (e.g. 'May') '''
        return self.to_string('%B')


    @property
    def yesterday(self):
        ''' the date one day earlier '''
        return self.shift(days=-1)


    @property
    def tomorrow(self):
        ''' the date one day later '''
        return self.shift(days=+1)


    @property
    def month_start(self):
        ''' the date shifted to the first of the month '''
        return self.replace(day=1)


    @property
    def month_end(self):
        ''' returns the last day of the month as a MonthEnd object '''
        return self.to_month_end(strict=False)


    @property
    def is_month_end(self):
        ''' returns True if the date aligns with a month end date '''
        return self.is_last_day_of_month


    @property
    def is_quarter_end(self):
        ''' returns True if the date aligns with a quarter end date '''
        scheme = set(self._get_quarter_end_cls()._scheme)
        return self.is_month_end and self.month in scheme


    @property
    def weekday_name(self):
        ''' full weekday name (e.g. 'Monday') '''
        return self.to_string('%A')


    @property
    def weekday_abbr(self):
        ''' abbreviated weekday name (e.g. 'Mon') '''
        return self.to_string('%a')


    @property
    def weekday_index(self):
        ''' weekday index (e.g. 0) '''
        return self.dt.weekday()


    @property
    def is_weekend(self):
        ''' returns True if the date falls on the weekend '''
        return self.weekday_name in {'Saturday','Sunday'}


    @property
    def is_holiday(self):
        ''' returns True if the date is a U.S. holiday '''
        return self.holiday_name is not None


    @property
    def is_non_business_day(self):
        ''' returns True if the date is a not a business day '''
        return self.is_weekend or self.is_holiday


    @property
    def is_business_day(self):
        ''' returns True if the date is a business day '''
        return not self.is_non_business_day


    @property
    def is_business_hours(self):
        ''' returns True if the date is within business hours '''
        if not self.is_business_day:
            return False

        since, until = (
            datetime.datetime(
                year=self.year,
                month=self.month,
                day=self.day,
                hour=hour,
                tzinfo=self.tz,
                )
            for hour in self.business_hours
            )

        return since <= self.dt <= until


    @property
    def is_today(self):
        ''' returns True if date is the current day '''
        today = datetime.datetime.now(tz=self.tz).date()
        return self.date == today


    @property
    def is_normalized(self):
        ''' returns True if date has no time component (i.e. 00:00:00) '''
        return self.time == datetime.time.min


    @property
    def last_day_of_month(self):
        ''' returns the last day of the month '''
        return self.days_in_month(year=self.year, month=self.month)


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
        month_end_cls = self._get_month_end_cls()
        year, month = self.year, self.month

        if not self.is_month_end:
            year, month = self._get_prior_month(
                year=year,
                month=month,
                )

        month_end = month_end_cls(
            year=year,
            month=month,
            target_tz=self.tz,
            )

        return month_end


    @property
    def last_quarter_end(self):
        ''' returns most recent quarter end relative to self '''
        quarter_end_cls = self._get_quarter_end_cls()
        year, month = self.year, self.month

        if not self.is_quarter_end:
            year, month = quarter_end_cls._backtrack_to_scheme(
                year=self.year,
                month=self.month,
                )

        quarter_end = quarter_end_cls(
            year=year,
            month=month,
            target_tz=self.tz,
            )

        return quarter_end


    #╭-------------------------------------------------------------------------╮
    #| Magic Methods                                                           |
    #╰-------------------------------------------------------------------------╯

    def __hash__(self):
        return hash(self.dt)


    def __getattr__(self, name):
        return getattr(self.dt, name)


    def __copy__(self):
        return self.clone()


    def __deepcopy__(self, memo):
        return self.clone()


    def __repr__(self):
        return '{0}(dt={1}, tz={2})'.format(
            self.__class__.__name__,
            self.to_string(self.repr_format),
            self.time_zone,
            )


    def __str__(self):
        return repr(self)


    def __float__(self):
        return self.to_timestamp()


    def __int__(self):
        return int(float(self))


    @other_to_dt
    def __eq__(self, other):
        return self.dt == other


    @other_to_dt
    def __ne__(self, other):
        return self.dt != other


    @other_to_dt
    def __lt__(self, other):
        return self.dt < other


    @other_to_dt
    def __gt__(self, other):
        return self.dt > other


    @other_to_dt
    def __le__(self, other):
        return self.dt <= other


    @other_to_dt
    def __ge__(self, other):
        return self.dt >= other


    @other_to_delta
    def __add__(self, other):
        return self.dt + other


    @other_to_delta
    def __sub__(self, other):
        return self.dt - other


    #╭-------------------------------------------------------------------------╮
    #| Instance Methods                                                        |
    #╰-------------------------------------------------------------------------╯

    def shift(self, *, biz_days=None, **kwargs):
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

        obj = (
            self._shift(**kwargs)
            if kwargs
            else self.clone()
            )

        if biz_days is None or biz_days == 0:
            return obj

        delta = int(np.sign(biz_days))
        counter = 0

        while counter < abs(biz_days):
            obj = obj._shift(days=delta)
            if obj.is_business_day:
                counter += 1

        return obj


    @handle_next_last
    def next(x):
        ''' see decorator for documentation '''
        return +1 if x >= 0 else 0


    @handle_next_last
    def last(x):
        ''' see decorator for documentation '''
        return -1 if x <= 0 else 0


    @to_period_end
    def to_month_end():
        pass


    @to_period_end
    def to_quarter_end():
        pass


    def with_time_zone(self, tz):
        tz = self._resolve_time_zone(value=tz, name='tz')
        return self.replace(tzinfo=tz)


    def to_time_zone(self, tz):
        dt = self.to_datetime()
        dt = self._to_time_zone(dt, tz)
        return self._spawn(dt)


    def to_utc(self):
        return self.to_time_zone('utc')


    def to_naive(self):
        return self.to_time_zone(None)


    def clone(self):
        ''' returns a deep copy of self '''
        return self._spawn(self)


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
        return self.dt.timestamp()


    def to_date(self):
        ''' return the date component as a 'datetime.date' object '''
        return self.dt.date()


    def to_time(self):
        ''' returns the time component as a 'datetime.time' object '''
        return self.dt.time()


    def to_string(self, format):
        ''' strftime alias '''
        return self.strftime(format)


    def to_iso_string(self, *, include_time=True):
        obj = self.dt if include_time else self.d
        return obj.isoformat()


    @skip_shift
    def skip_holidays():
        ''' returns the nearest non-holiday date by skipping holidays in the
            specified direction '''
        pass


    @skip_shift
    def skip_weekends():
        ''' returns the nearest non-weekend date by skipping weekends in the
            specified direction '''
        pass


    @skip_shift
    def skip_non_business_days():
        ''' returns the nearest business day date by skipping non-business
            days in the specified direction '''
        pass


    def normalize(self):
        dt = self.to_datetime()
        normalized_dt = self._normalize(dt)
        return self._spawn(normalized_dt)


    def replace(self, **kwargs):
        dt = self.to_datetime().replace(**kwargs)
        return self._spawn(dt)


    def _spawn(self, *args, **kwargs):
        return type(self)(*args, **kwargs)


    def _build_delta(self, value):
        ''' constructs a time delta object from keyword arguments '''

        kwargs = (
            value.copy()
            if isinstance(value, dict)
            else dict(days=value)
            )

        relative = kwargs.pop('relative', False)

        if not kwargs:
            raise AssertionError(
                'kwargs cannot be empty.'
                )

        delta_cls = (
            relativedelta
            if relative
            else datetime.timedelta
            )

        delta = delta_cls(**kwargs)
        return delta


    def _shift(self, **kwargs):
        delta = self._build_delta(kwargs)
        result = self._make_base(self.dt + delta)
        return result


    def _to_time_zone(self, dt, tz):
        tz = self._resolve_time_zone(value=tz, name='tz')
        dt = dt.astimezone(tz)
        if tz is None:
            dt = dt.replace(tzinfo=None)
        return dt


    def _init_dt(self, **kwargs):
        self._dt = self._resolve_dt(**kwargs)


    def _resolve_dt(
        self,
        source,
        source_format,
        source_tz,
        target_tz,
        offset,
        ):
        '''
        Description
        ------------
        Converts a scalar to datetime.datetime instance.

        Parameters
        ------------
        source : None | any
            Value to convert to datetime. Supported formats include:
                • None → returns the current datetime (i.e. now)
                • pd.Timestamp
                • cw.Timestamp or subclass
                • datetime.datetime
                • datetime.date
                • int or float (expressed in seconds)
                • str
                    ► Day of the week, either fully spelled out or abbreviated
                      to the first three letters. Case-insensitive (e.g.
                      'Monday', 'monday', 'MON').
                    ► Quarter end label (e.g. '2025 Q1', '3Q25', 'Q4').
                    ► A string, accompanied by a 'source_format' string
                      describing how to parse it.
                    ► Any string parsable by 'dateutil.parser.parse()'
        source_format : str | None
            Datetime format code(s) used to parse 'source' when it is a string
            (e.g. '%Y%m%d %H%M%S').
        source_tz : UNSET | None | str | datetime.timezone
            Source time zone.
        target_tz : UNSET | None | str | datetime.timezone
            Desired time zone.
        offset : int
            If a day of the week is provided (e.g., 'Monday'), the current week
            is considered the reference point (offset = 0). Other offsets shift
            the result relative to this reference. For example, if value='Monday'
            and offset=-1, the result will be the Monday of the previous week.
            In the case of quarter end labels, see the subclass documentation.

        Returns
        ------------
        dt : datetime.datetime
            datetime.datetime instance.
        '''

        def try_weekday(source, offset):
            ''' check if value is a weekday label '''
            weekday = self.get_weekday_index(source)

            if weekday is None:
                return None

            if source_tz is not UNSET:
                raise ValueError(
                    "'source_tz' is not applicable when 'source' is a "
                    "weekday name."
                    )

            now = datetime.datetime.now(tz=_target_tz)
            days = weekday - now.weekday()
            dt = now + datetime.timedelta(days=days, weeks=offset)
            dt = self._normalize(dt)
            return dt


        def try_quarter_end(source, offset):
            ''' check if value is a quarter end label '''
            cls = self._get_quarter_end_cls()
            parsed = cls._parse_label(source, target_tz)

            if parsed is None:
                return None

            if source_tz is not UNSET:
                raise ValueError(
                    "'source_tz' is not applicable when 'source' is a "
                    "quarter end label."
                    )

            year, quarter = parsed

            qe = cls(
                year=year,
                quarter=quarter,
                offset=offset,
                target_tz=target_tz,
                )

            dt = qe.to_datetime()
            return dt


        def ensure_parsed_tz(dt):
            if source_tz is not UNSET and source_tz != dt.tzinfo:
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=source_tz)
                else:
                    raise ValueError(
                        f"Time zone parsed from string ({dt.tzinfo}) does "
                        f"not align with 'source_tz' ({source_tz})."
                        )

            if target_tz is not UNSET and target_tz != dt.tzinfo:
                dt = self._to_time_zone(dt=dt, tz=target_tz)

            return dt


        _source_tz, _target_tz = (
            (None if tz is UNSET else tz)
            for tz in (source_tz, target_tz)
            )


        if source is None:
            dt = datetime.datetime.now(tz=_target_tz)
            return dt

        if isinstance(source, str):

            if source_format is not None:
                dt = datetime.datetime.strptime(source, source_format)
                dt = ensure_parsed_tz(dt)
                return dt

            for func in (try_weekday, try_quarter_end):
                dt = func(source, offset)
                if dt is not None:
                    return dt

            dt = ensure_parsed_tz(parse(source))
            return dt

        if source_format is not None:
            raise ValueError(
                "'source_format' must be None when 'source' is not a string."
                )

        dt = None

        if type(source) is datetime.datetime:
            dt = source

        elif type(source) is datetime.date:
            dt = datetime.datetime.combine(
                date=source,
                time=datetime.time.min,
                tzinfo=_source_tz,
                )

        elif isinstance(source, Timestamp):
            dt = source.to_datetime()

        elif hasattr(source, 'to_pydatetime'):
            dt = source.to_pydatetime()

        if dt is not None:
            (
            Validator(
                whitelist=[datetime.datetime]
                )
            .validate(
                type(dt),
                f"'dt' type",
                )
            )

            if source_tz is not UNSET and source_tz != dt.tzinfo:
                raise ValueError(
                    f"The resolved datetime's Time zone ({dt.tzinfo}) does "
                    f"not align with 'source_tz' ({source_tz})."
                    )

            if target_tz is not UNSET and target_tz != dt.tzinfo:
                dt = self._to_time_zone(dt=dt, tz=target_tz)

            return dt


        # timestamp expressed in seconds
        elif isinstance(source, (float, int)):
            if not (
                source_tz is UNSET
                or source_tz == datetime.timezone.utc
                ):
                raise ValueError(
                    "'source_tz' must be UNSET or UTC when 'source' is a "
                    f"timestamp, got: {source_tz!r}"
                    )

            dt = datetime.datetime.fromtimestamp(
                timestamp=source,
                tz=_target_tz,
                )

            return dt

        else:
            raise TypeError(
                f"'source' argument is not supported <{type(source).__name__}>: "
                f"{source!r}"
                )


    #╭-------------------------------------------------------------------------╮
    #| Static Methods                                                          |
    #╰-------------------------------------------------------------------------╯

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
        result : int
            Number of days.
        '''
        return calendar.monthrange(year, month)[1]


    @staticmethod
    def _make_base(*args, **kwargs):
        return Timestamp(*args, **kwargs)


    @staticmethod
    def _normalize(value):
        ''' Sets the time component to zero (midnight) '''
        return value.replace(hour=0, minute=0, second=0, microsecond=0)


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
    def _ensure_int(value, name=None):
        Validator(types=(int, str)).validate(value, name)

        if isinstance(value, str):
            if value.isdigit():
                return int(value)
            raise TypeError(
                f"Failed to convert 'value' to integer: {value!r}"
                )

        return value


    @staticmethod
    def _resolve_time_zone(value, name):

        cls = datetime.timezone

        (
        Validator(
            types=(str, cls),
            allow_none=True,
            allow_unset=True,
            )
        .validate(value, name)
        )

        if value in (UNSET, None):
            return value

        if isinstance(value, str):
            if value.lower() == 'utc':
                return cls.utc
            else:
                raise ValueError(
                    f'Unsupported string value for {name!r}: {value!r}.'
                    )

        if isinstance(value, cls):
            return value

        raise AssertionError


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
            result = {k: i for i, k in enumerate(calendar.day_name)}
            result.update({k[:3]: v for k, v in result.items()})
            cls.weekday_map = result

        return cls.weekday_map


    @classmethod
    def get_weekday_index(cls, weekday):
        return cls._get_weekday_map().get(weekday.title())


    @classmethod
    def _get_month_end_cls(cls):
        if cls._month_end_cls is None:
            from ..month_end import MonthEnd
            cls._month_end_cls = MonthEnd
        return cls._month_end_cls


    @classmethod
    def _get_quarter_end_cls(cls):
        if cls._quarter_end_cls is None:
            from ..quarter_end import QuarterEnd
            cls._quarter_end_cls = QuarterEnd
        return cls._quarter_end_cls