# Runtime Performance Benchmark

Status: **PASS**

The benchmark uses a fixed number of concurrent candidates. It characterizes event-volume scaling and does not establish scaling to an unbounded number of candidates.

| Events | Median replay (s) | Median total (s) | Peak MiB | State bytes |
|---:|---:|---:|---:|---:|
| 100 | 0.000758 | 0.006019 | 0.15 | 24729 |
| 1000 | 0.005678 | 0.052658 | 1.31 | 226329 |
| 10000 | 0.055061 | 0.570081 | 13.15 | 2242329 |
| 100000 | 0.582241 | 6.378369 | 130.20 | 22402329 |
