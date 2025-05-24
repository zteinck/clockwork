import time
import os
from contextlib import redirect_stdout
from schedule import CancelJob

from ..timestamp import Timestamp
from ..utils import elapsed_time
from .utils import PrerequisiteError, ContinueFailedJob


class Task(object):
    '''
    Description
    --------------------
    job object designed to be used in conjunction with TaskScheduler as the
    'job' argument in self._run_job()

    Class Attributes
    --------------------
    manager : TaskMaster
        TaskMaster object
    verbose : bool
        If True, class content is printed to console.
    disable_print : bool
        If True, printing is suppressed while func runs. Must be True if verbose
        is True.
    cascade_status : str
        cascade status

    Instance Attributes
    --------------------
    name : str
        name of job
    at : str
        at time string
    expiry : Timestamp
        If not None, job will be set inactive and stop running after this
        datetime
    func : func
        function to run
    args : tuple
        func arguments
    kwargs : dict
        func key word arguments
    cancel_on_failure : bool
        If True, the job will be cancelled if it raises an exception.
    cancel_on_completion : bool
        If True, the job will be cancelled if it completed successfully
        (i.e. job will run only once).
    notify_on_failure : bool
        If True, an email notification is sent to my inbox that includes the
        traceback. cancel_on_failure and cascade are automatically set to True
        if this argument is True (prevents endless spam).
    restrict_to_business_hours : bool
        If True, the job will only execute during business hours. This is a more
        restrictive version of restrict_to_business_days.
    restrict_to_business_days : bool
        If True, the job will only execute during weekdays (i.e. not weekends).
    cascade : bool
        If True, when the job (denoted by the 'name' argument) is reflected
        multiple times in the jobs table due to having multiple 'at' values,
        changes in activiation in one will cascade to all others. For example,
        consider the job named 'my job' which is scheduled at 8:00 AM and 5:00
        PM that is cancelled on completion. If the 8:00 AM completes successfully
        then the job with that 'at' time will be set to inactive and have its status
        updated in the table accordingly. Under default behavior, the 5:00 PM run
        will be unaffected by the completion of the 8:00 AM run, however, if cascade
        is set to True then the 5:00 PM run will also receive the same updates.
    attempts : int
        If greater than 1, the job will be attempted this number of times before
        being cancelled.
    status : str | None
        current status of the job
    '''

    #╭-------------------------------------------------------------------------╮
    #| Class Attributes                                                        |
    #╰-------------------------------------------------------------------------╯

    verbose = True
    disable_print = True
    cascade_status = 'cancelled on cascade'


    #╭-------------------------------------------------------------------------╮
    #| Initialize Instance                                                     |
    #╰-------------------------------------------------------------------------╯

    def __init__(
        self,
        name,
        at,
        expiry,
        func,
        args=(),
        kwargs={},
        cancel_on_failure=False,
        cancel_on_completion=False,
        notify_on_failure=False,
        restrict_to_business_hours=False,
        restrict_to_business_days=False,
        cascade=True,
        attempts=1
        ):

        if self.verbose and not self.disable_print:
            raise NotImplementedError(
                'if Task.verbose is True then disable_print must be True '
                'to suppress intra-function prints.')

        self.name = name
        self.at = at
        self.expiry = expiry
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.cancel_on_failure = cancel_on_failure
        self.cancel_on_completion = cancel_on_completion
        self.notify_on_failure = notify_on_failure
        self.cascade = cascade
        self.restrict_to_business_hours = restrict_to_business_hours
        self.restrict_to_business_days = restrict_to_business_days
        self.attempts = attempts
        self.status = None


    #╭-------------------------------------------------------------------------╮
    #| Instance Methods                                                        |
    #╰-------------------------------------------------------------------------╯

    def update_table(self, active):

        def exe(sql, status):
            self.master.db.execute(sql, (active, status, self.name, self.at))

        sql = self.db.update_query(
            tbl_name='jobs',
            update_cols=['active','status'],
            where_cols=['name','at']
            )
        exe(sql, self.status)

        if self.cascade:
            exe(sql.replace('[at] = ?', '[at] <> ?'), self.cascade_status)
            for name, at in self.master.jobs.keys():
                if name == self.name:
                    self.master.jobs[name, at].status = self.cascade_status


    def send_email_notification(self):
        raise NotImplementedError


    #╭-------------------------------------------------------------------------╮
    #| Magic Methods                                                           |
    #╰-------------------------------------------------------------------------╯

    def __call__(self):

        logger = getattr(self.master.logger, 'logger', None)

        def update_status(status, set_inactive=False):
            self.status = status
            if logger: logger.info(f"{self.name} status update: '{self.status}'")
            self.update_table(active=0 if set_inactive else 1)

        if self.expiry and self.expiry < Timestamp():
            update_status('cancelled on expiration', set_inactive=True)
            if self.verbose:
                print('Killing', end=' ')
                print(self.name, end='')
                print(f' @ {Timestamp()} ->', end=' ')
                print('Job Cancelled')

        # cancel job if it was cancelled on cascasde or
        # if it was set inactive after being scheduled
        if self.status == self.cascade_status or \
           not self.master.is_active(self.name, self.at):
            return CancelJob

        while True:
            try:
                start = time.time()
                if logger: logger.info(f'{self.name} start')

                if self.verbose:
                    print('Running', end=' ')
                    print(self.name, end='')
                    print(f' @ {Timestamp()} ->', end=' ')

                if self.restrict_to_business_hours and not Timestamp().is_business_hours:
                    raise PrerequisiteError('cannot execute outside of business hours')

                if self.restrict_to_business_days and not Timestamp().is_business_day:
                    raise PrerequisiteError('cannot execute during the weekend')

                if self.disable_print:
                    with redirect_stdout(open(os.devnull, 'w')):
                        out = self.func(*self.args, **self.kwargs)
                else:
                    out = self.func(*self.args, **self.kwargs)

                if self.verbose:
                    print(f'Complete {elapsed_time(time.time() - start)}', end='')
                    print(' (Job Cancelled)') if self.cancel_on_completion else print('')

                if logger: logger.info(f'{self.name} complete')

                if self.cancel_on_completion:
                    update_status('cancelled on completion', set_inactive=True)

                return CancelJob if self.cancel_on_completion else out

            except Exception as e:

                if isinstance(e, PrerequisiteError):
                    if self.verbose: print(f'PrerequisiteError: {e}')
                    if logger: logger.exception('see traceback below')
                    return ContinueFailedJob

                if self.attempts > 0: self.attempts -= 1
                self.cancel_on_failure = True if self.attempts == 0 else False

                # wait 5 seconds then try again
                if self.attempts > 0:
                    time.sleep(5)
                    continue

                if self.verbose:
                    if self.cancel_on_failure:
                        print(f'Job Cancelled: {e}')
                    else:
                        print(f'Failed: {e}')

                if logger: logger.exception('see traceback below')

                if self.cancel_on_failure:
                    update_status('cancelled on failure', set_inactive=False)

                    if self.notify_on_failure:
                        self.send_email_notification()

                return CancelJob if self.cancel_on_failure else ContinueFailedJob