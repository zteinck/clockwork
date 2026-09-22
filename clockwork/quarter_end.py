import datetime
import re

from oddments import Validator, UNSET
import polars as pl

from .month_end import MonthEnd
from .constants import MONTHS_IN_YEAR


class QuarterEnd(MonthEnd):
    '''
    Description
    --------------------
    Quarter end date.

    Class Attributes
    --------------------
    _scheme : tuple
        Quarter end months.

    Instance Attributes
    --------------------
    None
    '''

    #╭-------------------------------------------------------------------------╮
    #| Class Attributes                                                        |
    #╰-------------------------------------------------------------------------╯

    _increment = 3
    _scheme = (3, 6, 9, 12)


    #╭-------------------------------------------------------------------------╮
    #| Initialize Instance                                                     |
    #╰-------------------------------------------------------------------------╯

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


    #╭-------------------------------------------------------------------------╮
    #| Properties                                                              |
    #╰-------------------------------------------------------------------------╯

    @property
    def scheme(self):
        return self._scheme


    @property
    def long_label(self):
        return f'{self.year}Q{self.quarter}'


    @property
    def compact_label(self):
        return f'{self.quarter}Q' + self.to_string('%y')


    @property
    def short_label(self):
        return f'Q{self.quarter}'


    @property
    def quarter(self):
        ''' the quarter number (1 to 4) '''
        return int(self.scheme.index(self.month) + 1)


    #╭-------------------------------------------------------------------------╮
    #| Instance Methods                                                        |
    #╰-------------------------------------------------------------------------╯

    def _init_dt(
        self,
        source,
        target_tz,
        year=None,
        month=None,
        quarter=None,
        **kwargs
        ):
        '''
        Parameters
        ------------
        source : None | any
            A value representing a quarter end date. Must be None if 'year',
            'month', or 'quarter' are provided.
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
            forward in time and negative values to move backward in time.
        kwargs : dict
            Additional keyword arguments forwarded to the Timestamp
            constructor.
        '''

        parsed_label = self._parse_label(source, target_tz)

        if parsed_label is not None:
            for k, v in {
                'year': year,
                'month': month,
                'quarter': quarter,
                }.items():
                if v is not None:
                    raise ValueError(
                        f"{k!r} must be None when 'source' is a quarter end "
                        f"label: {source!r}."
                        )

            year, quarter = parsed_label
            source = None

        has_quarter = quarter is not None

        if month is not None:
            if has_quarter:
                raise ValueError(
                    "Cannot pass 'quarter' and 'month' arguments "
                    "simultaneously."
                    )

            month = self._ensure_int(month)

            # validate month
            (
            Validator(
                types=int,
                whitelist=self.scheme,
                )
            .validate(
                month=month
                )
            )

        if has_quarter:
            quarter = self._ensure_int(
                value=quarter,
                name='quarter',
                )
            month = self.scheme[quarter - 1]

        super()._init_dt(
            source=source,
            target_tz=target_tz,
            year=year,
            month=month,
            **kwargs
            )


    def _offset(self, year, month, offset):
        year, month = self._backtrack_to_scheme(
            year=year,
            month=month,
            )

        result = super()._offset(
            year=year,
            month=month,
            offset=offset,
            )

        return result


    def _find_error(self):
        if self.month not in self.scheme:
            return f'the month ({self.month}) is not in scheme: {self.scheme}'
        return super()._find_error()


    #╭-------------------------------------------------------------------------╮
    #| Class Methods                                                           |
    #╰-------------------------------------------------------------------------╯

    @classmethod
    def set_scheme(cls, value):
        ''' safely sets 'scheme' class attribute '''

        name = 'scheme'

        Validator(types=tuple).validate(value, name)

        if len(value) != 4:
            raise ValueError(
                f"'scheme' must contain 4 elements, got: {len(value):,}"
                )

        value = tuple(map(cls._ensure_int, value))
        s = pl.Series(name=name, values=value)

        valid_increments = (
            s.diff(null_behavior='drop') == 3
            ).all()

        if not valid_increments:
            raise ValueError(
                "'scheme' must be ascending in increments of 3, got: "
                f"{value!r}"
                )

        valid_months = s.is_between(
            lower_bound=1,
            upper_bound=MONTHS_IN_YEAR,
            closed='both'
            ).all()

        if not valid_months:
            raise ValueError(
                f"'scheme' values must be between 1 and {MONTHS_IN_YEAR}, "
                f"got: {value!r}."
                )

        cls._scheme = value


    @classmethod
    def _backtrack_to_scheme(cls, year, month):
        ''' Backtracks from the given year and month, moving one month at a
            time, until a month that is part of the scheme is found. '''

        while month not in cls._scheme:
            year, month = cls._get_prior_month(
                year=year,
                month=month,
                )

        return year, month


    @classmethod
    def _parse_label(cls, source, target_tz):
        '''
        Description
        ------------
        Parses a quarter end label into its year and quarter components.
        Supports input patterns like YYYYQ#, #QYY, and Q#. When the year
        is not provided in the label, the current year is used by default.

        Parameters
        ------------
        source : str
            Quarter end label to parse.
        target_tz : str | datetime.timezone
            Refer to '_resolve_dt()' documentation.

        Returns
        ------------
        Returns None if input is not a string or parsing failed.
        Otherwise:

        result : tuple
            year : int
                The four-digit year.
            quarter : int
                The quarter number (1 to 4).
        '''

        def extract_year_and_quarter(value):
            if not isinstance(value, str):
                return None

            value = value.strip().upper()

            # 'YYYYQ#' | 'YYYY Q#'
            match = re.fullmatch(r'(\d{4})\s?Q(\d)', value)

            if match:
                return match.groups()

            tz = None if target_tz is UNSET else target_tz
            now = datetime.datetime.now(tz=tz)

            # '#QYY'
            match = re.fullmatch(r'(\d)Q(\d{2})', value)

            if match:
                quarter, year = match.groups()
                return f'{now.year // 100}{year}', quarter

            # 'Q#'
            match = re.fullmatch(r'Q(\d)', value)

            if match:
                quarter = match.group(1)
                return f'{now.year}', quarter


        parsed = extract_year_and_quarter(source)

        if parsed is None:
            return None

        year, quarter = (cls._ensure_int(x) for x in parsed)

        if not (1 <= quarter <= 4):
            raise ValueError(
                f"Quarter must be between 1 and 4, got: {quarter}"
                )

        return year, quarter