from ._base import DateBase


class MonthEnd(DateBase):

    #╭-------------------------------------------------------------------------╮
    #| Initialize Instance                                                     |
    #╰-------------------------------------------------------------------------╯

    def __init__(self, dt):
        day = self.n_days_in_month(dt.year, dt.month)
        super().__init__(dt.replace(day=day))


    #╭-------------------------------------------------------------------------╮
    #| Properties                                                              |
    #╰-------------------------------------------------------------------------╯

    @property
    def long(self):
        return self.str('%Y-%m-%d')


    @property
    def compact(self):
        return self.str('%Y-%m')


    @property
    def short(self):
        return self.str('%b')


    @property
    def is_year_end(self):
        return self.month == 12


    @property
    def is_quarter_end(self):
        return self.month in {3, 6, 9, 12}


    @property
    def last_quarter_end(self):
        ''' returns most recent quarter end '''
        delta = 0
        while True:
            me = self.offset(delta=delta)
            if me.is_quarter_end:
                return me.to_quarter_end()
            delta -= 1


    #╭-------------------------------------------------------------------------╮
    #| Instance Methods                                                        |
    #╰-------------------------------------------------------------------------╯

    def to_quarter_end(self):
        from ._quarter_end import QuarterEnd
        if self.is_quarter_end:
            return QuarterEnd(self.dt)
        else:
            raise ValueError(
                "Month-end date does not align with a quarter-end "
                f"date: '{self.ymd}'"
                )


    def offset(self, delta):
        ''' returns the month end 'delta' months away from the instance '''
        if not isinstance(delta, int):
            raise TypeError("'delta' argument must be an integer")
        if delta == 0: return self
        dt = self.shift(months=delta).dt
        return self.__class__(dt)