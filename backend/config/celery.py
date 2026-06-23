import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("flewcae")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "dispatch-weekly-suggestions": {
        "task": "content_calendar.tasks.dispatch_weekly_suggestions",
        "schedule": crontab(day_of_week="mon", hour=6, minute=0),
    },
    "scan-reminder-escalations": {
        "task": "notifications.tasks.scan_reminder_escalations",
        "schedule": crontab(minute="*/15"),
    },
    "poll-pending-video-generations": {
        "task": "generation.tasks.poll_pending_video_generations",
        "schedule": crontab(minute="*/2"),
    },
    "refresh-stale-country-templates": {
        "task": "special_days.tasks.refresh_stale_country_templates",
        "schedule": crontab(hour=3, minute=0),
    },
}
