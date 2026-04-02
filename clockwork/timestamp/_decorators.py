from functools import wraps

import oddments as odd


def enable_inplace(func):
    ''' Enables in-place updates '''

    @wraps(func)
    def wrapper(self, **kwargs):
        params = {**kwargs}
        inplace = params.pop('inplace', False)
        dt = func(self, **params)

        if inplace:
            self.dt = dt
        else:
            return self.__class__(dt)

    return wrapper


def other_to_dt(func):
    ''' Converts the 'other' argument to a datetime object for use in magic
        methods. '''

    @wraps(func)
    def wrapper(self, other):
        return func(self, self._to_datetime(other))

    return wrapper


def other_to_delta(func):
    ''' Converts the 'other' argument to a time delta object for use in magic
        methods. '''

    @wraps(func)
    def wrapper(self, other):
        # Subtracting a date-like 'other' returns a datetime.timedelta
        # object.
        if (
            func.__name__.replace('_', '') == 'sub'
            and not isinstance(other, (dict, float, int))
            ):
            return func(self, self._to_datetime(other))

        # Otherwise, 'other' is assumed to be a delta and the resulting
        # Timestamp object is returned.
        delta = self._build_delta(other)
        return self._make_base(func(self, delta))

    return wrapper


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


def handle_next_last(func):
    ''' Facilitates shifting based on specific weekdays '''

    def wrapper(self, arg, offset=0):
        '''
        Description
        ------------
        Returns an instance representing the next or last day of the week
        relative to self. For example self.next('Mon') would return the date
        of the following Monday. Also supports offsets for additional
        shifting.

        Parameters
        ------------
        arg : str
            Day of the week either fully spelled out or the first three
            characters (e.g. 'Friday' or 'Fri') not case-sensitive. Also
            supports period ends (e.g. 'QE', 'ME').
        offset : int
            Offset value +/- indicating how many additional weeks to shift.
            For example, self.next('Mon', offset=+1) would return the Monday
            two weeks from self.

        Returns
        ------------
        shifted : Timestamp
            Timestamp instance
        '''

        odd.validate_value(
            value=arg,
            name='arg',
            types=str
            )

        kind = func.__name__

        # try weekday
        target = self.get_weekday_index(arg)

        if target is not None:
            actual = self.weekday_index
            weeks = func(actual - target) + offset
            return (
                self
                .shift(days=-actual)
                .shift(days=target, weeks=weeks)
                )

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
            If True, an exception is raised if self does not already align
                with a period end date.
            If False, self will be coerced to a period end date.

        Returns
        ------------
        period_end : MonthEnd | QuarterEnd
            Period end instance.
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
        period_end = pe_cls(year=self.year, month=self.month)
        return period_end

    return wrapper