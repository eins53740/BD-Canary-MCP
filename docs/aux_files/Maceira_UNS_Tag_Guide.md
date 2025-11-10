# Maceira UNS Tag & Path Guide (LLM Ready)

> Version: auto-generated from available Canary path descriptions (if present).

## 1. Canonical Path Shape
```
Maceira.<AreaCode - AreaName>.<UnitCode - UnitName>.<Schema>.<Category>.<DeviceOrSignal>.<Attribute>
```

### 1.1 Schemas
- **Edge** — raw source systems
- **KPI** — calculated indicators
- **Normalised** — cleansed, semantic model (preferred)

### 1.2 Common Categories (Normalised)
`Alarms`, `Analog`, `Asset`, `Automation`, `Controllers`, `Daily`, `Department`, `ECS`, `Edge`, `Emissions`, `Energy`, `Equipment`, `Gamma Metrics`, `Group`, `Groups`, `HGH`, `Indications`, `Instantaneous`, `Machines`, `Monthly`, `OptimizationSystem`, `Other`, `Output Material`, `POLAB`, `Quality`, `Quarry`, `Selections`, `Shift`, `Weekly`, `Yearly`

## 2. ISA-95 Mapping to the Namespace
- **Site** → `Maceira`
- **Area (Production Segment)** → `100 … 900` code with name, e.g., `400 - Clinker Production`
- **Unit (Equipment)** → code with name, e.g., `431 - Kiln`, `432 - Kiln`, `442 - Clinker Cooler`
- **Schema** → Normalised / Edge / KPI
- **Category** → Analog, Indications, Machines, Alarms, etc.
- **DeviceOrSignal** → plant mnemonic (e.g., `FO6AI_6461`)
- **Attribute** → `Value`, `Active`, `Open/Closed`, `Status`, `Setpoint`, …

## 3. Area & Unit Catalogue (ISA-95 codes)
_Extracted from the uploaded dataset; codes and names are authoritative._

### 100 - Raw Materials Handling
- 111 - Crushing
- 121 - Conveying to Storage
- 131 - Raw Materials Storage
- 141 - Conveying To Mills
### 200 - Additives And Fuel Handling
- 211 - Coal Intake and Crushing
- 231 - Coal Storage
- 232 - Heavy Fuel
- 241 - Coal Transport from Storage
- 261 - Tyre Storage
- 262 - Alternative Fuel Storage
### 300 - Raw Meal Production
- 311 - Raw Materials Conveying
- 321 - Raw Mill
- 322 - Raw Mill
- 323 - Filler Mill
- 341 - Raw Mill Silo
### 400 - Clinker Production
- 431 - Kiln
- 432 - Kiln
- 441 - Clinker Cooler
- 442 - Clinker Cooler
- 451 - Bypass
- 461 - Coal Mill
- 462 - Coal Mill
- 481 - Clinker Storage
- 490 - Miscellaneous For Clinker Production
### 500 - Cement Grinding
- 511 - Clinker Conveying
- 521 - Roller Press
- 531 - Cement Mill
- 532 - Cement Mill
- 533 - Cement Mill
- 534 - Mixer
- 541 - Conveying to Silos
### 600 - Cement Packaging and Dispatch
- 621 - Cement conveying
- 631 - Bulk Dispatch Station
- 632 - Bulk Dispatch Station
- 633 - Bulk Dispatch Station
- 634 - Bulk Dispatch Station
- 635 - Bulk Dispatch Station
- 636 - Bulk Dispatch Station
- 641 - Packing Machine
- 642 - Packing Machine
- 643 - Packing Machine
- 661 - Big-Bag Loading Station
- 671 - Bag Conveying
- 681 - Palletizer
- 682 - Palletizer
### 700 - Utilities
- 761 - Raw Water Treatment
### 800 - Electrical Departments
- 841 - Control Equipment
- 851 - Instrumentation
- 891 - Plant Main Substation

## 4. End-to-End Examples (NL → Tag Path)
- `400 - Clinker Production.451 - Bypass.Normalised.Indications.BYPVT603INT02.Active`  
  _from Canary_Path_description_maceira.json_
- `400 - Clinker Production.432 - Kiln.Normalised.Machines.FO6RGH32M1.Closed`  
  _from Canary_Path_description_maceira.json_
- `400 - Clinker Production.432 - Kiln.Normalised.OptimizationSystem.FO6AI_6461.Value`  
  _from Canary_Path_description_maceira.json_
- `500 - Cement Grinding.511 - Clinker Conveying.Normalised.Indications.TADTL32INT01.Status`  
  _from Canary_Path_description_maceira.json_
