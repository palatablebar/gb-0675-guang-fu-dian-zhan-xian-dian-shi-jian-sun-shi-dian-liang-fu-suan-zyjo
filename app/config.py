from pathlib import Path
import json, os
ROOT = Path(__file__).resolve().parents[1]
META = json.loads((ROOT / 'app/project.json').read_text())
MODULES = META['keys']
RULE_VERSION = '2026.11.20-r1'
DB_PATH = os.environ.get('DB_PATH', '/data/workbench.sqlite')
SENTINELS = {'', '-', 'N/A', 'NULL', '未知'}
MAX_BYTES = 2_000_000
