import oddments as odd
import pandas as pd
import datetime
import re

from .month_end import MonthEnd
from .constants import MONTHS_IN_YEAR


class QuarterEnd(MonthEnd):
    '''
    Description
    --------------------
    Quarter end timestamp object.

    Class Attributes
    --------------------
    scheme : tuple
        Quarter end months.

    Instance Attributes
    --------------------
    ...
    '''

    #╭-------------------------------------------------------------------------╮
    #| Class Attributes                                                        |
    #╰-------------------------------------------------------------------------╯

    _increment = 3
    scheme = (3, 6, 9, 12)


    #╭-------------------------------------------------------------------------╮
    #| Initialize Instance                                                     |
    #╰-------------------------------------------------------------------------╯

    def __init__(self, arg=None, **kwargs):
        '''
        Parameters
        ------------
        arg : None | any
            A scalar value to be interpreted as a quarter end date. Must be
            None if 'year', 'month', or 'quarter' are provided. Refer to
            '_to_datetime()' for supported input formats.
        year : int
            The calendar year of the quarter end date.
        month : int
            The calendar month of the quarter end date (1 to 12).
        quarter : int
            The quarter number (1 to 4). Cannot be used together with the
            'month' argument.
        offset : int
            Number of quarters to shift from the base quarter end. Base
            quarter end defaults to the most recently completed quarter end
            when no other parameters are provided. Use positive values to move
            forward and negative values to move backward in time.
        kwargs : dict
            Additional keyword arguments are forwarded to the Timestamp
            constructor. Refer to its documentation for details.
        '''
        qtr = kwargs.pop('quarter', None)
        parsed = self.parse_label(arg)

        if parsed is not None:
            for k in ['year','quarter']:
                if kwargs.get(k) is not None:
                    raise ValueError(
                        f"'{k}' must be None when 'arg' "
                        "is a quarter label: {arg!r}."
                        )

            kwargs['year'], qtr = parsed
            arg = None

        if qtr is not None:
            if kwargs.get('month') is not None:
                raise ValueError(
                    "Cannot pass 'quarter' and 'month' "
                    "arguments simultaneously."
                    )
            qtr = self._try_int(qtr)
            kwargs['month'] = self.scheme[qtr - 1]

        super().__init__(arg, **kwargs)


    #╭-------------------------------------------------------------------------╮
    #| Properties                                                              |
    #╰-------------------------------------------------------------------------╯

    @property
    def long_label(self):
        return f'{self.year}Q{self.qtr}'


    @property
    def compact_label(self):
        return f'{self.qtr}Q' + self.to_string('%y')


    @property
    def short_label(self):
        return f'Q{self.qtr}'


    @property
    def quarter(self):
        ''' the quarter number (1 to 4) '''
        return int(self.scheme.index(self.month) + 1)


    @property
    def qtr(self):
        ''' quarter alias '''
        return self.quarter


    #╭-------------------------------------------------------------------------╮
    #| Instance Methods                                                        |
    #╰-------------------------------------------------------------------------╯

    def _offset(self, year, month, offset):
        year, month = self._backtrack_to_scheme(year, month)
        return super()._offset(year, month, offset)


    def _validate_instance(self):
        if self.month not in self.scheme:
            return f'month ({self.month}) is not in scheme: {self.scheme}'
        return super()._validate_instance()


    #╭-------------------------------------------------------------------------╮
    #| Class Methods                                                           |
    #╰-------------------------------------------------------------------------╯

    @classmethod
    def _backtrack_to_scheme(cls, year, month):
        ''' Backtracks from the given year and month, moving one month at a
            time, until a month that is part of the scheme is found. '''
        while month not in cls.scheme:
            year, month = cls._get_prior_month(year, month)
        return year, month


    @classmethod
    def set_scheme(cls, value):
        ''' safely sets 'scheme' class attribute '''

        odd.validate_value(
            value=value,
            name='scheme',
            types=tuple
            )

        if len(value) != 4:
            raise ValueError(
                "'scheme' must contain 4 elements, "
                f"got: {len(value):,}"
                )

        value = tuple(map(cls._try_int, value))
        s = pd.Series(value)

        if not (s.diff().dropna() == 3).all():
            raise ValueError(
                "'scheme' must be ascending in "
                f"increments of 3. got: {value}."
                )

        if not s.between(
            left=1,
            right=MONTHS_IN_YEAR,
            inclusive='both'
            ).all():
            raise ValueError(
                "'scheme' values must be between 1 "
                f"and {MONTHS_IN_YEAR}, got: {value}."
                )

        cls.scheme = value


    @classmethod
    def parse_label(cls, x):
        '''
        Description
        ------------
        Parses a quarter end label into its year and quarter components.
        Supports input patterns like YYYYQ#, #QYY, and Q#. When the year
        is not provided in the label, the current year is used by default.

        Parameters
        ------------
        x : str
            Quarter end label to parse.

        Returns
        ------------
        Returns None if input is not a string or parsing failed.
        Otherwise:

        out : tuple
            year : int
                The four-digit year.
            qtr : int
                The quarter number (1 to 4).
        '''

        def extract_year_qtr(x):
            if not isinstance(x, str): return
            x = x.strip().upper()

            # YYYYQ#
            match = re.fullmatch(r'(\d{4})Q(\d)', x)
            if match: return match.groups()

            now = datetime.datetime.now()

            # #QYY
            match = re.fullmatch(r'(\d)Q(\d{2})', x)
            if match:
                qtr, yy = match.groups()
                return f'{now.year // 100}{yy}', qtr

            # Q#
            match = re.fullmatch(r'Q(\d)', x)
            if match:
                qtr = match.group(1)
                return str(now.year), qtr


        parsed = extract_year_qtr(x)
        if parsed is None: return
        year, qtr = map(cls._try_int, parsed)

        if not (1 <= qtr <= 4):
            raise ValueError(
                "Quarter must be between "
                f"1 and 4, got: {qtr}"
                )

        return year, qtr