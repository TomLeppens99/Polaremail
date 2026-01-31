"""
Webhook listener for Polar Accesslink events.
Receives and processes EXERCISE, SLEEP, and ACTIVITY_SUMMARY events.
"""

import hmac
import hashlib
import logging
from datetime import datetime
from typing import Optional

from flask import Flask, request, jsonify, redirect, session
from flask_cors import CORS

from .config import Config
from .models import (
    get_session as get_db_session, init_db, WebhookEvent,
    Exercise, SleepRecord, ActivitySummary
)
from .auth import PolarAuth
from .polar_api import PolarAPI

logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = Config.FLASK_SECRET_KEY
CORS(app)

# Initialize auth handler
polar_auth = PolarAuth()


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """
    Verify webhook signature using HMAC SHA-256.

    Args:
        payload: Raw request body
        signature: Signature from Polar-Webhook-Signature header

    Returns:
        True if signature is valid
    """
    if not Config.WEBHOOK_SECRET:
        logger.warning("Webhook secret not configured - skipping verification")
        return True

    expected_signature = hmac.new(
        Config.WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature)


def process_exercise_event(event_data: dict, db_session) -> Optional[Exercise]:
    """
    Process an EXERCISE webhook event.

    Args:
        event_data: Webhook event payload
        db_session: Database session

    Returns:
        Created Exercise record or None
    """
    entity_id = event_data.get('entity_id')
    user_id = event_data.get('user_id')

    if not entity_id or not user_id:
        logger.error("Missing entity_id or user_id in exercise event")
        return None

    # Check if already exists
    existing = db_session.query(Exercise).filter_by(
        polar_exercise_id=str(entity_id)
    ).first()

    if existing:
        logger.info(f"Exercise {entity_id} already exists, skipping")
        return existing

    # Fetch full exercise data from API
    try:
        api = PolarAPI(user_id=str(user_id))
        exercise_data = api.get_exercise_details(str(entity_id))

        if not exercise_data:
            logger.error(f"Could not fetch exercise details for {entity_id}")
            return None

        # Parse heart rate zones
        hr_zones = {}
        if 'heart_rate' in exercise_data and 'zones' in exercise_data['heart_rate']:
            for i, zone in enumerate(exercise_data['heart_rate']['zones'], 1):
                zone_duration = PolarAPI.parse_iso_duration(zone.get('in_zone', 'PT0S'))
                hr_zones[f'zone{i}'] = zone_duration

        from dateutil import parser as date_parser

        exercise = Exercise(
            polar_exercise_id=str(entity_id),
            user_id=str(user_id),
            sport=exercise_data.get('sport'),
            start_time=date_parser.parse(exercise_data['start_time']) if exercise_data.get('start_time') else None,
            duration_seconds=PolarAPI.parse_iso_duration(exercise_data.get('duration', '')),
            duration_iso=exercise_data.get('duration'),
            distance_meters=exercise_data.get('distance'),
            calories=exercise_data.get('calories'),
            average_heart_rate=exercise_data.get('heart_rate', {}).get('average'),
            max_heart_rate=exercise_data.get('heart_rate', {}).get('maximum'),
            heart_rate_zones=hr_zones if hr_zones else None,
            training_load_cardio=exercise_data.get('training_load', {}).get('cardio_load'),
            training_load_muscle=exercise_data.get('training_load', {}).get('muscle_load'),
            ascent_meters=exercise_data.get('ascent'),
            descent_meters=exercise_data.get('descent'),
            running_index=exercise_data.get('running_index', {}).get('value'),
            raw_payload=exercise_data,
            source='webhook'
        )

        db_session.add(exercise)
        logger.info(f"Created exercise record from webhook: {entity_id}")
        return exercise

    except Exception as e:
        logger.error(f"Error processing exercise event: {e}")
        return None


