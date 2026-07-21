"""kimi-atlas benchmark harness — measures the plugin's real output quality AND, uniquely,
the trustworthiness of its verdict (does OK really mean correct?). Pure scoring core
(`bench.scorer`) + thin I/O runner (`bench.runner`) + scorecard (`bench.report`), mirroring
the plugin's own pure-core/hands split."""
