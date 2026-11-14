# NASA OSDR environmental imports

Place CSV exports from the [NASA OSDR Environmental Data Application](https://visualization.osdr.nasa.gov/eda/) here.

AEGIS does **not** call a live NASA API. Import via:

```bash
curl -X POST http://127.0.0.1:8000/api/environment/import \
  -F "file=@your_osdr_export.csv"
```

or

```bash
curl -X POST http://127.0.0.1:8000/api/environment/import-local
```

Supported columns (flexible aliases): `co2` / `co2_ppm`, `temperature` / `temp_c`, `humidity` / `rh`, optional `mission_day` / `timestamp`.

Until a file is imported, the app uses the synthetic fixture and shows **DEMO DATA — NASA IMPORT NOT LOADED**.
