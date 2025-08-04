# backend/crypto_api/views.py

from django.http import HttpResponse
from django.core import management
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import generics

from .models import UpcomingCrypto
from .serializers import UpcomingCryptoSerializer

# --- НОВОЕ: API для списка монет ---
class CryptoListAPIView(generics.ListAPIView):
    queryset = UpcomingCrypto.objects.all()
    serializer_class = UpcomingCryptoSerializer

# --- Существующее: запуск парсинга ---
@api_view(['POST'])
def trigger_parsing(request):
    def run():
        management.call_command('run_parsers')
    import threading
    thread = threading.Thread(target=run)
    thread.start()
    return Response({"status": "success", "message": "Parsing started"})

# --- Опционально: корневая страница ---
def api_root(request):
    return HttpResponse("""
    <h1>🚀 Crypto Backend API</h1>
    <p>Доступные эндпоинты:</p>
    <ul>
        <li><a href="/admin">Админка</a></li>
        <li><a href="/api/coins/">Список монет</a></li>
        <li><a href="/api/trigger-parsing/" target="_blank">Запустить парсинг</a></li>
    </ul>
    """)