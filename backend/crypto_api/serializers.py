# backend/crypto_api/serializers.py
from rest_framework import serializers
from .models import UpcomingCrypto

class UpcomingCryptoSerializer(serializers.ModelSerializer):
    tokenomics = serializers.JSONField(read_only=True, required=False, allow_null=True)

    class Meta:
        model = UpcomingCrypto
        fields = '__all__'