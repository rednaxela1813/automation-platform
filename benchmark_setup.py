"""
Benchmark: скачивает тестовые PDF из invoice2data и прогоняет твой парсер.

Запуск (из корня проекта automation-platform):
    pip install invoice2data --quiet
    python benchmark_setup.py

Что делает:
  1. Скачивает ~15 реальных тестовых PDF из invoice2data (GitHub)
  2. Прогоняет каждый через твой PdfInvoiceParser
  3. Выводит таблицу с результатами: что нашёл, что не нашёл
  4. Сохраняет детальный отчёт в benchmark_results.json
"""

import json
import sys
import urllib.request
from pathlib import Path

# ── 1. Тестовые PDF из invoice2data ──────────────────────────────────────────
# Эти файлы лежат в открытом доступе на GitHub (raw)
BASE = "https://raw.githubusercontent.com/invoice-x/invoice2data/master/src/invoice2data/test/pdfs"

TEST_PDFS = [
    "osx-invoice.pdf",
    "solarworld-invoice.pdf",
    "aws-test-invoice.pdf",
    "energy-invoice.pdf",
    "free-mobile-invoice.pdf",
    "google-invoice.pdf",
    "mindfct-invoice.pdf",
    "netcologne-invoice.pdf",
    "nx-invoice.pdf",
    "o2-invoice.pdf",
    "orange-invoice.pdf",
    "sfy-invoice.pdf",
    "strato-invoice.pdf",
    "telepass-invoice.pdf",
]

# ── 2. Папка для загрузки ─────────────────────────────────────────────────────
FIXTURES_DIR = Path("tests/benchmark/fixtures")
FIXTURES_DIR.mkdir(parents=True, exist_ok=True)


def download_pdfs():
    """Скачать PDF-файлы, если их ещё нет локально."""
    print("📥 Скачиваю тестовые PDF из invoice2data...\n")
    downloaded, skipped, failed = [], [], []

    for name in TEST_PDFS:
        dest = FIXTURES_DIR / name
        if dest.exists():
            skipped.append(name)
            print(f"  ⏭  уже есть: {name}")
            continue
        url = f"{BASE}/{name}"
        try:
            urllib.request.urlretrieve(url, dest)
            downloaded.append(name)
            print(f"  ✅ скачан:   {name}")
        except Exception as e:
            failed.append(name)
            print(f"  ❌ ошибка:   {name} → {e}")

    print(f"\nСкачано: {len(downloaded)}, уже были: {len(skipped)}, ошибки: {len(failed)}\n")
    return failed


# ── 3. Запуск парсера ─────────────────────────────────────────────────────────
def run_parser_on_pdf(parser, pdf_path: Path) -> dict:
    """Запустить парсер на одном файле и вернуть словарь с результатом."""
    try:
        result = parser.parse_invoice(pdf_path)
        inv = result.invoice
        return {
            "file": pdf_path.name,
            "success": result.success,
            "errors": result.errors,
            "invoice_number": inv.invoice_number if inv else None,
            "invoice_date": str(inv.invoice_date) if inv else None,
            "amount": str(inv.amount) if inv else None,
            "currency": inv.currency if inv else None,
            "partner_id": inv.partner_id if inv else None,
        }
    except Exception as e:
        return {
            "file": pdf_path.name,
            "success": False,
            "errors": [f"Исключение: {e}"],
            "invoice_number": None,
            "invoice_date": None,
            "amount": None,
            "currency": None,
            "partner_id": None,
        }


def run_benchmark():
    # Импортируем парсер из твоего проекта
    try:
        from automation.adapters.pdf_parser import PdfInvoiceParser
    except ImportError:
        print("❌ Не удалось импортировать PdfInvoiceParser.")
        print("   Запускай скрипт из корня проекта (там где src/) командой:")
        print("   PYTHONPATH=src python benchmark_setup.py\n")
        sys.exit(1)

    parser = PdfInvoiceParser()
    pdf_files = sorted(FIXTURES_DIR.glob("*.pdf"))

    if not pdf_files:
        print("❌ PDF-файлы не найдены в", FIXTURES_DIR)
        sys.exit(1)

    print(f"🔍 Прогоняю парсер на {len(pdf_files)} файлах...\n")
    results = []
    for pdf in pdf_files:
        r = run_parser_on_pdf(parser, pdf)
        results.append(r)

    return results


# ── 4. Отчёт ─────────────────────────────────────────────────────────────────
FIELDS = ["invoice_number", "amount", "currency", "invoice_date"]
COL_W = 22  # ширина колонки


def print_report(results: list):
    total = len(results)
    passed = sum(1 for r in results if r["success"])

    # Заголовок
    header = f"{'Файл':<28}" + "".join(f"{f:<{COL_W}}" for f in FIELDS) + "OK?"
    print("=" * len(header))
    print(header)
    print("=" * len(header))

    for r in results:
        row = f"{r['file']:<28}"
        for field in FIELDS:
            val = r[field] or "—"
            row += f"{str(val):<{COL_W}}"
        row += "✅" if r["success"] else "❌"
        print(row)

    print("=" * len(header))
    print(f"\nИтого: {passed}/{total} успешно распознано  ({100*passed//total}%)\n")

    # Статистика по полям
    print("Статистика по полям:")
    for field in FIELDS:
        found = sum(1 for r in results if r[field] is not None)
        print(f"  {field:<20} найдено в {found}/{total} файлах")

    # Что не сработало
    failures = [r for r in results if not r["success"]]
    if failures:
        print(f"\n⚠️  Не распознано ({len(failures)} файлов):")
        for r in failures:
            errs = "; ".join(r["errors"]) if r["errors"] else "нет деталей"
            print(f"  • {r['file']}: {errs}")


def save_json(results: list):
    out = Path("benchmark_results.json")
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"\n💾 Детальные результаты сохранены в: {out.resolve()}\n")


# ── 5. Точка входа ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    failed_downloads = download_pdfs()
    results = run_benchmark()
    print_report(results)
    save_json(results)

    if failed_downloads:
        print(f"⚠️  Не скачались {len(failed_downloads)} файлов: {failed_downloads}")
        print("   Это нормально — некоторые имена могли измениться в репо.\n")