# ============================================
#   VALCORE — R2 STORAGE SERVICE
#   app/services/storage.py
#
#   Wraps Cloudflare R2 (S3-compatible).
#   Keys come from Settings, never hardcoded.
#   If not configured, upload functions return
#   a clear "not configured" error instead of
#   crashing — same pattern as Paystack/Discord.
# ============================================

import uuid
import os
from app.core.database import get_setting


def is_r2_configured():
    """Check if all required R2 settings are filled in."""
    required = [
        get_setting('r2_account_id'),
        get_setting('r2_access_key_id'),
        get_setting('r2_secret_access_key'),
        get_setting('r2_bucket_name'),
    ]
    return all(required)


def get_r2_client():
    """
    Returns a boto3 S3-compatible client configured for R2.
    Only call this after confirming is_r2_configured() is True.
    Requires: pip install boto3
    """
    import boto3

    account_id = get_setting('r2_account_id')
    access_key = get_setting('r2_access_key_id')
    secret_key = get_setting('r2_secret_access_key')

    return boto3.client(
        's3',
        endpoint_url=f'https://{account_id}.r2.cloudflarestorage.com',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name='auto',
    )


def upload_file(file_storage, folder='products'):
    """
    Uploads a Flask FileStorage object to R2.
    Returns: {'ok': True, 'url': '...'} or {'ok': False, 'error': '...'}
    """
    if not is_r2_configured():
        return {
            'ok': False,
            'error': 'Storage not configured. Add R2 credentials in Admin → Settings.'
        }

    try:
        client = get_r2_client()
        bucket = get_setting('r2_bucket_name')
        public_url = get_setting('r2_public_url').rstrip('/')

        ext = os.path.splitext(file_storage.filename)[1] or '.bin'
        key = f'{folder}/{uuid.uuid4().hex}{ext}'

        client.upload_fileobj(
            file_storage,
            bucket,
            key,
            ExtraArgs={'ContentType': file_storage.content_type or 'application/octet-stream'}
        )

        url = f'{public_url}/{key}' if public_url else f'https://{bucket}.r2.dev/{key}'
        return {'ok': True, 'url': url}

    except ImportError:
        return {'ok': False, 'error': 'boto3 not installed. Run: pip install boto3'}
    except Exception as e:
        return {'ok': False, 'error': f'Upload failed: {str(e)}'}


def upload_zip(file_storage, product_slug):
    """Same as upload_file but for ZIP downloads, stored in a separate folder."""
    if not is_r2_configured():
        return {
            'ok': False,
            'error': 'Storage not configured. Add R2 credentials in Admin → Settings.'
        }

    try:
        client = get_r2_client()
        bucket = get_setting('r2_bucket_name')
        public_url = get_setting('r2_public_url').rstrip('/')

        key = f'downloads/{product_slug}/{uuid.uuid4().hex}.zip'

        client.upload_fileobj(
            file_storage,
            bucket,
            key,
            ExtraArgs={'ContentType': 'application/zip'}
        )

        url = f'{public_url}/{key}' if public_url else f'https://{bucket}.r2.dev/{key}'
        return {'ok': True, 'url': url}

    except ImportError:
        return {'ok': False, 'error': 'boto3 not installed. Run: pip install boto3'}
    except Exception as e:
        return {'ok': False, 'error': f'Upload failed: {str(e)}'}
