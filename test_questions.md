# Test Questions — Data Analyst Agent

Questions with answers checked by hand against `data/crashes.duckdb`.
These are the starting point for the Step 7 evaluation set.

Run any query with:
```powershell
python sql.py "<SQL here>"
```

---

## Q1 — Easy
**Question:** How many fatal crashes were there in Queensland in 2024?

**SQL:**
```sql
SELECT COUNT(*) FROM crashes WHERE crash_year = 2024 AND crash_severity = 'Fatal'
```

**Answer:** 273

**Tests:** Basic filter and count on the main table.

**Notes:** This counts *crashes*, not *deaths*. One fatal crash can kill several people (see Q3).

---

## Q2 — Easy
**Question:** Which local government area had the most crashes in 2024?

**SQL:**
```sql
SELECT loc_local_government_area, COUNT(*) AS n_crashes
FROM crashes
WHERE crash_year = 2024
GROUP BY 1
ORDER BY n_crashes DESC
LIMIT 5
```

**Answer:** Brisbane City, with 3,580 crashes.

| LGA | Crashes (2024) |
|---|---|
| Brisbane City | 3,580 |
| Gold Coast City | 1,688 |
| Logan City | 1,315 |
| Moreton Bay Region | 1,137 |
| Sunshine Coast Region | 745 |

**Tests:** GROUP BY, ORDER BY, LIMIT.

**Notes:** We show the top 5 so the size of the gap is visible. This is a raw count, not a rate: Brisbane City has the largest population, so it comes first. 2024 has no property-damage-only crashes, so these are injury and fatal crashes only. The data uses the old name "Moreton Bay Region" even though the council became the City of Moreton Bay in 2023, so a filter on "Moreton Bay City" would return nothing.

---

## Q3 — Medium
**Question:** How many people were killed on Queensland roads in 2024?

**SQL:**
```sql
SELECT SUM(count_casualty_fatality) FROM crashes WHERE crash_year = 2024
```

**Cross-check (should give the same number):**
```sql
SELECT SUM(casualty_count) FROM agg_casualties
WHERE crash_year = 2024 AND casualty_severity = 'Fatal'
```

**Answer:** 302 people. Both queries return 302.

**Tests:** Choosing SUM of a count column instead of counting rows.

**Notes:** The wrong answer is 273 (fatal *crashes*, from Q1). The 29 extra deaths come from crashes where more than one person died. The row-level and aggregated tables agree exactly.

---

## Q4 — Medium
**Question:** How many crashes in the Brisbane police region involved drink driving in 2024?

**SQL:**
```sql
SELECT SUM(count_crashes)
FROM agg_crash_factors
WHERE crash_year = 2024
  AND police_region = 'Brisbane'
  AND involving_drink_driving = 'Yes'
```

**Answer:** 176 crashes.

**Tests:** Finding the right table (drink driving is only in `agg_crash_factors`) and using SUM on a pre-aggregated table.

**Notes:** `COUNT(*)` here would be wrong: it counts rows (combinations of factors), not crashes. The `crashes` table has no drink-driving column. "Brisbane police region" is not the same area as "Brisbane City" LGA (Q2), so an agent must not mix up `police_region` and `loc_local_government_area`.

---

## Q5 — Hard
**Question:** Did the total number of crashes fall between 2010 and 2011?

**SQL:**
```sql
SELECT crash_year,
       COUNT(*) AS all_crashes,
       COUNT(*) FILTER (WHERE crash_severity <> 'Property damage only') AS injury_and_fatal_crashes
FROM crashes
WHERE crash_year IN (2010, 2011)
GROUP BY 1
ORDER BY 1
```

**Answer:** Only slightly. All recorded crashes went from 22,537 to 12,689 (looks like about -44%), but that is because property-damage-only crashes stopped being included after 2010. Comparing like with like, injury and fatal crashes went from 13,350 to 12,689 (about -5%).

**Tests:** Recognising a change in data coverage instead of reporting a fake trend.

**Notes:** The naive answer ("crashes fell by 44%") is wrong. A good answer must mention the property-damage-only cut-off. (Numbers taken from the explore_checks.py crosstab; confirm by running the SQL.)

---

## General data caveats (for the system prompt later)
- Property-damage-only crashes are only included up to 31 Dec 2010.
- 2025 covers January to June only.
- `police_region` includes an "Unknown" value in every table.
- `crash_severity = 'Fatal'` counts crashes; `count_casualty_fatality` counts people.
- `agg_` tables are pre-aggregated: use `SUM(count_crashes)` / `SUM(casualty_count)`, never `COUNT(*)`.
- Police regions and LGAs are different geographies with overlapping names (e.g. "Brisbane").
- Some LGA names are out of date (e.g. "Moreton Bay Region").
