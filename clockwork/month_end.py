import datetime

from oddments import Validator, UNSET

from .timestamp import Timestamp
from .constants import MONTHS_IN_YEAR


class MonthEnd(Timestamp):
    '''
    Description
    --------------------
    Month end date.

    Class Attributes
    --------------------
    _increment : int
        Number of months to increment during offsets.

    Instance Attributes
    --------------------
    None
    '''

    #╭-------------------------------------------------------------------------╮
    #| Class Attributes                                                        |
    #╰-------------------------------------------------------------------------╯

    repr_format = '%Y-%m-%d'
    _increment = 1


    #╭-------------------------------------------------------------------------╮
    #| Initialize Instance                                                     |
    #╰-------------------------------------------------------------------------╯

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


    #╭-------------------------------------------------------------------------╮
    #| Properties                                                              |
    #╰-------------------------------------------------------------------------╯

    @property
    def long_label(self):
        return self.to_string('%Y-%m-%d')


    @property
    def compact_label(self):
        return self.to_string('%Y-%m')


    @property
    def short_label(self):
        return self.to_string('%b')


    @property
    def is_year_end(self):
        return self.month == MONTHS_IN_YEAR


    @property
    def relative_offset(self):
        return self._compute_relative_offset()


    #╭-------------------------------------------------------------------------╮
    #| Instance Methods                                                        |
    #╰-------------------------------------------------------------------------╯

    def offset(self, periods):
        ''' offsets instance by desired number of periods '''
        Validator(types=int).validate(periods=periods)
        offset = self.relative_offset + periods
        result = self._spawn(offset=offset, target_tz=self.tz)
        return result


    def _offset(self, year, month, offset):
        total_months = self._total_months(
            years=year,
            months=(month + offset),
            )

        y, m = divmod(total_months, MONTHS_IN_YEAR)

        if m == 0:
            return y - 1, MONTHS_IN_YEAR

        return y, m


    def _compute_relative_offset(self):
        '''
        Description
        ------------
        Returns the number of periods the instance is offset relative to
        the most recent period end. Periods are defined by the '_increment'
        class attribute.

        Returns
        ------------
        q : int
            Number of offset periods.
        '''
        a, b = (
            self._total_months(
                years=obj.year,
                months=obj.month,
                )
            for obj in (
                self,
                self._spawn(
                    offset=0,
                    target_tz=self.tz,
                    )
                )
            )

        q, r = divmod(a - b, self._increment)

        if r != 0:
            raise AssertionError(
                f'Unexpected remainder: {r}'
                )

        return int(q)


    def _validate(self):
        ''' raises an error if the instance fails validation '''
        msg = self._find_error()

        if msg is not None:
            raise ValueError(
                f'{self.__class__.__name__} instance is invalid because {msg}'
                )


    def _find_error(self):
        if not self.is_last_day_of_month:
            return (
                f'{self.day} is not the last day ({self.last_day_of_month}) '
                f'of {self.month_name} {self.year}'
                )

        if not self.is_normalized:
            return (
                'the time component must be normalized (i.e. all zoroes), '
                f'got: {self.time}'
                )


    def _init_dt(
        self,
        source,
        target_tz,
        offset,
        year=None,
        month=None,
        **kwargs
        ):
        '''
        Parameters
        ------------
        source : None | any
            A value representing a month end date. Must be None if 'year' or
            'month' arguments are provided.
        year : int
            The calendar year of the month end date.
        month : int
            The calendar month of the month end date (1 to 12).
        offset : int
            Number of months to shift from the base month end. Base month end
            defaults to the most recently completed month end when no other
            parameters are provided. Use positive values to move forward in
            time and negative values to move backward in time.
        kwargs : dict
            Additional keyword arguments are forwarded to the Timestamp
            constructor.
        '''

        has_source = source is not None
        has_year_or_month = year is not None or month is not None

        if has_source:
            if has_year_or_month:
                raise ValueError(
                    "Both 'year' and 'month' must be None when 'source' is "
                    "not None."
                    )

            self._dt = self._resolve_dt(
                source=source,
                target_tz=target_tz,
                offset=offset,
                **kwargs
                )

            if offset != 0:
                self._dt = self.offset(periods=offset).to_datetime()

        else:
            _target_tz = None if target_tz is UNSET else target_tz

            if has_year_or_month:
                year, month = (
                    self._ensure_int(value=v, name=k)
                    for k, v in {
                        'year': year,
                        'month': month,
                        }.items()
                    )
                self._validate_month(month)

            else:
                now = datetime.datetime.now(tz=_target_tz)

                year, month = self._get_prior_month(
                    year=now.year,
                    month=now.month,
                    )

            year, month = self._offset(
                year=year,
                month=month,
                offset=(offset * self._increment),
                )

            day = self.days_in_month(year, month)

            self._dt = datetime.datetime(
                year=year,
                month=month,
                day=day,
                tzinfo=_target_tz,
                )

        self._dt = self._normalize(self._dt)
        self._validate()