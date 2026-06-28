# ============================================
#   VALCORE — DISCORD NOTIFICATION SERVICE
#   app/services/notifications.py
#
#   Same graceful-degradation pattern as
#   payments.py / storage.py: if no webhook
#   is set, this silently does nothing —
#   never crashes the calling route.
# ============================================

import requests
from app.core.database import get_setting


def is_discord_configured():
    return bool(get_setting('discord_webhook'))


def send_discord_notification(title, description, fields=None, color=0xD4AF37):
    """
    Sends a Discord embed message via webhook.
    fields: list of {'name': str, 'value': str, 'inline': bool}
    color: decimal color code (default gold, matches VALCORE branding)

    Fails silently if not configured or if the request errors —
    a notification failure should NEVER break the actual purchase/
    signup/ticket flow that triggered it.
    """
    if not is_discord_configured():
        return {'ok': False, 'error': 'Discord not configured'}

    webhook_url = get_setting('discord_webhook')

    payload = {
        'embeds': [{
            'title': title,
            'description': description,
            'color': color,
            'fields': fields or [],
        }]
    }

    try:
        resp = requests.post(webhook_url, json=payload, timeout=8)
        return {'ok': resp.status_code in (200, 204)}
    except requests.exceptions.RequestException:
        # Deliberately swallow errors — notifications are best-effort,
        # never let a Discord outage block a real purchase/signup.
        return {'ok': False, 'error': 'Discord request failed'}


def notify_purchase(product_name, customer_email, amount_naira):
    send_discord_notification(
        title='💰 New Purchase',
        description=f'**{product_name}** was just purchased.',
        fields=[
            {'name': 'Customer', 'value': customer_email, 'inline': True},
            {'name': 'Amount', 'value': f'₦{amount_naira:,}', 'inline': True},
        ],
        color=0x2ECC71,
    )


def notify_signup(username, email):
    send_discord_notification(
        title='👤 New Signup',
        description=f'**{username}** just joined VALCORE.',
        fields=[{'name': 'Email', 'value': email, 'inline': True}],
        color=0x3B82F6,
    )


def notify_appointment(name, project_type):
    send_discord_notification(
        title='📅 New Appointment Request',
        description=f'**{name}** booked an appointment.',
        fields=[{'name': 'Project Type', 'value': project_type or 'Not specified', 'inline': True}],
        color=0xF1C40F,
    )


def notify_support_ticket(subject, username):
    send_discord_notification(
        title='💬 New Support Ticket',
        description=f'**{subject}**',
        fields=[{'name': 'From', 'value': username, 'inline': True}],
        color=0xE74C3C,
    )
