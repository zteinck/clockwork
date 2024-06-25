from ._month_end import MonthEnd



class QuarterEnd(MonthEnd):

    #╭-------------------------------------------------------------------------╮
    #| Initialize Instance                                                     |
    #╰-------------------------------------------------------------------------╯

    def __init__(self, dt, qtr, *args, **kwargs):
        super().__init__(dt)
        self.qtr = qtr


    #╭-------------------------------------------------------------------------╮
    #| Properties                                                              |
    #╰-------------------------------------------------------------------------╯

    @property
    def long(self):
        return f'{self.year}Q{self.qtr}'

    @property
    def compact(self):
        return f'{self.qtr}Q' + self.str('%y')

    @property
    def short(self):
        return f'Q{self.qtr}'

    @property
    def quarter(self):
        return self.qtr


    #╭-------------------------------------------------------------------------╮
    #| Instance Methods                                                        |
    #╰-------------------------------------------------------------------------╯

    def to_month_end(self):
        return MonthEnd(self.dt)


    def offset(self, delta):
        ''' returns the quarter end 'delta' quarters away from the instance '''
        if not isinstance(delta, int):
            raise TypeError("'delta' argument must be an integer")
        if delta == 0: return self
        dt = self.shift(months=delta * 3).dt
        qtr = ((self.qtr - 1 + delta) % 4) + 1
        return self.__class__(dt, qtr)