# backend/crypto_api/serializers.py
from rest_framework import serializers
from .models import UpcomingCrypto

class UpcomingCryptoSerializer(serializers.ModelSerializer):
    class Meta:
        model = UpcomingCrypto
        fields = '__all__'