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
    """
    Возвращает детали монеты по ID, включая токеномику из отдельной таблицы
    """
    queryset = UpcomingCrypto.objects.all()
    serializer_class = UpcomingCryptoSerializer
    lookup_field = 'id'

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        data = self.get_serializer(instance).data

        # Добавляем токеномику из таблицы cryptorank_tokenomics
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT tokenomics FROM cryptorank_tokenomics WHERE project_name = %s",
                [instance.project_name]
            )
            row = cursor.fetchone()
            if row:
                # Если tokenomics строка — парсим
                tokenomics_data = row[0]
                if isinstance(tokenomics_data, str):
                    import json
                    try:
                        tokenomics_data = json.loads(tokenomics_data)
                    except:
                        tokenomics_data = None
                data['tokenomics'] = tokenomics_data
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


# --- API: OHLC (чтение из ohlc_<symbol>) ---
class OHLCDataView(generics.GenericAPIView):
    """
    Возвращает OHLC-данные из таблицы ohlc_<symbol>
    Использует колонку `date`, а не `timestamp`
    """

    def get(self, request, symbol):
        symbol_lower = symbol.strip().lower()
        table_name = f"ohlc_{symbol_lower}"

        with connection.cursor() as cursor:
            # Проверяем, существует ли таблица
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = %s
                );
            """, [table_name])

            if not cursor.fetchone()[0]:
                return Response({
                    "symbol": symbol.upper(),
                    "data": []
                })

            # Читаем данные, конвертируя date в строку
            cursor.execute(f"""
                SELECT 
                    date::text as date,
                    open_price,
                    high_price,
                    low_price,
                    close_price,
                    volume_usd as volume,
                    change_percent,
                    market_cap
                FROM {table_name}
                ORDER BY date ASC
            """)

            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            data = [dict(zip(columns, row)) for row in rows]

        return Response({
            "symbol": symbol.upper(),
            "data": data
        })


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