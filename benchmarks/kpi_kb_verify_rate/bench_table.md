# KPI-KB-VERIFY-RATE ref vs got（程序化生成，勿手改）

| tier | case | ref (num/den/current) | got (num/den/current) | abs err | pass |
|---|---|---|---|---|---|
| A | mixed-10ko | 1/8/0.125 | 1/8/0.125 | 0 | PASS |
| A | empty-db | 0/0/None | 0/0/None | 0 | PASS |
| A | two-of-three | 2/3/0.6666666666666666 | 2/3/0.6666666666666666 | 0 | PASS |
| B | mixed-10ko | 1/8/0.125 | 1/8/0.125 | 0.0 | PASS |
| B | empty-db | 0/0/None | 0/0/None | None | PASS |
| B | two-of-three | 2/3/0.6666666666666666 | 2/3/0.6666666666666666 | 0.0 | PASS |
| C | live | 0/5338 | 0/5338 |  | PASS |
