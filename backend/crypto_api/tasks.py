# backend/crypto_api/tasks.py
from celery import shared_task
from django.core.management import call_command


@shared_task
def run_full_parsing_pipeline():
    """
    Celery задача для запуска полного парсинга
    Вызывается как из API, так и по расписанию
    """
    print("🚀 ЗАПУСК ПАЙПЛАЙНА ЧЕРЕЗ CELERY")
    try:
        call_command('run_parsers')
        print("✅ Пайплайн завершён")
        return "Parsing completed"
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return f"Error: {str(e)}"