# backend/crypto_api/views.py
from rest_framework import generics
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import HttpResponse
from django.core import management
from django.conf import settings
import json
import psycopg2
from .models import UpcomingCrypto
from .serializers import UpcomingCryptoSerializer

# --- Модели и сериализаторы ---
class CryptoListAPIView(generics.ListAPIView):
    """
    Список всех upcoming-проектов
    GET /api/coins/
    """
    queryset = UpcomingCrypto.objects.all()
    serializer_class = UpcomingCryptoSerializer


class CryptoDetailAPIView(generics.RetrieveAPIView):
    """
    Детали одного проекта
    GET /api/coins/<id>/
    """
    queryset = UpcomingCrypto.objects.all()
    serializer_class = UpcomingCryptoSerializer


# --- Запуск парсинга ---
@api_view(['POST'])
def trigger_parsing(request):
    """
    Запускает полный парсинг через Celery
    POST /api/trigger-parsing/
    """
    def run():
        management.call_command('run_parsers')
    import threading
    thread = threading.Thread(target=run)
    thread.start()
    return Response({
        "status": "success",
        "message": "Parsing started"
    })


# --- Токеномика (из вьюшки tokenomics_detailed) ---
# --- Токеномика (из таблицы cryptorank_tokenomics) ---
class TokenomicsDetailedView(generics.ListAPIView):
    """
    Получает данные из таблицы cryptorank_tokenomics
    GET /api/tokenomics-detailed/
    """
    def get(self, request, *args, **kwargs):
        try:
            conn = psycopg2.connect(
                host=settings.DATABASES['default']['HOST'],
                port=settings.DATABASES['default']['PORT'],
                database=settings.DATABASES['default']['NAME'],
                user=settings.DATABASES['default']['USER'],
                password=settings.DATABASES['default']['PASSWORD']
            )
            cursor = conn.cursor()

            # Читаем данные из cryptorank_tokenomics
            cursor.execute("SELECT project_name, tokenomics FROM cryptorank_tokenomics;")
            rows = cursor.fetchall()
            conn.close()

            # Формируем список, раскрывая JSONB поле `tokenomics`
            data = []
            for row in rows:
                project_name, tokenomics_json = row
                # Добавляем project_name внутрь данных токеномики
                if isinstance(tokenomics_json, dict):
                    tokenomics_json['project_name'] = project_name
                    data.append(tokenomics_json)
                else:
                    data.append({
                        'project_name': project_name,
                        'error': 'Invalid tokenomics data',
                        'raw': tokenomics_json
                    })

            return Response(data)

        except Exception as e:
            return Response({"error": f"Database error: {str(e)}"}, status=500)


# --- OHLC данные по символу ---
class OHLCDataView(generics.GenericAPIView):
    """
    Получает OHLC-данные по символу монеты
    GET /api/ohlc/<symbol>/
    Пример: /api/ohlc/pvt/
    """
    def get(self, request, symbol):
        table_name = f"ohlc_{symbol.lower()}"
        try:
            conn = psycopg2.connect(
                host=settings.DATABASES['default']['HOST'],
                port=settings.DATABASES['default']['PORT'],
                database=settings.DATABASES['default']['NAME'],
                user=settings.DATABASES['default']['USER'],
                password=settings.DATABASES['default']['PASSWORD']
            )
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT 
                    date, open_price, high_price, low_price, med_price,
                    close_price, change_percent, volume_usd, change_volume_percent, market_cap
                FROM {table_name}
                ORDER BY date DESC;
            """)
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            data = [dict(zip(columns, row)) for row in rows]
            conn.close()
            return Response(data)
        except psycopg2.errors.UndefinedTable:
            return Response([], status=200)
        except Exception as e:
            return Response({"error": f"Database error: {str(e)}"}, status=500)


# --- Корневой эндпоинт (опционально) ---
def api_root(request):
    """
    Простая корневая страница API
    """
    return HttpResponse("""
    <h1>🚀 Crypto Backend API</h1>
    <p>Доступные эндпоинты:</p>
    <ul>
        <li><a href="/admin">Админка</a></li>
        <li><a href="/api/coins/">Список монет</a></li>
        <li><a href="/api/tokenomics-detailed/">Токеномика</a></li>
        <li><a href="/api/trigger-parsing/" target="_blank">Запустить парсинг</a></li>
    </ul>
    """)