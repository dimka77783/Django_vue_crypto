# backend/crypto_api/views.py
from rest_framework import generics
from rest_framework.response import Response
from .models import UpcomingCrypto
from .serializers import UpcomingCryptoSerializer
import json
import psycopg2
from django.conf import settings

# Список и детали монет
class CryptoListAPIView(generics.ListAPIView):
    queryset = UpcomingCrypto.objects.all()
    serializer_class = UpcomingCryptoSerializer

class CryptoDetailAPIView(generics.RetrieveAPIView):
    queryset = UpcomingCrypto.objects.all()
    serializer_class = UpcomingCryptoSerializer

# Токеномика (из вьюшки)
class TokenomicsDetailedView(generics.ListAPIView):
    def get(self, request, *args, **kwargs):
        conn = psycopg2.connect(**settings.DATABASES['default'])
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tokenomics_detailed;")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        data = [dict(zip(columns, row)) for row in rows]
        conn.close()
        return Response(data)

# OHLC данные
class OHLCDataView(generics.GenericAPIView):
    def get(self, request, symbol):
        table_name = f"ohlc_{symbol.lower()}"
        conn = psycopg2.connect(**settings.DATABASES['default'])
        cursor = conn.cursor()
        try:
            cursor.execute(f"SELECT * FROM {table_name} ORDER BY date DESC;")
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            data = [dict(zip(columns, row)) for row in rows]
        except psycopg2.errors.UndefinedTable:
            data = []
        finally:
            conn.close()
        return Response(data)