# CyberKun's challenge solutions

## a97

In `canon#0`, the user received five units of `KB-200`. The inventory log records the shipment taking stock from 40 to 45, then an automatic retry applying the same five units again. The subsequent `get_stock` call read 50, which the agent reported to the user.

**Failing check:** `T1-015`. The recorded `adjust_stock` result has `before=40`, `delta=5`, and `after=50`.

**Correction:** Once the first adjustment committed, the retry should have returned that adjustment's original result without writing again. The on-hand count for this shipment should have been 45.
