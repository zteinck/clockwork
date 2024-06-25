import datetime
import time
import uuid
from iterlab import to_iter
from pathpilot import Folder

from ..core import Date
from ._scheduler import TaskScheduler
from ._task import Task



#╭-------------------------------------------------------------------------╮
#| Classes                                                                 |
#╰-------------------------------------------------------------------------╯

class TaskMaster(object):
    '''
    Description
    --------------------
    Class provides a user-friendly means of using the TaskScheduler implementation of
    schedule.Scheduler to schedule SmartJobs

    Class Attributes
    --------------------
    db : SQLiteFile
        database
    scheduler : TaskScheduler
        TaskScheduler instance
    jobs : dict
        ...
    logger : None | Logger
        logger

    Instance Attributes
    --------------------
    None
    '''

    #╭-------------------------------------------------------------------------╮
    #| Class Attributes                                                        |
    #╰-------------------------------------------------------------------------╯

    jobs = {}
    logger = None


    #╭-------------------------------------------------------------------------╮
    #| Class Methods                                                           |
    #╰-------------------------------------------------------------------------╯

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
            Task.name
        at : str
            Task.at
        active : binary
            If 1, the job is active and able to be scheduled.
            If 0, the job is inactive and unable to be scheduled. This value is obtained via one of the following avenues
                1) job completed succesfully and was cancelled
                2) job obained this status via cascade from a job that satisfied criteria in 1)
                3) job was manually set inactive via TaskMaster.set_inactive method
        expiry : str
            Task.expiry
        status : str
            Task.status
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
            Task func argument
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
            keyword arguments passed to Task.__init__

        Returns
        ------------
        None
        '''

        if not hasattr(cls, 'db'):
            cls.db = Folder().parent.join('Data', 'SQLite', read_only=False).join('taskmaster.sqlite')
            cls.db.connect()
            cls.db.enable_foreign_keys()

        if not hasattr(cls, 'scheduler'):
            cls.scheduler = TaskScheduler()

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
            job = getattr(cls.scheduler.every(interval), every)
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
            cls.jobs[name, at] = Task(name, at, expiry, func, **kwargs)
            job.do(cls.jobs[name, at])


    @classmethod
    def run(cls, wait=0):
        while True:
            cls.scheduler.run_pending()
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



#╭-------------------------------------------------------------------------╮
#| Assign Class Attribute                                                  |
#╰-------------------------------------------------------------------------╯

Task.master = TaskMaster