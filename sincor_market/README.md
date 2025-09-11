# SINCOR Market Pack v2 - Dual Mode Edition

**What this is:** Complete drop-in scaffold for the 43-agent constellation with hybrid STRUCTURED/SWARM execution modes:

- 📊 **Canonical skill taxonomy** (16-dimensional)
- 🤖 **43-agent registry** across 6 guilds (S*, O*, P*, N*, Q*, M*)
- 🏛️ **Vickrey-style task market** (score to select, second-price pay)
- 🤝 **Atomic handoffs** (ack or requeue with 5s timeout)
- 🧠 **Dual execution modes**: STRUCTURED lattice vs SWARM liquid intelligence
- 👑 **God Mode controls** for root-level overrides and emergency operations
- 📈 **Overlap/gap audit** utilities for specialization tuning

## Key Features

### Dual Execution Modes
- **STRUCTURED Mode**: Traditional auction → assignment → handoff → QA pipeline
- **SWARM Mode**: Ephemeral pods (5-15 micro-agents) with multi-route consensus
- **Intelligent routing** based on novelty, ambiguity, time pressure, and safety signals

### God Mode Operations  
- `force_mode(task, mode)` - Override execution mode
- `seize(task)` - Emergency stop with checkpointing
- `pause(guild|market)` - Drain and park operations
- `emergency_write(target)` - Temporary external write allowance
- Complete audit trail with blast-radius controls

## Quickstart

```bash
# Run dual-mode simulation
python scripts/simulate.py

# God Mode operations (root access only)
python scripts/root.py force_mode TT-123 SWARM
python scripts/root.py seize TT-456
python scripts/root.py audit --limit 10
```

## Files

### Core Engine
- `config/taxonomy.yaml` — 16-dimensional skill space
- `config/agents.yaml` — 43 agents with guild assignments and skill triads
- `config/mode_policy.yaml` — STRUCTURED/SWARM routing policy
- `config/rbac.yaml` — God Mode permissions and audit settings

### Python Modules
- `src/sincor/agents.py` — Agent model + registry loader
- `src/sincor/task.py` — TaskToken + AuctionSpec + Lot definitions
- `src/sincor/auction.py` — Vickrey auction engine with diversity bonuses
- `src/sincor/handoff.py` — Atomic handoff manager (5s ack timeout)
- `src/sincor/mode_select.py` — Signal-based mode selection logic
- `src/sincor/swarm.py` — SwarmAdapter for liquid intelligence pods
- `src/sincor/god_mode.py` — Root access controller with RBAC
- `src/sincor/audit.py` — Overlap/gap analysis utilities

### Scripts
- `scripts/simulate.py` — End-to-end dual-mode demo
- `scripts/root.py` — God Mode CLI (requires root principal)

## Mode Selection Logic

The system automatically routes lots based on computed signals:

- **Novelty**: Embedding distance vs corpus (unseen patterns)
- **Ambiguity**: Spec entropy and conflicting constraints  
- **Time Pressure**: Deadline tightness vs historical P95
- **Externality**: Vendor/API unknowns and ToS risks
- **Safety Risk**: PII, external writes, legal exposure

**SWARM mode** excels at:
- Novel/ambiguous problems requiring exploration
- Creative synthesis and multi-perspective analysis  
- Rapid prototyping with acceptable fault tolerance

**STRUCTURED mode** handles:
- Well-defined specifications with clear acceptance criteria
- High-stakes operations requiring audit trails
- Time-critical delivery with predictable SLOs

## Safety Rails

- Safety risk ≥ 0.5 → **always STRUCTURED**
- PII, external writes, legal holds → **forbid SWARM**
- God Mode cooldowns and blast-radius limits
- Dual audit logging (immutable + human-readable)

## Agent Guild Structure

- **INTAKE (S1-S8)**: Discovery, triage, retrieval, enrichment
- **ORCH (O1-O6)**: Decomposition, routing, budgets, dependencies  
- **PROD (P1-P18)**: Makers - code, design, data, copy, analytics
- **NEG (N1-N4)**: Vendor APIs, pricing, ToS risk, rate limits
- **QA (Q1-Q4)**: Spec conformance, tests, red-team checks
- **OPS (M1-M3)**: Versioning, audit, budgets, policy, observability

## Tuning Knobs

- `config/mode_policy.yaml` — Adjust routing weights and thresholds
- `config/agents.yaml` — Modify costs, SLOs, and skill distributions
- `scripts/simulate.py` — Test with your real workload patterns

## Production Integration

1. **Drop in real tasks**: Edit `scripts/simulate.py` lots to mirror your pipelines
2. **Run and inspect**: Monitor winner selection, pay curves, and ack outcomes  
3. **Adjust diversity λ**: Tune 0.05-0.15 until bid spreads stabilize
4. **Audit gaps**: Use `audit.gap_suggestions()` for capacity planning

## God Mode Security

- **RBAC**: Role-based access with principal authentication
- **Cooldowns**: Prevent rapid-fire emergency actions
- **Blast radius**: Limit affected lots per minute
- **Dual logging**: Immutable ledger + redacted event log
- **Authorization**: Multi-factor checks for high-impact operations

---

**Next Steps:**
1. Run `python scripts/simulate.py` to see dual-mode execution
2. Examine bid distributions and confidence scores
3. Tune `mode_policy.yaml` weights for your domain
4. Integrate with your existing SINCOR deployment

The system maintains backward compatibility - existing STRUCTURED workflows continue unchanged while gaining SWARM capabilities for complex/novel tasks.