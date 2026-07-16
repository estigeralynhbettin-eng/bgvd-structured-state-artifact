# Runtime Performance Benchmark

Status: **PASS**

The benchmark uses a fixed number of concurrent candidates. It characterizes event-volume scaling and does not establish scaling to an unbounded number of candidates.

| Events | Median replay (s) | Median total (s) | Peak MiB | State bytes |
|---:|---:|---:|---:|---:|
| 100 | 0.000726 | 0.006284 | 0.15 | 24729 |
| 1000 | 0.005263 | 0.050503 | 1.31 | 226329 |
| 10000 | 0.052356 | 0.558827 | 13.15 | 2242329 |
| 100000 | 1.337475 | 13.300971 | 130.20 | 22402329 |
