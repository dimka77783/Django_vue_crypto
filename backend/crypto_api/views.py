# backend/crypto_api/views.py
from rest_framework import generics
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import HttpResponse
from django.core import management
import threading
import json
import psycopg2
from django.conf import settings
import psycopg2.extras  # Для RealDictCursor
import re

# ✅ ОБЯЗАТЕЛЬНЫЕ ИМПОРТЫ
from .models import UpcomingCrypto
from .serializers import UpcomingCryptoSerializer


# --- 1. Список и детали монет ---
class CryptoListAPIView(generics.ListAPIView):
    """
    GET /api/coins/ — список всех монет
    """
    queryset = UpcomingCrypto.objects.all()
    serializer_class = UpcomingCryptoSerializer


class CryptoDetailAPIView(generics.RetrieveAPIView):
    """
    GET /api/coins/<id>/ — детали одной монеты
    """
    queryset = UpcomingCrypto.objects.all()
    serializer_class = UpcomingCryptoSerializer


# --- 2. Запуск парсинга ---
@api_view(['POST'])
def trigger_parsing(request):
    """
    POST /api/trigger-parsing/ — запускает run_parsers
    """
    def run():
        try:
            management.call_command('run_parsers')
        except Exception as e:
            print(f"❌ Ошибка при запуске парсинга: {e}")

    thread = threading.Thread(target=run)
    thread.start()
    return Response({
        "status": "success",
        "message": "Parsing started"
    })


# --- 3. Токеномика (из таблицы cryptorank_tokenomics) ---
class TokenomicsDetailedView(generics.GenericAPIView):
    """
    GET /api/tokenomics-detailed/ — все данные токеномики
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

            # Формируем список: раскрываем JSONB поле `tokenomics`
            data = []
            for row in rows:
                project_name, tokenomics_json = row
                if isinstance(tokenomics_json, dict):
                    tokenomics_json['project_name'] = project_name
                    data.append(tokenomics_json)
                else:
                    # Если данные не в JSON, попробуем распарсить
                    try:
                        parsed = json.loads(tokenomics_json)
                        parsed['project_name'] = project_name
                        data.append(parsed)
                    except:
                        data.append({
                            'project_name': project_name,
                            'error': 'Invalid tokenomics data',
                            'raw': str(tokenomics_json)
                        })

            return Response(data)

        except Exception as e:
            return Response({
                "error": f"Database error: {str(e)}"
            }, status=500)


# --- 4. OHLC данные по символу ---
def normalize_symbol(symbol):
    """Преобразует символ в формат имени таблицы"""
    # Убираем всё, кроме букв и цифр, заменяем пробелы и дефисы на _
    normalized = re.sub(r'[^a-zA-Z0-9]+', '_', symbol.strip().lower())
    # Убираем двойные подчёркивания и ведущие/конечные _
    normalized = re.sub(r'_+', '_', normalized).strip('_')
    return normalized


class OHLCDataView(generics.GenericAPIView):
    """
    GET /api/ohlc/<symbol>/ — исторические данные (Open, High, Low, Close и т.д.)
    Пример: /api/ohlc/pvt/
    """
    def get(self, request, symbol):
        # Нормализуем символ
        table_name = f"ohlc_{normalize_symbol(symbol)}"
        print(f"🔍 Поиск таблицы: {table_name}")

        try:
            # Подключаемся к БД
            conn = psycopg2.connect(
                host=settings.DATABASES['default']['HOST'],
                port=settings.DATABASES['default']['PORT'],
                database=settings.DATABASES['default']['NAME'],
                user=settings.DATABASES['default']['USER'],
                password=settings.DATABASES['default']['PASSWORD']
            )

            # Используем RealDictCursor для получения словарей
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Проверяем, существует ли таблица (без учёта регистра)
            cursor.execute("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname='public' AND LOWER(tablename) = %s;
            """, (table_name,))
            table_check = cursor.fetchone()

            if not table_check:
                print(f"❌ Таблица {table_name} не найдена")
                return Response([], status=200)

            # Читаем данные из таблицы
            cursor.execute(f"""
                SELECT 
                    date, open_price, high_price, low_price, med_price,
                    close_price, change_percent, volume_usd, change_volume_percent, market_cap
                FROM {table_name}
                ORDER BY date ASC;
            """)
            rows = cursor.fetchall()
            conn.close()

            # Преобразуем результат в список словарей
            data = []
            for row in rows:
                item = {}
                for key, value in row.items():
                    # Преобразуем Decimal, datetime и None в JSON-совместимые типы
                    if isinstance(value, (int, float)):
                        item[key] = float(value) if isinstance(value, float) else value
                    elif isinstance(value, str):
                        item[key] = value
                    elif value is None:
                        item[key] = None
                    else:
                        item[key] = str(value)  # Остальное — как строки
                data.append(item)

            print(f"✅ Успешно загружено {len(data)} строк из {table_name}")
            return Response(data)

        except Exception as e:
            print(f"❌ Ошибка при загрузке OHLC: {e}")
            return Response({"error": f"Database error: {str(e)}"}, status=500)


# --- 5. Корневой эндпоинт (опционально) ---
def api_root(request):
    """
    GET /api/ — простая HTML-страница с ссылками
    """
    return HttpResponse("""
    <h1>🚀 Crypto Backend API</h1>
    <p>Доступные эндпоинты:</p>
    <ul>
        <li><a href="/admin">Админка</a></li>
        <li><a href="/api/coins/">Список монет</a></li>
        <li><a href="/api/tokenomics-detailed/">Токеномика</a></li>
        <li><a href="/api/trigger-parsing/" target="_blank">Запустить полный парсинг</a></li>
    </ul>
    """)