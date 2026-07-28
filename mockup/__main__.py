"""python -m mockup entry.

  python -m mockup              # stream + SVG snapshots
  python -m mockup.capture      # PNG evidence for visual QA
  python -m mockup.capture --html
"""

from .run import main

raise SystemExit(main())
