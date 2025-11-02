
import datetime
import oddments as odd

from .timestamp import Timestamp
from .constants import MONTHS_IN_YEAR


class MonthEnd(Timestamp):
    '''
    Description
    --------------------
    Month end timestamp object.

    Class Attributes
    --------------------
    _increment : int
        Number of months to increment during offsets.

    Instance Attributes
    --------------------
    ...
    '''

    #╭-------------------------------------------------------------------------╮
    #| Class Attributes                                                        |
    #╰-------------------------------------------------------------------------╯

    _increment = 1


    #╭-------------------------------------------------------------------------╮
    #| Initialize Instance                                                     |
    #╰-------------------------------------------------------------------------╯

    def __init__(self, arg=None, **kwargs):
        '''
        Parameters
        ------------
        arg : None | any
            A scalar value to be interpreted as a month end date. Must be None
            if 'year' or 'month' are provided. Refer to '_to_datetime()' for
            supported input formats.
        year : int
            The calendar year of the month end date.
        month : int
            The calendar month of the month end date (1 to 12).
        offset : int
            Number of months to shift from the base month end. Base month end
            defaults to the most recently completed month end when no other
            parameters are provided. Use positive values to move forward and
            negative values to move backward in time.
        kwargs : dict
            Additional keyword arguments are forwarded to the Timestamp
            constructor. Refer to its documentation for details.
        '''
        offset = self._try_int(kwargs.pop('offset', 0))
        year, month = [kwargs.pop(k, None) for k in ['year','month']]
        year_or_month = not (year is None and month is None)
        has_arg = arg is not None

        if has_arg:
            if year_or_month:
                raise ValueError(
                    "Both 'year' and 'month' must be "
                    "None when 'arg' is not None."
                    )
        else:
            if year_or_month:
                year, month = map(self._try_int, (year, month))
                self._validate_month(month)
            else:
                now = datetime.datetime.now()
                year = now.year
                month = now.month - 1 # default to last month

            year, month = self._offset(
                year=year,
                month=month,
                offset=offset * self._increment
                )

            day = self.days_in_month(year, month)
            arg = datetime.datetime(year, month, day)

        super().__init__(arg, **kwargs)
        self.validate_instance()

        if has_arg and offset != 0:
            self.offset(periods=offset, inplace=True)


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
        a, b = [
            self._total_months(obj.year, obj.month)
            for obj in (self, self.__class__(offset=0))
            ]
        q, r = divmod(a - b, self._increment)
        if r == 0: return int(q)
        raise ValueError(f"Unexpected remainder: {r}")


    #╭-------------------------------------------------------------------------╮
    #| Instance Methods                                                        |
    #╰-------------------------------------------------------------------------╯

    def offset(self, periods, inplace=False):
        ''' offsets instance by desired number of periods '''
        odd.validate_value(
            value=periods,
            name='periods',
            types=int
            )

        out = self.__class__(offset=self.relative_offset + periods)

        if inplace:
            self.dt = out.dt
        else:
            return out


    def _offset(self, year, month, offset):
        total_months = self._total_months(year, month + offset)
        y, m = divmod(total_months, MONTHS_IN_YEAR)
        return (y - 1, MONTHS_IN_YEAR) if m == 0 else (y, m)


    def validate_instance(self):
        ''' raises an error if the instance fails validation '''
        error_msg = self._validate_instance()

        if error_msg is not None:
            raise ValueError(
                f"Failed to initialize a {self.__class__.__name__} "
                f"instance because the {error_msg}. "
                )


    def _validate_instance(self):
        if not self.is_last_day_of_month:
            return (
                f"day ({self.day}) is not the last day "
                f"({self.last_day_of_month}) of {self.month_name} {self.year}"
                )

        if not self.is_normalized:
            return (
                "date must have no time component. Use "
                "'normalize=True' when creating the date"
                )