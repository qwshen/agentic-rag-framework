import os
import time
import threading

from queue import Queue, Empty
from datetime import datetime
from enum import Enum
from types import NoneType
from typing import Callable
from croniter import croniter
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from .utils import is_file_ready

# Enum for schedule events
class ScheduleEvent(Enum):
    TimeEvent = 1
    FileEvent = 2

# Base class for all schedulers
class Scheduler:
    def __init__(self):
        self._callbacks = []
        self._queue = Queue()

    def add_callback(self, job: Callable[[ScheduleEvent, dict], NoneType]):
        self._callbacks.append(job)

    # run the callbacks through items in the queue
    def _run(self):
        while True:
            try:
                # get the closest runs
                event_type, event_kwargs = self._queue.get(True, 3)
                # run each callback
                for callback in self._callbacks:
                    callback(event=event_type, kwargs=event_kwargs)
            except Empty:
                time.sleep(1)

    def run(self):
        if self._callbacks is not None and len(self._callbacks) > 0:
            # start a thread to run the callbacks
            threading.Thread(target=self._run).start()
   
# Scheduler for schedules defined by cron expressions
#   such as '0 0 1 * *' (every first day of the month at midnight)
class CronScheduler(Scheduler):
    def __init__(self, crons: list[str]):
        super().__init__()
        if crons is None or len(crons) <= 0:
            raise ValueError("At least on cron expression is required for CronScheduler")
        if not isinstance(crons, list):
            raise TypeError("crons must be a list of cron expressions")
        # verify cron expressions
        for cron in crons:
            try:
                croniter(cron, datetime.now())
            except ValueError as e:
                raise ValueError(f"Invalid cron expression '{cron}': {e}")
        # store cron expressions
        self._crons = crons

    # get the closest runs for the current time
    #   returns a tuple of (last_run, current_time, next_run)
    def _closest_runs(self, cron: str) -> tuple[datetime, datetime, datetime]:
        now = datetime.now()
        it = croniter(cron, now)
        dt_last_run, dt_next_run = (it.get_prev(datetime), it.get_next(datetime))
        gap = dt_next_run - dt_last_run
        return (dt_last_run - gap, now, dt_next_run - gap)

    # execute the callbacks if the next run is within the interval
    def _trigger(self, **kwargs: dict):
        run_cron = kwargs.get("run_cron", None)        
        # get the closest runs
        dt_last_run, _, dt_next_run = self._closest_runs(run_cron)
        # put the run into the queue
        self._queue.put((ScheduleEvent.TimeEvent, {"run_start_ts": dt_last_run, "run_end_ts": dt_next_run}))
                
    # run the scheduler
    def run(self):
        if self._callbacks is not None and len(self._callbacks) > 0:
            super().run()

            scheduler = BlockingScheduler()
            # add a job for each cron expression
            for cron in self._crons:
                scheduler.add_job(func=self._trigger, trigger=CronTrigger.from_crontab(cron), kwargs={"run_cron": cron})
            # start the scheduler
            scheduler.start()



# Handler for file system events
class _fileArrivalHandler(FileSystemEventHandler):
    def __init__(self, callbacks: list[Callable[[ScheduleEvent, dict], NoneType]], queue: Queue):
        super().__init__()

        # verify callbacks
        if callbacks is None or not isinstance(callbacks, list) or len(callbacks) <= 0:
            raise ValueError("At least one callback is required for FileArrivalScheduler")
        if not all(callable(callback) for callback in callbacks):
            raise TypeError("All callbacks must be callable")

        self._callbacks = callbacks
        self._queue = queue

    # called when a file is created
    #   it checks if the file is ready and calls the callbacks
    def on_created(self, event):
        # ignore directories
        if event.is_directory or not event.event_type == 'created':
            return
        
        # run each callback if the file is created
        if self._callbacks is not None and len(self._callbacks) > 0:
            # check if the file is ready
            if is_file_ready(event.src_path):
                self._queue.put((ScheduleEvent.FileEvent, {"file_path": event.src_path}))


# Scheduler for file arrivals in a directory
#   it will call the callbacks when a file is created in the directory
#   it will check if the file is ready to be processed
#   it will call the callbacks with the file path
class FileArrivalScheduler(Scheduler):
    def __init__(self, directory: str, recursive: bool = True):
        super().__init__()
        # verify the directory
        if directory is None or not isinstance(directory, str) or len(directory.strip()) == 0:
            raise ValueError("A valid directory path is required for FileArrivalScheduler")

        self._directory = directory
        self._recursive = recursive
        
        # verify if the directory exists
        if not os.path.isdir(self._directory):
            raise ValueError(f"The directory '{self._directory}' does not exist or is not a directory.")
        # verify if the directory is readable
        if not os.access(self._directory, os.R_OK):
            raise ValueError(f"The directory '{self._directory}' is not readable.")
               
    # run the scheduler
    def run(self):
        if self._callbacks is not None and len(self._callbacks) > 0:
            super().run()

            handler = _fileArrivalHandler(self._callbacks, self._queue)
            # create an observer to watch the directory
            observer = Observer()
            # schedule the handler for the directory
            observer.schedule(handler, self._directory, recursive = self._recursive)
            # start the observer
            observer.start()        
        
