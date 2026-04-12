# zbx_loganalyzer

Анализатор лога Zabbix Server. Поддерживает два режима: извлечение блоков профилирования и агрегация времени выполнения LLD-правил.

## Использование

```
python3 zbx_loganalyzer.py --mode <profiling|lld> [options]
```

## Параметры

| Параметр | Описание | По умолчанию |
|---|---|---|
| `--mode` | Режим работы: `profiling` или `lld` | обязательный |
| `--log` | Путь к файлу лога | `/var/log/zabbix/zabbix_server.log` |
| `--pid` | Фильтр по PID процесса | все процессы |
| `--after` | Показывать записи после даты/времени (`YYYY-MM-DD HH:MM:SS`) | — |
| `--before` | Показывать записи до даты/времени (`YYYY-MM-DD HH:MM:SS`) | — |
| `--top N` | (только `lld`) Показать топ N правил по суммарному времени; `0` — все | `10` |

## Режимы

**`profiling`** — извлекает и выводит блоки строк `=== Profiling statistics` из лога.

**`lld`** — вычисляет для каждого LLD-правила количество запусков, суммарное, среднее и максимальное время выполнения. Выводит таблицу, отсортированную по суммарному времени.

## Примеры

```bash
# Блоки профилирования за конкретный час
python3 zbx_loganalyzer.py --mode profiling \
    --after "2026-04-12 10:00:00" --before "2026-04-12 11:00:00"

# Топ-20 медленных LLD-правил
python3 zbx_loganalyzer.py --mode lld --top 20

# LLD по конкретному PID, все правила
python3 zbx_loganalyzer.py --mode lld --pid 12345 --top 0

# Нестандартный путь к логу
python3 zbx_loganalyzer.py --mode profiling --log /opt/zabbix/zabbix_server.log
```
