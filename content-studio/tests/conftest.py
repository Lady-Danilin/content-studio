"""Setup compartido de tests: agrega lib/ al sys.path.

`lib/plan.py` (y otros módulos de lib/) importan sus vecinos como módulos de
top-level, por ejemplo `import studio`, no `from lib import studio`. Eso
funciona cuando lib/ está en el sys.path, que es como corren los comandos y
los otros tests de este repo (ver test_importar.py). pytest, en cambio, sólo
agrega la raíz del repo (por el `python -m pytest`), así que `lib` se resuelve
como paquete pero `studio` dentro de plan.py no. Este conftest agrega lib/
para que ambos estilos de import convivan sin tocar lib/plan.py.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
