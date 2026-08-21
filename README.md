# Середовище практичних робіт IoT та Big Data

## Запуск

1. Встановіть Docker Desktop або Docker Engine із Docker Compose.
2. Відкрийте термінал у каталозі проєкту.
3. Виконайте:

```bash
docker compose up --build
```

4. Відкрийте у браузері:

```text
http://localhost:8888/lab?token=iot-bigdata
```

## Перевірка середовища

В іншому вікні термінала виконайте:

```bash
docker compose exec lab python scripts/check_environment.py
```

Усі перевірки мають завершитися повідомленням:

```text
Середовище готове до роботи.
```

## Зупинка

```bash
docker compose down
```

## Каталоги

- `data/input` — початкові дані, доступні лише для читання;
- `data/working` — проміжні й оброблені дані;
- `notebooks` — ноутбуки практичних робіт;
- `results` — результати для перевірки;
- `src` — повторно використовуваний Python-код.

## Структура результатів

Для кожної практичної роботи використовується окремий підкаталог:

```text
results/practical_01/
results/practical_02/
results/practical_03/
results/practical_04/
results/practical_05/
```

Після ПР2 очищений файл очікується тут:

```text
results/practical_02/clean_iot_events.parquet
```

Результати ПР3 очікуються тут:

```text
results/practical_03/
```

Результати ПР4 очікуються тут:

```text
results/practical_04/device_behavior_baseline.csv
results/practical_04/hourly_anomaly_scores.csv
results/practical_04/detection_findings.csv
results/practical_04/practical_04_summary.json
```

Результати ПР5 очікуються тут:

```text
results/practical_05/incident_mart.csv
results/practical_05/device_risk_summary.csv
results/practical_05/scenario_risk_summary.csv
results/practical_05/location_risk_summary.csv
results/practical_05/top_incidents.csv
results/practical_05/practical_05_summary.json
results/practical_05/findings_by_scenario.png
results/practical_05/severity_distribution.png
results/practical_05/top_risky_devices.png
results/practical_05/risk_by_location.png
```

Базова перевірка результатів ПР5:

```bash
docker compose exec lab python scripts/check_practical_05_outputs.py
```

## Linux: проблема з правами доступу

За замовчуванням контейнер використовує UID/GID `1000:1000`. Якщо ваші значення інші, виконайте:

```bash
id -u
id -g
```

і замініть `STUDENT_UID` та `STUDENT_GID` у файлі `.env`, після чого повторіть збірку:

```bash
docker compose build --no-cache
docker compose up
```
