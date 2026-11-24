import sys, sqlite3, pathlib, tempfile, os
sys.path.insert(0, ".")
tmp = pathlib.Path(tempfile.mkdtemp())
db = tmp / "funds.db"
con = sqlite3.connect(db)
con.executescript("""
CREATE TABLE nav (fund_code TEXT, d TEXT, v REAL, adj_v REAL);
INSERT INTO nav VALUES ("510300.SH","2024-01-02",3.411,3.411);
INSERT INTO nav VALUES ("510300.SH","2024-01-03",3.425,3.425);
INSERT INTO nav VALUES ("510300.SH","2024-01-04",3.430,3.430);
CREATE TABLE idx_daily (c TEXT, d TEXT, close REAL);
INSERT INTO idx_daily VALUES ("000300.SH","2024-01-02",3400.1);
INSERT INTO idx_daily VALUES ("000300.SH","2024-01-03",3410.2);
INSERT INTO idx_daily VALUES ("000300.SH","2024-01-04",3405.5);
""")
con.commit()
con.close()
dsn = "sqlite:///" + str(db)
lake_dir = str(tmp / "lake")
cfg = f"""
datasource:
  provider: sql
  dsn: {dsn}
  datasets:
    fund_nav:
      query: >-
        SELECT fund_code, d, v, adj_v FROM nav
        WHERE fund_code = :code AND d >= :start_date_iso AND d <= :end_date_iso ORDER BY d
      column_map: {{fund_code: ts_code, d: nav_date, v: unit_nav, adj_v: adj_nav}}
    index_daily:
      query: >-
        SELECT c, d, close FROM idx_daily
        WHERE c = :code AND d >= :start_date_iso AND d <= :end_date_iso ORDER BY d
      column_map: {{c: ts_code, d: trade_date}}
cache:
  enabled: true
  dir: {lake_dir}
"""
cfg_file = tmp / "config.yaml"
cfg_file.write_text(cfg, encoding="utf-8")
os.environ["FUND_SELECTOR_CONFIG"] = str(cfg_file)

from src.config import load_config
from src.datasource import DataSource
ds = DataSource.from_config(load_config())
nav = ds.fetch("fund_nav", code="510300.SH", start_date="20240101", end_date="20241231")
idx = ds.fetch("index_daily", code="000300.SH", start_date="20240101", end_date="20241231")
print("NAV rows:", len(nav), "| cols:", list(nav.columns), flush=True)
print(nav.to_string(), flush=True)
print("IDX rows:", len(idx), flush=True)
lake = pathlib.Path(lake_dir)
print("cache files:", [str(p.relative_to(lake)) for p in lake.rglob("*.parquet")], flush=True)

import warnings
warnings.filterwarnings("ignore")
from src.data_loader import preprocess_fund_data
pre = preprocess_fund_data(nav)
print("preprocess ok:", len(pre), "rows, cum_nav last =", round(float(pre.cum_nav.iloc[-1]), 4), flush=True)

# DuckDB 离线查询放在子进程里：部分虚拟化 CPU 会因 duckdb 的 SIMD 指令 SIGILL，
# 不应影响主链路验证
import subprocess, sys
glob = str(lake / "fund_nav" / "*.parquet")
probe = (
    "import duckdb,sys;"
    "print(int(duckdb.sql('SELECT COUNT(*) AS n FROM read_parquet(?)',"
    "params=[sys.argv[1]]).to_df().n.iloc[0]))"
)
pp = subprocess.run([sys.executable, "-c", probe, glob], capture_output=True, text=True)
if pp.returncode == 0:
    print("duckdb offline rows:", pp.stdout.strip(), flush=True)
else:
    print("duckdb unavailable in this environment (exit", pp.returncode, ")", flush=True)
assert len(nav) == 3 and len(idx) == 3 and len(pre) == 3
print("SMOKE OK", flush=True)
