# HDM overhead measurement

Status: **Implemented (pure local assessment); Real measurement required**

`hdm.domain.performance_measurement` assesses one caller-supplied timing sample
from existing read-only HDM work. It reuses the shared telemetry admission
contract, accepts only player-diagnostics consumers, and requires benchmarked
cost within the existing one-tenth interval budget.

The sample contains only monotonic timing and snapshot/optional-observer cost.
Its public report contains a categorical result, public code, an `unknown`
game-impact assessment, and total HDM cost only when observed. It carries no
game title, AppID, account, path, device identity, or observation timestamp.

Running or unknown games defer measurement. Unbenchmarked, over-budget, stale,
or unavailable optional-observer evidence is explicit and fail-closed. An
observed cost is diagnostic evidence only: it never proves zero game impact or
authorizes Auto TDP, process intervention, tuning, collection scheduling, or
device action.

There is no collector, poller, persistence, UI delivery, or hardware evidence
in this slice. A supported-profile measurement must use existing HDM work or a
separately reviewed bounded read-only source and record actual game-impact
evidence before any operational conclusion.