- `500 - Cement Grinding.521 - Roller Press.Normalised.OptimizationSystem.PRLEV14M14.Open`  
  _from Canary_Path_description_maceira.json_
- `400 - Clinker Production.431 - Kiln.KPI.Instantaneous.Emissions.Part`  
  _from Canary_Path_description_maceira.json_
- `800 - Electrical Departments.841 - Control Equipment.Edge.POLAB.MKF6.MKF6_HALITE`  
  _from Canary_Path_description_maceira.json_
- `600 - Cement Packaging and Dispatch.671 - Bag Conveying.Normalised.Indications.EMBRG1003INT04.Status`  
  _from Canary_Path_description_maceira.json_
- `400 - Clinker Production.462 - Coal Mill.Normalised.Alarms.MC1DISJ_D1.InAlarm`  
  _from Canary_Path_description_maceira.json_
- `400 - Clinker Production.462 - Coal Mill.Normalised.Analog.MC1TT_6335_6.Value`  
  _from Canary_Path_description_maceira.json_
- `500 - Cement Grinding.532 - Cement Mill.Normalised.Analog.MC8SO3SP_SP13.Value`  
  _from Canary_Path_description_maceira.json_
- `600 - Cement Packaging and Dispatch.671 - Bag Conveying.Normalised.Indications.EMBEV1300INT07.Status`  
  _from Canary_Path_description_maceira.json_
- `500 - Cement Grinding.531 - Cement Mill.Normalised.Analog.MC7TT_7129_2_2.Value`  
  _from Canary_Path_description_maceira.json_
- `500 - Cement Grinding.531 - Cement Mill.Normalised.Indications.MC7G05INT01.Active`  
  _from Canary_Path_description_maceira.json_
- `600 - Cement Packaging and Dispatch.633 - Bulk Dispatch Station.Edge.ECS.TSACG01.GN34EV34`  
  _from Canary_Path_description_maceira.json_
- `500 - Cement Grinding.531 - Cement Mill.Normalised.Analog.MC7TT_133_1_2.Value`  
  _from Canary_Path_description_maceira.json_
- `500 - Cement Grinding.534 - Mixer.Normalised.Indications.MSTSO78INT06.Active`  
  _from Canary_Path_description_maceira.json_
- `600 - Cement Packaging and Dispatch.671 - Bag Conveying.Normalised.Indications.EMBVC3227INT02.Status`  
  _from Canary_Path_description_maceira.json_
- `500 - Cement Grinding.531 - Cement Mill.Normalised.Analog.MC7RESIDUE32RST_SP18.Status`  
  _from Canary_Path_description_maceira.json_
- `300 - Raw Meal Production.323 - Filler Mill.Normalised.Indications.MFLG02INT02.Active`  
  _from Canary_Path_description_maceira.json_
- `400 - Clinker Production.431 - Kiln.KPI.Daily.Quality.Kiln`  
  _from Canary_Path_description_maceira.json_
- `400 - Clinker Production.432 - Kiln.Normalised.Asset.Equipment.Hydrogen`  
  _from Canary_Path_description_maceira.json_
- `500 - Cement Grinding.541 - Conveying to Silos.Normalised.Indications.TSLVC8INT04.Active`  
  _from Canary_Path_description_maceira.json_
- `600 - Cement Packaging and Dispatch.671 - Bag Conveying.Normalised.Indications.EMBTL6054INT02.Status`  
  _from Canary_Path_description_maceira.json_
- `600 - Cement Packaging and Dispatch.671 - Bag Conveying.Normalised.Indications.EMBTP6007INT01.Active`  
  _from Canary_Path_description_maceira.json_
- `400 - Clinker Production.431 - Kiln.Normalised.Analog.FO5JT_89.Value`  
  _from Canary_Path_description_maceira.json_
- `500 - Cement Grinding.541 - Conveying to Silos.Normalised.Selections.TSLEL1_S25SEL01.Selected`  
  _from Canary_Path_description_maceira.json_
- `300 - Raw Meal Production.322 - Raw Mill.Normalised.Indications.MC6RG6044M1INT02.Status`  
  _from Canary_Path_description_maceira.json_
- `600 - Cement Packaging and Dispatch.671 - Bag Conveying.Normalised.Indications.EMBMT0909M3INT09.Status`  
  _from Canary_Path_description_maceira.json_
- `500 - Cement Grinding.532 - Cement Mill.Normalised.Indications.MC8G01INT04.Status`  
  _from Canary_Path_description_maceira.json_
