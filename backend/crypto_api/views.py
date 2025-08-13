# backend/crypto_api/views.py

from rest_framework import generics
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import HttpResponse
from django.db import connection

from .models import UpcomingCrypto
from .serializers import UpcomingCryptoSerializer
from .tasks import run_full_parsing_pipeline


# --- API: Список монет ---
class CryptoListAPIView(generics.ListAPIView):
    """
    Возвращает список всех upcoming-проектов
    """
    queryset = UpcomingCrypto.objects.all()
    serializer_class = UpcomingCryptoSerializer


# --- API: Детали монеты ---
class CryptoDetailAPIView(generics.RetrieveAPIView):
    queryset = UpcomingCrypto.objects.all()
    serializer_class = UpcomingCryptoSerializer
    lookup_field = 'id'

    def retrieve(self, request, *args, **kwargs):
        # Получаем объект из cryptorank_upcoming
        instance = self.get_object()
        data = self.get_serializer(instance).data  # Сериализуем

        # Добавляем токеномику из cryptorank_tokenomics
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT tokenomics FROM cryptorank_tokenomics WHERE project_name = %s",
                [instance.project_name]
            )
            row = cursor.fetchone()
            if row:
                data['tokenomics'] = row[0]  # Добавляем в ответ
            else:
                data['tokenomics'] = None

        return Response(data)


# --- API: Токеномика (вся таблица) ---
class TokenomicsDetailedView(generics.ListAPIView):
    """
    Возвращает данные из вьюшки tokenomics_detailed
    """
    def get_queryset(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM tokenomics_detailed")
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def list(self, request, *args, **kwargs):
        return Response(self.get_queryset())


# --- API: OHLC (заглушка) ---
class OHLCDataView(generics.GenericAPIView):
    """
    Возвращает OHLC-данные (заглушка)
    """
    def get(self, request, symbol):
        data = {
            "symbol": symbol,
            "data": [
                {"time": "2025-08-01", "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.05},
                {"time": "2025-08-02", "open": 1.05, "high": 1.2, "low": 1.0, "close": 1.15},
            ]
        }
        return Response(data)


# --- API: Запуск парсинга ---
@api_view(['POST'])
def trigger_parsing(request):
    """
    Запускает Celery-задачу для полного парсинга
    """
    task = run_full_parsing_pipeline.delay()
    print(f"✅ Задача запущена: {task.id}")
    return Response({
        "status": "success",
        "message": "Parsing started",
        "task_id": task.id
    })


# --- API: Корневая страница ---
def api_root(request):
    """
    Дружелюбная HTML-страница с ссылками на API
    """
    return HttpResponse("""
    <h1>🚀 Crypto Backend API</h1>
    <p>Доступные эндпоинты:</p>
    <ul>
        <li><a href="/admin">Админка Django</a></li>
        <li><a href="/api/coins/">Список монет</a></li>
        <li><a href="/api/tokenomics-detailed/">Детали токеномики</a></li>
        <li><a href="/api/trigger-parsing/" target="_blank">Запустить парсинг</a></li>
    </ul>
    """)