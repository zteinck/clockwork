import datetime
import time
import uuid
import os
from contextlib import redirect_stdout
from schedule import Scheduler, CancelJob
from iterlab import to_iter
from pathpilot import Folder

from .core import Date, elapsed_time
from .chronicle import Logger



#+---------------------------------------------------------------------------+
# Classes
#+---------------------------------------------------------------------------+

class PrerequisiteError(Exception):
    ''' exception used to indicate a prerequisite condition has not been met '''
    def __init__(self, message):
        super().__init__(message)



class ContinueFailedJob(object):
    ''' can be returned to continue running a failed job '''
    pass



class SmartScheduler(Scheduler):
    '''
    Description
    --------------------
    Custom implementation of schedule.Scheduler designed to interact with SmartJob objects.
    This gives the user complete control over the behavior of individual jobs.
    '''

    def __init__(self):
        super().__init__()


    def _run_job(self, job):
        ret = job.run()
        if ret is CancelJob:
            self.cancel_job(job)
        elif ret is ContinueFailedJob:
            job.last_run = datetime.datetime.now()
            job._schedule_next_run()



class SmartJob(object):
    '''
    Description
    --------------------
    job object designed to be used in conjunction with SmartScheduler as the 'job' argument
    in self._run_job()

    Class Attributes
    --------------------
    verbose : bool
        If True, class content is printed to console.
    disable_print : bool
        If True, printing is suppressed while func runs. Must be True if verbose is True.
    cascade_status : str
        cascade status

    Instance Attributes
    --------------------
    name : str
        name of job
    at : str
        at time string
    expiry : Date
        If not None, job will be set inactive and stop running after this datetime
    func : func
        function to run
    args : tuple
        func arguments
    kwargs : dict
        func key word arguments
    cancel_on_failure : bool
        If True, the job will be cancelled if it raises an exception.
    cancel_on_completion : bool
        If True, the job will be cancelled if it completed successfully (i.e. job will run only once).
    notify_on_failure : bool
        If True, an email notification is sent to my inbox that includes the traceback. cancel_on_failure
        and cascade are automatically set to True if this argument is True (prevents endless spam).
    restrict_to_business_hours : bool
        If True, the job will only execute during business hours. This is a more restrictive version of restrict_to_business_days.
    restrict_to_business_days : bool
        If True, the job will only execute during weekdays (i.e. not weekends).
    cascade : bool
        If True, when the job (denoted by the 'name' argument) is reflected multiple times in the jobs table
        due to having multiple 'at' values, changes in activiation in one will cascade to all others. For example,
        consider the job named 'my job' which is scheduled at 8:00 AM and 5:00 PM that is cancelled on completion.
        If the 8:00 AM completes successfully then the job with that 'at' time will be set to inactive and have its
        status updated in the table accordingly. Under default behavior, the 5:00 PM run will be unaffected by the
        completion of the 8:00 AM run, however, if cascade is set to True then the 5:00 PM run will also receive
        the same updates.
    attempts : int
        If greater than 1, the job will be attempted this number of times before being cancelled.
    status : str | None
        current status of the job
    '''

    verbose = True
    disable_print = True
    cascade_status = 'cancelled on cascade'


    def __init__(self, name, at, expiry, func, args=(), kwargs={}, cancel_on_failure=False, cancel_on_completion=False,
                 notify_on_failure=False, restrict_to_business_hours=False, restrict_to_business_days=False, cascade=True,
                 attempts=1):

        if self.verbose and not self.disable_print:
            raise NotImplementedError('if SmartJob.verbose is True then disable_print must be True to suppress intra-function prints.')

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



    def update_table(self, active):

        def exe(sql, status):
            TaskMaster.db.execute(sql, (active, status, self.name, self.at))

        sql = self.db.update_query(
            tbl_name='jobs',
            update_cols=['active','status'],
            where_cols=['name','at']
            )
        exe(sql, self.status)

        if self.cascade:
            exe(sql.replace('[at] = ?', '[at] <> ?'), self.cascade_status)
            for name, at in TaskMaster.jobs.keys():
                if name == self.name:
                    TaskMaster.jobs[name, at].status = self.cascade_status



    def send_email_notification(self):
        raise NotImplementedError



    def __call__(self):

        logger = getattr(TaskMaster.logger, 'logger', None)

        def update_status(status, set_inactive=False):
            self.status = status
            if logger: logger.info(f"{self.name} status update: '{self.status}'")
            self.update_table(active=0 if set_inactive else 1)

        if self.expiry and self.expiry < Date():
            update_status('cancelled on expiration', set_inactive=True)
            if self.verbose:
                print('Killing', end=' ')
                print(self.name, end='')
                print(f' @ {Date()} ->', end=' ')
                print('Job Cancelled')

        # cancel job if it was cancelled on cascasde or if it was set inactive after being scheduled
        if self.status == self.cascade_status or not TaskMaster.is_active(self.name, self.at):
            return CancelJob

        while True:
            try:
                start = time.time()
                if logger: logger.info(f'{self.name} start')

                if self.verbose:
                    print('Running', end=' ')
                    print(self.name, end='')
                    print(f' @ {Date()} ->', end=' ')

                if self.restrict_to_business_hours and not Date().is_business_hours:
                    raise PrerequisiteError('cannot execute outside of business hours')

                if self.restrict_to_business_days and not Date().is_business_day:
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



