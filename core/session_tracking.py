"""Tracked login-session helpers used by auth views and heartbeat middleware."""

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from accounts.models import UserSession


SESSION_RECORD_KEY = "_pathgen_user_session_id"
SESSION_TOUCH_KEY = "_pathgen_user_session_touch_at"


def _minimum_interval_seconds():
    return int(getattr(settings, "PATHGEN_HEARTBEAT_MIN_INTERVAL", 30))


def _stale_after_seconds():
    return int(getattr(settings, "PATHGEN_HEARTBEAT_STALE_AFTER", 120))


def start_tracked_session(request):
    """Create the research session row associated with this browser session."""

    if not request.user.is_authenticated:
        return None

    now = timezone.now()
    tracked_session = UserSession.objects.create(
        user=request.user,
        login_at=now,
        last_heartbeat_at=now,
    )
    request.session[SESSION_RECORD_KEY] = tracked_session.pk
    request.session[SESSION_TOUCH_KEY] = now.timestamp()
    return tracked_session


def touch_tracked_session(request, *, force=False):
    """Record bounded active time without writing on every HTTP request."""

    if not request.user.is_authenticated:
        return None

    now = timezone.now()
    last_touch = request.session.get(SESSION_TOUCH_KEY)
    if not force and last_touch is not None:
        try:
            if now.timestamp() - float(last_touch) < _minimum_interval_seconds():
                return None
        except (TypeError, ValueError):
            pass

    tracked_session_id = request.session.get(SESSION_RECORD_KEY)
    if not tracked_session_id:
        return start_tracked_session(request)

    with transaction.atomic():
        tracked_session = (
            UserSession.objects.select_for_update()
            .filter(
                pk=tracked_session_id,
                user=request.user,
                logout_at__isnull=True,
            )
            .first()
        )
        if tracked_session is None:
            return start_tracked_session(request)

        elapsed = max(
            0,
            int((now - tracked_session.last_heartbeat_at).total_seconds()),
        )
        if elapsed >= _minimum_interval_seconds() or force:
            tracked_session.active_duration_seconds += min(
                elapsed,
                _stale_after_seconds(),
            )
            tracked_session.last_heartbeat_at = now
            tracked_session.save(
                update_fields=[
                    "active_duration_seconds",
                    "last_heartbeat_at",
                ]
            )

    request.session[SESSION_TOUCH_KEY] = now.timestamp()
    return tracked_session


def end_tracked_session(request):
    """Close the current tracked session before Django flushes auth state."""

    if not request.user.is_authenticated:
        return None

    tracked_session_id = request.session.get(SESSION_RECORD_KEY)
    if not tracked_session_id:
        return None

    now = timezone.now()
    with transaction.atomic():
        tracked_session = (
            UserSession.objects.select_for_update()
            .filter(
                pk=tracked_session_id,
                user=request.user,
                logout_at__isnull=True,
            )
            .first()
        )
        if tracked_session is None:
            return None

        elapsed = max(
            0,
            int((now - tracked_session.last_heartbeat_at).total_seconds()),
        )
        tracked_session.active_duration_seconds += min(
            elapsed,
            _stale_after_seconds(),
        )
        tracked_session.last_heartbeat_at = now
        tracked_session.logout_at = now
        tracked_session.save(
            update_fields=[
                "active_duration_seconds",
                "last_heartbeat_at",
                "logout_at",
            ]
        )

    request.session.pop(SESSION_RECORD_KEY, None)
    request.session.pop(SESSION_TOUCH_KEY, None)
    return tracked_session
