# backend/crypto_api/management/commands/run_parsers.py
from django.core.management.base import BaseCommand
from crypto_api.parsers.upcoming import main as run_upcoming
from crypto_api.parsers.investors import main as run_investors
from crypto_api.parsers.launchpads import main as run_launchpads
from crypto_api.parsers.tokenomics import main as run_tokenomics
from crypto_api.parsers.historical_parser import main as run_historical  # ← НОВАЯ СТРОКА

class Command(BaseCommand):
    help = 'Запускает все парсеры: upcoming → investors → launchpads → tokenomics → historical'

    def handle(self, *args, **options):
        self.stdout.write("🚀 ЗАПУСК ПОЛНОГО ПАЙПЛАЙНА\n" + "=" * 60)

        self.stdout.write("\n1️⃣ Парсинг upcoming-проектов...")
        try:
            run_upcoming()
            self.stdout.write(self.style.SUCCESS("✅ Upcoming-данные сохранены"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Ошибка: {e}"))

        self.stdout.write("\n2️⃣ Парсинг инвесторов...")
        try:
            run_investors()
            self.stdout.write(self.style.SUCCESS("✅ Инвесторы обновлены"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Ошибка: {e}"))

        self.stdout.write("\n3️⃣ Парсинг launchpad-платформ...")
        try:
            run_launchpads()
            self.stdout.write(self.style.SUCCESS("✅ Launchpad-платформы обновлены"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Ошибка: {e}"))

        self.stdout.write("\n4️⃣ Парсинг токеномики...")
        try:
            run_tokenomics()
            self.stdout.write(self.style.SUCCESS("✅ Токеномика сохранена"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Ошибка: {e}"))

        self.stdout.write("\n5️⃣ Парсинг исторических данных (OHLC)...")
        try:
            run_historical()
            self.stdout.write(self.style.SUCCESS("✅ Исторические данные сохранены"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Ошибка: {e}"))

        self.stdout.write("\n" + "✅ ПАЙПЛАЙН ЗАВЕРШЁН\n" + "=" * 60)