def process_sleep_event(event_data: dict, db_session) -> Optional[SleepRecord]:
    """
    Process a SLEEP webhook event.

    Args:
        event_data: Webhook event payload
        db_session: Database session

    Returns:
        Created SleepRecord or None
    """
    user_id = event_data.get('user_id')
    sleep_date_str = event_data.get('date')

    if not user_id or not sleep_date_str:
        logger.error("Missing user_id or date in sleep event")
        return None

    from dateutil import parser as date_parser
    try:
        sleep_date = date_parser.parse(sleep_date_str).date()
    except (ValueError, date_parser.ParserError) as e:
        logger.error(f"Invalid date format in sleep event: {sleep_date_str} - {e}")
        return None

    # Check if already exists
    existing = db_session.query(SleepRecord).filter_by(
        user_id=str(user_id),
        sleep_date=sleep_date
    ).first()

    if existing:
        logger.info(f"Sleep record for {sleep_date} already exists")
        return existing

    # Fetch full sleep data from API and find matching record
    try:
        api = PolarAPI(user_id=str(user_id))
        sleep_records = api.get_sleep_data()

        sleep_data = None
        for record in sleep_records:
            if record.get('date') == sleep_date_str:
                sleep_data = record
                break

        if not sleep_data:
            logger.warning(f"Could not find sleep data for {sleep_date_str}")
            return None

        # Parse sleep stages
        light_seconds = 0
        deep_seconds = 0
        rem_seconds = 0
        wake_seconds = 0

        for stage in sleep_data.get('hypnogram', []):
            stage_type = stage.get('sleep_stage')
            duration = PolarAPI.parse_iso_duration(stage.get('duration', 'PT0S'))

            if stage_type == 1:
                rem_seconds += duration
            elif stage_type == 2:
                light_seconds += duration
            elif stage_type == 3:
                deep_seconds += duration
            elif stage_type == 0:
                wake_seconds += duration

        sleep_record = SleepRecord(
            user_id=str(user_id),
            sleep_date=sleep_date,
            sleep_start=date_parser.parse(sleep_data['sleep_start_time']) if sleep_data.get('sleep_start_time') else None,
            sleep_end=date_parser.parse(sleep_data['sleep_end_time']) if sleep_data.get('sleep_end_time') else None,
            duration_seconds=PolarAPI.parse_iso_duration(sleep_data.get('duration', '')),
            light_sleep_seconds=light_seconds,
            deep_sleep_seconds=deep_seconds,
            rem_sleep_seconds=rem_seconds,
            wake_seconds=wake_seconds,
            sleep_score=sleep_data.get('sleep_score'),
            sleep_continuity=sleep_data.get('continuity'),
            sleep_cycles=sleep_data.get('sleep_cycles'),
            average_heart_rate=sleep_data.get('heart_rate_avg'),
            min_heart_rate=sleep_data.get('heart_rate_min'),
            average_breathing_rate=sleep_data.get('breathing_rate_avg'),
            raw_payload=sleep_data,
            source='webhook'
        )

        db_session.add(sleep_record)
        logger.info(f"Created sleep record from webhook: {sleep_date}")
        return sleep_record

    except Exception as e:
        logger.error(f"Error processing sleep event: {e}")
        return None


def process_activity_event(event_data: dict, db_session) -> Optional[ActivitySummary]:
    """
    Process an ACTIVITY_SUMMARY webhook event.

    Args:
        event_data: Webhook event payload
        db_session: Database session

    Returns:
        Created ActivitySummary or None
    """
    user_id = event_data.get('user_id')
    activity_date_str = event_data.get('date')

    if not user_id or not activity_date_str:
        logger.error("Missing user_id or date in activity event")
        return None

    from dateutil import parser as date_parser
    try:
        activity_date = date_parser.parse(activity_date_str).date()
    except (ValueError, date_parser.ParserError) as e:
        logger.error(f"Invalid date format in activity event: {activity_date_str} - {e}")
        return None

    # Check if already exists
    existing = db_session.query(ActivitySummary).filter_by(
        user_id=str(user_id),
        activity_date=activity_date
    ).first()

    if existing:
        # Update existing record
        existing.raw_payload = event_data
        existing.updated_at = datetime.utcnow()
        logger.info(f"Updated activity summary for {activity_date}")
        return existing

    # Create new record from webhook data
    activity = ActivitySummary(
        user_id=str(user_id),
        activity_date=activity_date,
        active_calories=event_data.get('active_calories'),
        total_calories=event_data.get('calories'),
        steps=event_data.get('steps'),
        active_time_seconds=PolarAPI.parse_iso_duration(event_data.get('active_time', '')) if event_data.get('active_time') else None,
        activity_goal_percent=event_data.get('goal_percent'),
        raw_payload=event_data,
        source='webhook'
    )

    db_session.add(activity)
    logger.info(f"Created activity summary from webhook: {activity_date}")
    return activity


# Flask routes

@app.route('/')
def index():
    """Home page with status info."""
    return jsonify({
        'service': 'Polar Weekly Report',
        'status': 'running',
        'endpoints': {
            'webhook': '/webhook',
            'auth': '/auth',
            'callback': '/callback',
            'status': '/status'
        }
    })


