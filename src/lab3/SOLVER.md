# Решатель судоку: заметки по проекту

Машина: Python 3.14.8, Linux 7.3.0 (CachyOS, x86_64). Время: минимум из 5 прогонов, `time.perf_counter`.

## Архитектура
- `Board`: плоские int-структуры (`states`, `digit_cells`, `placed`, `buckets`, `empty_mask`,
  `zobrist`, `dirty`, `pending`). `copy()` = срезы списков. `place`/`eliminate` возвращают False
  при противоречии, такую доску выбрасывают.
- `propagate`: singles событийно (`buckets[1]`, `pending`), паттерны только по «грязным» регионам.
- `search`: DFS по одной клетке, проверка Zobrist в начале узла.

## Решения и отступления от кода студента
1. `Cell` как объект заменён int-состояниями; `Cell` остался неизменяемым снимком (C2, C6).
2. `Hash` и numpy убраны: таблица 81x10 из `random.Random(47)`, хэш это int (Z1–Z4).
3. `Region` статичен: маски и таблицы соседей. Счётчики считаются выражением над масками.
4. Куча клеток заменена `buckets[c]`, куча областей заменена `pending` (H2). `heap.py` починен, не используется.
5. `set_cell` разделён на `place` и `eliminate` с проверками и bool.
6. Четыре индикатора сведены к `find_subset_eliminations` на двух видах (клетки, цифры); hidden threes
   идут по объединению масок (P3).
7. Включены pointing/claiming; X-wing не реализован.
8. Ветвление по одной клетке (P4); схема студента доступна флагом `branch_all_cells`.
9. Хэш проверяется в узле ветвления, а не после каждой вписанной цифры (P5).
10. Базовый случай «нет свободных клеток» и ловля противоречия в области (P1, P2).

## Замеры
### База: solve_naive (23 пазла: puzzle1–3 + 20 сгенерированных)
puzzle2 и gen7 упёрлись в лимит 100000 шагов; puzzle1 4209 узлов, 14 мс; gen8 92322 узла, 328 мс.

### singles, лёгкий набор (23 пазла)
1–10 узлов на пазл, 0.17–0.32 мс; memo_hits = 0.

### Паттерны, 143 пазла (23 лёгких + трудные из puzzles/)
| конфигурация | сумма, мс | узлов | худший |
|---|---|---|---|
| singles | 477.7 | 11661 | hard_2#17 44.2 мс |
| +pairs | 487.8 | 5670 | hard_2#5 53.9 мс |
| +threes | 644.9 | 5268 | hard_2#5 72.5 мс |
| +pointing | 819.5 | 4777 | hard_2#13 218.4 мс |
| pointing only | 597.7 | 7624 | hard_2#13 141.1 мс |

Вывод: паттерны уменьшают число узлов (до 2.4 раза), но цена узла растёт так же быстро;
по времени выигрыша нет. Пары дают +2% (шум), поэтому по правилу «<10% в пользу простого»
по умолчанию singles.

### Стратегии, memo, branch_all_cells
_Вставить вывод `python bench.py --strategies`, `python bench.py --all-cells --limit 10`._

## Zobrist и memo
При ветвлении по одной клетке ветви различаются значением ветвящейся клетки, поэтому одинаковые
позиции почти не встречаются (в присланных таблицах memo_hits = 0). Механизм оставлен переключаемым
и покрыт тестами. Он полезен при переборе нескольких клеток (`branch_all_cells`) и при подсчёте
числа решений. Коллизии 64-битного хэша маловероятны, но не исключены.

## Соответствие псевдокода студента функциям
| псевдокод | функция |
|---|---|
| solve(Board): видели hash | `solver.search`, начало узла |
| top кучи заметок == 0 | `Board.eliminate` возвращает False (нет заметок) |
| obvious_singles | `solver.obvious_singles` (`buckets[1]`) |
| hidden_singles | `solver.hidden_singles` (`Board.pending`) |
| obvious/hidden pairs, threes | `patterns.find_subset_eliminations` на видах `cell_items`/`digit_items` |
| pointing_pairs | `patterns.intersection_targets` |
| x_wing | не реализован |
| solve_dfs | `solver.search` (одна клетка; `branch_all_cells`: несколько) |
| стратегии Cell | `select_cell_mrv`, `select_cell_mrv_degree`, `select_cell_digit_min` |
| стратегии Branch | `branch_asc`, `branch_rare_first` |
| modify(x, y, d) | `Board.place` / `Board.eliminate` |

## Не сделано
Приложение задания (threading/multiprocessing, режим `--parallel`) пропущено.