"""Static local project check; does not import app or access serial ports."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
required = ['mint_follower_demo/app.py', 'mint_follower_demo/SECURITY.md',
            'mint_follower_demo/tools/export_action_to_ros2.py',
            'workspaces/so101_ws/src/so101_bringup/package.xml',
            'workspaces/so101_ws/mes_backend/pom.xml',
            'so101_gz_scene/launch_live_follower_rviz.launch.py']
failures = []
for name in required:
    path = ROOT / name
    if not path.is_file() or not path.resolve().is_relative_to(ROOT):
        failures.append(name)
for path in [ROOT / 'mint_follower_demo/app.py', *ROOT.glob('so101_gz_scene/*.py')]:
    try:
        ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    except (OSError, SyntaxError) as error:
        failures.append(str(error))
for failure in failures:
    print(f'FAIL {failure}')
print(f'Offline SO101 layout: {len(failures)} failures; no runtime/hardware acceptance')
raise SystemExit(bool(failures))
