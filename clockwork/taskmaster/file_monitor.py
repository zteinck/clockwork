from .utils import PrerequisiteError


class FileMonitor(object):
    '''
    Description
    --------------------
    Monitors a folder for new files and passes latest and 2nd latest file
    names to user-defined function. Class is intended to be used in
    conjunction with TaskMaster as a func argument which allows for file
    monitoring at regular intervals.

    Class Attributes
    --------------------
    None

    Instance Attributes
    --------------------
    func : func
        Custom function that takes the latest and second-latest file names
        in a folder as the first and second arguments, respectively.
    folder : Folder object
        folder to monitor for new files.
    filter_kwargs : dict
        Key word arguments for folder.files.flter method.
    verbose : bool
        If True, information is printed to the console.
    latest_file : File
        the latest file
    '''

    #╭-------------------------------------------------------------------------╮
    #| Initialize Instance                                                     |
    #╰-------------------------------------------------------------------------╯

    def __init__(self, func, folder, filter_kwargs={}, verbose=False):
        self.func = func
        self.folder = folder
        self.filter_kwargs = filter_kwargs
        self.verbose = verbose
        self.latest_file = self.pick_file()


    #╭-------------------------------------------------------------------------╮
    #| Instance Methods                                                        |
    #╰-------------------------------------------------------------------------╯

    def pick_file(self):
        return self.folder.files.filter(**self.filter_kwargs)


    #╭-------------------------------------------------------------------------╮
    #| Magic Methods                                                           |
    #╰-------------------------------------------------------------------------╯

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

        kwargs = self.filter_kwargs.copy()
        kwargs['func'] = 1
        prior_file = self.folder.files.filter(**kwargs)

        if self.verbose:
            print('Ad hoc files:')
            print('\t*', new_file)
            print('\t*', prior_file)
            print()

        self.func(new_file, prior_file)