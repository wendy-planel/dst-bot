"""定时任务"""

from typing import Callable, Any, List

import asyncio
from datetime import datetime, timedelta, tzinfo

import structlog


log = structlog.get_logger()


class Job:
    def __init__(
        self,
        func: Callable[..., Any],
        seconds: int | None = None,
        minutes: int | None = None,
        hours: int | None = None,
        days: int | None = None,
        at: str | None = None,
        once: datetime | None = None,
        tz: tzinfo | None = None,
    ) -> None:
        self.func = func
        self.func_name = getattr(self.func, "__name__", "unknown")
        # 距离多少时长后执行
        self.seconds = seconds
        self.minutes = minutes
        self.hours = hours
        self.days = days
        # 在某一时刻执行
        self.at = at
        # 一次性任务
        self.once = once
        # 标记这个job是否永远不可执行
        self.invalid = False
        # 时区
        self.tz = tz
        self.last_run: datetime = datetime.now(tz)
        self.next_run: datetime = self._next_run()

    def _are_you_ok(
        self,
        check_datetime: datetime,
        target_mdhms: List[str | int],
    ) -> bool:
        if check_datetime <= self.last_run:
            return False
        mdhms = [
            check_datetime.month,
            check_datetime.day,
            check_datetime.hour,
            check_datetime.minute,
            check_datetime.second,
        ]
        for i in range(5):
            if target_mdhms[i] != "*" and target_mdhms[i] != mdhms[i]:
                return False
        return True

    def _next_run(self):
        if self.interval is not None:
            next_run = self.last_run + timedelta(seconds=self.interval)
        elif self.once:
            next_run = self.once
        else:
            # 解析at获取下次运行时间, (月, 日, 时, 分, 秒) = * * * * *
            target_mdhms = self.at.split(" ")
            timedeltas = [
                timedelta(days=360),
                timedelta(days=29),
                timedelta(days=1),
                timedelta(hours=1),
                timedelta(minutes=1),
            ]
            last_mdhms = [
                self.last_run.month,
                self.last_run.day,
                self.last_run.hour,
                self.last_run.minute,
                self.last_run.second,
            ]
            mdhms = []
            max_timedelta = timedelta()
            for i in range(5):
                if target_mdhms[i] == "*":
                    mdhms.append(last_mdhms[i])
                else:
                    target_mdhms[i] = int(target_mdhms[i])
                    mdhms.append(target_mdhms[i])
                    max_timedelta = max(max_timedelta, timedeltas[i])
            next_run = datetime(self.last_run.year, *mdhms, tzinfo=self.tz)
            while not self._are_you_ok(next_run, target_mdhms):
                next_run += max_timedelta
        log.info(f"[Job] {self.func_name} next run: {next_run}")
        return next_run

    def refresh_next_run(self):
        if self.once is not None:
            self.invalid = True
        self.last_run = self.next_run
        self.next_run = self._next_run()

    @property
    def interval(self):
        interval = self.seconds
        if self.minutes:
            interval = self.minutes * 60
        elif self.hours:
            interval = self.hours * 60 * 60
        elif self.days:
            interval = self.days * 24 * 60 * 60
        return interval

    async def run(self):
        if asyncio.iscoroutinefunction(self.func):
            return await self.func()
        else:
            return self.func()

    @property
    def ready(self) -> bool:
        return datetime.now(self.tz) >= self.next_run and not self.invalid


class Schedule:
    def __init__(self) -> None:
        self.jobs: List[Job] = []
        self.tasks: List[asyncio.Task] = []

    def validate_at(sel, at: str) -> bool:
        if at is None:
            return True
        mdhms = at.split(" ")
        assert len(mdhms) == 5, f"at arg such as: '* * * * 1' not '{at}'"
        for i in mdhms:
            if i != "*":
                int(i)
        return True

    def job(
        self,
        seconds: int | None = None,
        minutes: int | None = None,
        hours: int | None = None,
        days: int | None = None,
        at: str | None = None,
        once: datetime | None = None,
        tz: tzinfo | None = None,
    ):
        """异步任务装饰器, 被装饰的函数会在指定的时间自动执行, 被装饰的函数必须是无参的.

        Args:
            seconds (int | None, optional): 每经过X秒执行.
            minutes (int | None, optional): 每经过X分钟执行.
            hours (int | None, optional): 每经过X小时执行.
            days (int | None, optional): 每经过X天执行.
            at (str | None, optional): 在某时刻执行24小时时间制(月, 日, 时, 分, 秒) = * * * * *.
            once (datetime | None, optional): 一次性任务，在指定是日期运行.
            tz (tzinfo | None, optional): 时区.
        """
        self.validate_at(at)

        def decorator(func: Callable[..., Any]):
            job = Job(func, seconds, minutes, hours, days, at, once, tz)
            self.jobs.append(job)
            return func

        return decorator

    def clear(self):
        """清理无效的job和执行完毕的task."""
        self.jobs = [job for job in self.jobs if not job.invalid]
        self.tasks = [task for task in self.tasks if not task.done()]

    async def run(self):
        interval = 0.1
        clear_interval = 0
        while True:
            for job in self.jobs:
                if job.ready:
                    # 刷新下次运行时间, 防止重复运行
                    job.refresh_next_run()
                    self.tasks.append(asyncio.create_task(job.run()))
            if clear_interval > 10:
                self.clear()
                clear_interval = 0
            clear_interval += interval
            await asyncio.sleep(0.1)

    def add_jobs(
        self,
        schedule: "Schedule" = None,
        jobs: List[Job] = [],
    ):
        if schedule is not None:
            for job in schedule.jobs:
                self.jobs.append(job)
        self.jobs.extend(jobs)

    def add_job(self, job: Job):
        self.jobs.append(job)


schedule = Schedule()