class TaskMaster(object):
    '''
    Description
    --------------------
    Class provides a user-friendly means of using the SmartScheduler implementation of
    schedule.Scheduler to schedule SmartJobs

    Class Attributes
    --------------------
    db : SQLiteFile
        database
    smart_scheduler : SmartScheduler
        SmartScheduler instance
    jobs : dict
        ...
    logger : None | Logger
        logger


    Instance Attributes
    --------------------
    None
    '''

    jobs = {}
    logger = None


    @classmethod
    def set_inactive(cls, name, status=None):
        cls.db.execute(
            'UPDATE jobs SET active = ?, status = ? WHERE name = ?',
            (0, status or 'manual intervention', name)
            )


    @classmethod
    def clear_all(cls):
        cls.clear_table()
        if cls.logger is not None:
            cls.logger.clear()


    @classmethod
    def build_table(cls):
        '''
        Columns
        ----------
        name : str
            SmartJob.name
        at : str
            SmartJob.at
        active : binary
            If 1, the job is active and able to be scheduled.
            If 0, the job is inactive and unable to be scheduled. This value is obtained via one of the following avenues
                1) job completed succesfully and was cancelled
                2) job obained this status via cascade from a job that satisfied criteria in 1)
                3) job was manually set inactive via TaskMaster.set_inactive method
        expiry : str
            SmartJob.expiry
        status : str
            SmartJob.status
        '''

        sql = """
        CREATE TABLE IF NOT EXISTS
            jobs (
                name TEXT,
                at TEXT,
                active INTEGER,
                status TEXT,
                expiry TEXT,
                PRIMARY KEY(name, at)
                )"""

        cls.db.execute(sql)



    @classmethod
    def clear_table(cls, warn=False):
        cls.db.clear_tables(warn=warn)



    @classmethod
    def add(cls, func, every=None, at=None, interval=1, start=None, expiry=None, **kwargs):
        '''
        Description
        ------------
        schedule a job

        https://schedule.readthedocs.io/en/stable/
            schedule.every(10).minutes.do(job)
            schedule.every().hour.do(job)
            schedule.every().day.at('10:30').do(job)
            schedule.every().monday.do(job)
            schedule.every().wednesday.at('13:15').do(job)
            schedule.every().minute.at(':17').do(job)

        Parameters
        ------------
        func : func
            SmartJob func argument
        every : str
            string representation of schedule.Job property (e.g. 'minutes', 'hour', 'day' etc.).
            If None and cancel_on_completion kwarg is True, every and interval will be set to
            'second' and 1, respectively, so that the job will run ASAP once the 'start' criteria
            has been met (if applicable).
        at : str | iter
            time_str argument passed to schedule.Job.at(time_str). Times may be passed in
            '%I:%M%p' format (e.g ['06:15 AM', '12:15 PM', '06:15 PM']). If argument is an
            iterable then the job will be scheduled at each constituent time.
        interval : int
            schedule.Scheduler.every interval argument
        start : Date
            If not None, job will be not be added until this datetime
        expiry : Date
            If not None, job will be set inactive and stop running after this datetime
        kwargs : keyword arguments
            keyword arguments passed to SmartJob.__init__

        Returns
        ------------
        None
        '''

        if not hasattr(cls, 'db'):
            cls.db = Folder().parent.join('Data', 'SQLite', read_only=False).join('taskmaster.sqlite')
            cls.db.connect()
            cls.db.enable_foreign_keys()

        if not hasattr(cls, 'smart_scheduler'):
            cls.smart_scheduler = SmartScheduler()

        now = Date()
        if (start and start > now) or (expiry and expiry < now): return
        expiry_str = expiry.dt.strftime('%Y-%m-%d %I:%M:%S.{} %p')\
                     .format('%03d' % (expiry.dt.microsecond / 1000))\
                     if expiry else None

        cls.build_table()
        name = kwargs.pop('name', f'Unnamed {uuid.uuid4().hex}')

        if every is None:
            if kwargs.get('cancel_on_completion'):
                every, interval = 'second', 1
            else:
                raise Exception("'every' argument cannot be None")

        for at in to_iter(at):
            job = getattr(cls.smart_scheduler.every(interval), every)
            if at is not None:
                try:
                    time_str = datetime.datetime.strptime(
                        at.upper().replace(' ',''), '%I:%M%p'
                        ).strftime('%H:%M')
                except:
                    time_str = at
                job = job.at(time_str)
            else:
                at = 'N/A'

            # if already scheduled or inactive then do not schedule
            if (name, at) in cls.jobs or not cls.is_active(name, at): continue
            cls.db.insert('jobs', (name, at, 1, None, expiry_str))
            cls.jobs[name, at] = SmartJob(name, at, expiry, func, **kwargs)
            job.do(cls.jobs[name, at])


    @classmethod
    def run(cls, wait=0):
        while True:
            cls.smart_scheduler.run_pending()
            time.sleep(wait)


    @classmethod
    def is_active(cls, name, at=None):
        where_cols, params = ['name'], [name]
        if at is not None:
            where_cols.append('at')
            params.append(at)
        sql = cls.db.select_query(
            tbl_name='jobs',
            select_cols='active',
            where_cols=where_cols
            )
        try:
            active = int(cls.db.c.execute(sql, tuple(params)).fetchone()[0])
            if active == 0: return False
        except:
            pass
        return True



