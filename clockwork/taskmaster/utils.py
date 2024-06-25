

class PrerequisiteError(Exception):
    ''' exception used to indicate a prerequisite condition has not been met '''

    def __init__(self, message):
        super().__init__(message)


class ContinueFailedJob(object):
    ''' can be returned to continue running a failed job '''
    pass