- `600 - Cement Packaging and Dispatch.621 - Cement conveying.Normalised.Selections.EMBCIRC48SEL01.Selected`  
  _from Canary_Path_description_maceira.json_
- `500 - Cement Grinding.531 - Cement Mill.Normalised.Indications.MC7MA7118INT02.Status`  
  _from Canary_Path_description_maceira.json_
- `500 - Cement Grinding.533 - Cement Mill.Normalised.Analog.MC9REJECT_SP16.Value`  
  _from Canary_Path_description_maceira.json_
- `500 - Cement Grinding.534 - Mixer.Normalised.Indications.MSTCP7142INT02.Active`  
  _from Canary_Path_description_maceira.json_
- `400 - Clinker Production.442 - Clinker Cooler.Normalised.Indications.AR6BR6128INT07.Status`  
  _from Canary_Path_description_maceira.json_
- `500 - Cement Grinding.533 - Cement Mill.Normalised.Indications.MC9G06INT09.Active`  
  _from Canary_Path_description_maceira.json_
- `400 - Clinker Production.442 - Clinker Cooler.Normalised.Analog.AR6JT_6068.Status`  
  _from Canary_Path_description_maceira.json_
- `500 - Cement Grinding.511 - Clinker Conveying.Normalised.Indications.TADTL85INT08.Active`  
  _from Canary_Path_description_maceira.json_
- `600 - Cement Packaging and Dispatch.671 - Bag Conveying.Normalised.Indications.EMBEX1031INT10.Active`  
  _from Canary_Path_description_maceira.json_
- `300 - Raw Meal Production.322 - Raw Mill.Normalised.Indications.MC6G06INT09.Active`  
  _from Canary_Path_description_maceira.json_

## 5. Tag Types, Sensor Types, and Data Types
### 5.1 Tag Types by Category & Attribute
| Category | Typical Devices | Attributes | Data type | Notes |
|---|---|---|---|---|
| Analog | AI channels, flow/pressure/temp, analysers | Value, Quality, Timestamp, Setpoint | float (double), int | Units in metadata (%, ppm, °C, mbar) |
| Indications | limit switches, binary states | Active, Status | boolean | True/False with quality bit |
| Machines | motors, fans, valves, dampers | Running, Stopped, Open, Closed, Position | boolean, integer, float | Position often 0–100 |
| Alarms | any equipment | Active, Ack, Shelved | boolean | Alarm model aligns with ISA-18.2 |
| OptimizationSystem | kiln/cooler analysers, MPC signals | Value, Target, Deviation | float | Advanced control interfaces |
| Controllers | PID blocks, loops | PV, SP, OP, Mode | float, enum | Mode may be enum (Auto/Man/Cascade) |
| Quality | lab results (POLAB) | Result, Lot, Timestamp | float, string, datetime | Often comes via Edge→Normalised |
| Emissions | CEMS stacks | Value, Status | float, enum | Regulatory reporting tags |
| Energy | power meters (ION) | kW, kWh, PF, V, A | float | Time-aggregated KPIs under KPI schema |

### 5.2 Sensor Types (examples)
| Sensor | Measures | Category | Data type | Units |
|---|---|---|---|---|
| Thermocouple / RTD | Temperature | Analog | float | °C |
| Electrochemical analysers | O₂, CO, NOx | Analog/OptimizationSystem | float | % / ppm |
| Differential pressure transmitter | DP across filter/fan | Analog | float | Pa / mbar |
| Vibration sensor (IEPE) | RMS velocity/accel | Analog | float | mm/s / g |
| Proximity switch | End position | Indications | boolean | Open/Closed |
| Limit switch | Gate/valve state | Indications/Machines | boolean | Active/Inactive |
| Rotameter / mass flow | Fuel/air flow | Analog | float | Nm³/h / t/h |
| Power meter (ION) | Electrical | Energy | float | kW/kWh |
| Weighfeeder | Feed rate | Analog/Controllers | float | t/h |

### 5.3 Data Types
- **boolean**: `True/False` states (Indications, Alarms).
- **integer**: counts, enumerations, discrete positions.
- **float/double**: measurements, KPIs, setpoints.
- **string**: codes, lot IDs, descriptive fields.
- **datetime (ISO 8601)**: timestamps for samples/aggregations.

## 6. Best Practices for Namespace Structuring
- Prefer **codes** as canonical keys; names are helper labels.
- Keep **schema boundaries** strict: Normalised for semantic, Edge for raw, KPI for aggregates.
- Standardise **attributes** across categories (`Value`, `Active`, `Status`, `Setpoint`, …).
- Store **units** in metadata, not in tag names.
- Avoid diacritics and special characters in keys; use clear pt-PT descriptions in metadata.
- Version changes using metadata (`version`, `source`, `last_changed`), never by changing codes.
- Use **idempotent** paths so clients can cache and subscribe reliably.

