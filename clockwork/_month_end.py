from ._base import DateBase



class MonthEnd(DateBase):

    #╭-------------------------------------------------------------------------╮
    #| Initialize Instance                                                     |
    #╰-------------------------------------------------------------------------╯

    def __init__(self, dt):
        super().__init__(dt.replace(day=self.n_days_in_month(dt.year, dt.month)))


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
    def last_quarter_end(self):
        ''' returns most recent quarter end '''
        delta = 0
        while True:
            obj = self.offset(delta=delta)
            if hasattr(obj, 'quarter'): return obj
            delta -= 1


    #╭-------------------------------------------------------------------------╮
    #| Instance Methods                                                        |
    #╰-------------------------------------------------------------------------╯

    def offset(self, delta):
        ''' returns the month end 'delta' months away from the instance '''
        if not isinstance(delta, int):
            raise TypeError("'delta' argument must be an integer")
        if delta == 0: return self
        dt = self.shift(months=delta).dt
        return self.__class__(dt)