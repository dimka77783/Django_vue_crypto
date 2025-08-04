from django.contrib import admin
from .models import UpcomingCrypto

@admin.register(UpcomingCrypto)
class UpcomingCryptoAdmin(admin.ModelAdmin):
    list_display = ('project_name', 'project_symbol', 'launch_date', 'initial_cap')
    list_filter = ('launch_date', 'is_active')
    search_fields = ('project_name', 'project_symbol')