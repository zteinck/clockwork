import datetime
from schedule import Scheduler, CancelJob

from .utils import ContinueFailedJob



class TaskScheduler(Scheduler):

    def __init__(self):
        super().__init__()


    def _run_job(self, job):
        ret = job.run()
        if ret is CancelJob:
            self.cancel_job(job)
        elif ret is ContinueFailedJob:
            job.last_run = datetime.datetime.now()
            job._schedule_next_run()