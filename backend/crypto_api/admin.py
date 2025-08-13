# crypto_api/admin.py

from django.contrib import admin
from .models import UpcomingCrypto

@admin.register(UpcomingCrypto)
class UpcomingCryptoAdmin(admin.ModelAdmin):
    list_display = ('project_name', 'launch_date', 'moni_score')
    search_fields = ('project_name', 'project_symbol')

    def has_module_permission(self, request):
        return True

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        my_urls = [
            path('run-parsers/', self.run_parsers),
        ]
        return my_urls + urls

    def run_parsers(self, request):
        # Здесь можно вызвать твои парсеры
        print("Запуск парсеров...")
        # Например:
        # from .management.commands.run_parsers import main
        # main()
        self.message_user(request, "Парсеры запущены!")
        return redirect('/admin/')