@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Webhook endpoint for receiving Polar events.
    Verifies signature and processes events.
    """
    # Get signature from header
    signature = request.headers.get('Polar-Webhook-Signature', '')

    # Verify signature
    if not verify_webhook_signature(request.data, signature):
        logger.warning("Invalid webhook signature")
        return jsonify({'error': 'Invalid signature'}), 401

    # Parse event data
    try:
        event_data = request.json
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        return jsonify({'error': 'Invalid JSON'}), 400

    if not event_data:
        return jsonify({'error': 'Empty payload'}), 400

    event_type = event_data.get('event')
    logger.info(f"Received webhook event: {event_type}")

    # Store raw event
    db_session = get_db_session()
    try:
        webhook_event = WebhookEvent(
            event_type=event_type,
            event_id=event_data.get('entity_id'),
            user_id=event_data.get('user_id'),
            payload=event_data
        )
        db_session.add(webhook_event)

        # Process based on event type
        result = None
        if event_type == 'EXERCISE':
            result = process_exercise_event(event_data, db_session)
        elif event_type == 'SLEEP':
            result = process_sleep_event(event_data, db_session)
        elif event_type == 'ACTIVITY_SUMMARY':
            result = process_activity_event(event_data, db_session)
        else:
            logger.warning(f"Unknown event type: {event_type}")

        # Mark event as processed
        webhook_event.processed = True
        webhook_event.processed_at = datetime.utcnow()

        db_session.commit()

        return jsonify({
            'status': 'success',
            'event_type': event_type,
            'processed': result is not None
        }), 200

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error processing webhook: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db_session.close()


@app.route('/auth')
def auth():
    """
    Start OAuth2 authorization flow.
    Redirects user to Polar login page.
    """
    import secrets
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state

    auth_url = polar_auth.get_authorization_url(state=state)
    return redirect(auth_url)


@app.route('/callback')
def callback():
    """
    OAuth2 callback endpoint.
    Exchanges authorization code for access token.
    """
    error = request.args.get('error')
    if error:
        return jsonify({'error': error, 'description': request.args.get('error_description')}), 400

    code = request.args.get('code')
    state = request.args.get('state')

    # Verify state
    stored_state = session.get('oauth_state')
    if state != stored_state:
        return jsonify({'error': 'Invalid state parameter'}), 400

    if not code:
        return jsonify({'error': 'No authorization code received'}), 400

    try:
        # Exchange code for token
        access_token, user_id = polar_auth.exchange_code_for_token(code)

        # Register user with Polar Accesslink
        user_info = polar_auth.register_user(access_token)

        # Save to database
        polar_auth.save_user_to_db(user_id, access_token, user_info)

        # Save to .env file
        polar_auth.save_token_to_env(access_token, user_id)

        # Initialize database
        init_db()

        # Sync initial data
        api = PolarAPI(access_token=access_token, user_id=user_id)
        sync_results = api.sync_all()

        return jsonify({
            'status': 'success',
            'message': 'Successfully authenticated with Polar',
            'user_id': user_id,
            'data_synced': sync_results,
            'next_steps': [
                'Configure webhook URL in .env file',
                'Run: python -m polar_report.webhook setup-webhook',
                'Start the scheduler for weekly reports'
            ]
        })

    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/status')
def status():
    """Get service status and data counts."""
    from .models import Exercise, SleepRecord, NightlyRecharge

    db_session = get_db_session()
    try:
        exercise_count = db_session.query(Exercise).count()
        sleep_count = db_session.query(SleepRecord).count()
        recharge_count = db_session.query(NightlyRecharge).count()

        return jsonify({
            'status': 'healthy',
            'database': {
                'exercises': exercise_count,
                'sleep_records': sleep_count,
                'nightly_recharge': recharge_count
            },
            'config': {
                'webhook_configured': Config.is_webhook_configured(),
                'email_configured': Config.is_email_configured(),
                'polar_configured': bool(Config.POLAR_ACCESS_TOKEN)
            }
        })
    finally:
        db_session.close()


@app.route('/sync', methods=['POST'])
def sync_data():
    """Manually trigger data sync from Polar API."""
    if not Config.POLAR_ACCESS_TOKEN:
        return jsonify({'error': 'Not authenticated with Polar'}), 401

    try:
        api = PolarAPI()
        results = api.sync_all()
        return jsonify({
            'status': 'success',
            'synced': results
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.before_request
def ensure_db():
    """Ensure database is initialized before handling requests."""
    init_db()


def run_server(host: str = '0.0.0.0', port: int = 5000, debug: bool = None):
    """
    Run the Flask webhook server.

    Args:
        host: Host to bind to
        port: Port to bind to
        debug: Enable debug mode (defaults to config)
    """
    if debug is None:
        debug = Config.FLASK_DEBUG

    logger.info(f"Starting webhook server on {host}:{port}")
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1 and sys.argv[1] == 'setup-webhook':
        from .auth import setup_webhook
        try:
            result = setup_webhook()
            print(f"Webhook registered: {result}")
        except Exception as e:
            print(f"Failed to setup webhook: {e}")
            sys.exit(1)
    else:
        run_server()