## 7. NL → ISA‑95 Resolution Algorithm (for LLMs)
1. Resolve **unit** from user text (e.g., 'Kiln 6' → `432 - Kiln`).
2. Infer **intent** → Category & Attribute.
3. Construct candidates under **Normalised**; fall back to **Edge**.
4. Validate by device code, unit of measure, and recent data quality.
5. Return best match with confidence and alternatives.

### 7.1 Asset Number Mapping Examples
- **Kiln 5** ↔ **ISA‑95 `431 - Kiln`**
- **Kiln 6** ↔ **ISA‑95 `432 - Kiln`**

## 8. Discovered Example Paths
| area                                | unit                        | schema     | category           | device               | attribute   | source_file                          |
|:------------------------------------|:----------------------------|:-----------|:-------------------|:---------------------|:------------|:-------------------------------------|
| 400 - Clinker Production            | 451 - Bypass                | Normalised | Indications        | BYPVT603INT02        | Active      | Canary_Path_description_maceira.json |
| 400 - Clinker Production            | 432 - Kiln                  | Normalised | Machines           | FO6RGH32M1           | Closed      | Canary_Path_description_maceira.json |
| 400 - Clinker Production            | 432 - Kiln                  | Normalised | OptimizationSystem | FO6AI_6461           | Value       | Canary_Path_description_maceira.json |
| 500 - Cement Grinding               | 511 - Clinker Conveying     | Normalised | Indications        | TADTL32INT01         | Status      | Canary_Path_description_maceira.json |
| 500 - Cement Grinding               | 521 - Roller Press          | Normalised | OptimizationSystem | PRLEV14M14           | Open        | Canary_Path_description_maceira.json |
| 400 - Clinker Production            | 431 - Kiln                  | KPI        | Instantaneous      | Emissions            | Part        | Canary_Path_description_maceira.json |
| 800 - Electrical Departments        | 841 - Control Equipment     | Edge       | POLAB              | MKF6                 | MKF6_HALITE | Canary_Path_description_maceira.json |
| 600 - Cement Packaging and Dispatch | 671 - Bag Conveying         | Normalised | Indications        | EMBRG1003INT04       | Status      | Canary_Path_description_maceira.json |
| 400 - Clinker Production            | 462 - Coal Mill             | Normalised | Alarms             | MC1DISJ_D1           | InAlarm     | Canary_Path_description_maceira.json |
| 400 - Clinker Production            | 462 - Coal Mill             | Normalised | Analog             | MC1TT_6335_6         | Value       | Canary_Path_description_maceira.json |
| 500 - Cement Grinding               | 532 - Cement Mill           | Normalised | Analog             | MC8SO3SP_SP13        | Value       | Canary_Path_description_maceira.json |
| 600 - Cement Packaging and Dispatch | 671 - Bag Conveying         | Normalised | Indications        | EMBEV1300INT07       | Status      | Canary_Path_description_maceira.json |
| 500 - Cement Grinding               | 531 - Cement Mill           | Normalised | Analog             | MC7TT_7129_2_2       | Value       | Canary_Path_description_maceira.json |
| 500 - Cement Grinding               | 531 - Cement Mill           | Normalised | Indications        | MC7G05INT01          | Active      | Canary_Path_description_maceira.json |
| 600 - Cement Packaging and Dispatch | 633 - Bulk Dispatch Station | Edge       | ECS                | TSACG01              | GN34EV34    | Canary_Path_description_maceira.json |
| 500 - Cement Grinding               | 531 - Cement Mill           | Normalised | Analog             | MC7TT_133_1_2        | Value       | Canary_Path_description_maceira.json |
| 500 - Cement Grinding               | 534 - Mixer                 | Normalised | Indications        | MSTSO78INT06         | Active      | Canary_Path_description_maceira.json |
| 600 - Cement Packaging and Dispatch | 671 - Bag Conveying         | Normalised | Indications        | EMBVC3227INT02       | Status      | Canary_Path_description_maceira.json |
| 500 - Cement Grinding               | 531 - Cement Mill           | Normalised | Analog             | MC7RESIDUE32RST_SP18 | Status      | Canary_Path_description_maceira.json |
| 300 - Raw Meal Production           | 323 - Filler Mill           | Normalised | Indications        | MFLG02INT02          | Active      | Canary_Path_description_maceira.json |