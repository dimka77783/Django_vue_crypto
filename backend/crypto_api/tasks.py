# backend/crypto_api/tasks.py
from celery import shared_task
from django.core.management import call_command

@shared_task
def run_full_parsing_pipeline():
    """
    Запускает полный пайплайн парсинга:
    - Upcoming
    - Investors
    - Launchpads
    - Tokenomics
    """
    call_command('run_parsers')
    return "✅ Парсинг завершён"