class FileMonitor(object):
    '''
    Description
    --------------------
    Monitors a folder for new files and passes latest and 2nd latest file names to user-defined function.
    Class is intended to be used in conjunction with TaskMaster as a func argument which allows for file
    monitoring at regular intervals.

    Class Attributes
    --------------------
    None

    Instance Attributes
    --------------------
    func : func
        Custom function that takes the latest and second-latest file names in a folder as the first and second arguments, respectively.
    folder : Folder object
        folder to monitor for new files.
    pick_file_kwargs : dict
        Key word arguments for file_tools.folder.pick_file
    verbose : bool
        If True, information is printed to the console.
    latest_file : File
        the latest file
    '''

    def __init__(self, func, folder, pick_file_kwargs={}, verbose=False):
        self.func = func
        self.folder = folder
        self.pick_file_kwargs = pick_file_kwargs
        self.verbose = verbose
        self.latest_file = self.pick_file()


    def pick_file(self):
        return self.folder.pick_file(**self.pick_file_kwargs)


    def __call__(self):
        latest_file = self.pick_file()

        if latest_file != self.latest_file:
            if self.verbose:
                print('new file detected:')
                print('\t*', latest_file)
                print('\t*', self.latest_file)
                print()

            self.func(latest_file, self.latest_file)
            self.latest_file = latest_file
        else:
            raise PrerequisiteError('no new files have been detected')


    def ad_hoc(self):
        ''' runs self.func using latest and 2nd latest file '''
        new_file = self.pick_file()

        kwargs = self.pick_file_kwargs.copy()
        kwargs['func'] = 1
        prior_file = self.folder.pick_file(**kwargs)

        if self.verbose:
            print('Ad hoc files:')
            print('\t*', new_file)
            print('\t*', prior_file)
            print()

        self.func(new_file, prior_file)



if __name__ == '__main__':

    def test_func():
        time.sleep(3)

    TaskMaster.logger = Logger('TaskMaster')

    TaskMaster.add(
        func=test_func,
        every='seconds',
        at=None,
        interval=10,
        start=None,
        expiry=None,
        # **kwargs
        )

    TaskMaster.run()