# Data for dietverse

The repository contains no data files. The demo and the tests use synthetic files that
`dietverse synth` or `dietverse demo` writes in the same layout.

## 1. COVID-19 Healthy Diet data set

| Item | Value |
|---|---|
| Source | Kaggle, "COVID-19 Healthy Diet Dataset" (Maria Ren). It combines FAO food balance data, obesity and undernourishment rates and COVID-19 case and death counts |
| URL | https://www.kaggle.com/datasets/mariaren/covid19-healthy-diet-dataset |
| Licence | See the Kaggle page. The underlying FAO and COVID-19 data have their own terms. Cite the sources |
| Download | `kaggle datasets download -d mariaren/covid19-healthy-diet-dataset`, then unzip |

Put the files in `data/covid-healthy-diet/` (or set `DIETVERSE_DATA_DIR`):

| File | Measure in dietverse | Unit |
|---|---|---|
| `Food_Supply_kcal_Data.csv` | `energy` | % of dietary energy supply |
| `Food_Supply_Quantity_kg_Data.csv` | `quantity` | % of food supply by weight |
| `Fat_Supply_Quantity_Data.csv` | `fat` | % of fat supply |
| `Protein_Supply_Quantity_Data.csv` | `protein` | % of protein supply |

`Supply_Food_Data_Descriptions.csv` lists the FAO items in each food group. dietverse does not read it.

## 2. Columns and unit rules

Each file has `Country`, 21 food groups, the aggregates `Animal Products` and `Vegetal Products`,
`Obesity`, `Undernourished`, `Confirmed`, `Deaths`, `Recovered`, `Active`, `Population` and
`Unit (all except Population)`.

| Rule | What dietverse does |
|---|---|
| The unit column must be `%` | Any other unit stops the load |
| The 21 groups add up to 50 and the two aggregates add up to 50 in each row | The load checks both sums (tolerance 0.5). The share of a group is its value divided by the group sum, times 100 |
| `Obesity`, `Undernourished`, `Confirmed`, `Deaths` are % of the population | Deaths per 100,000 = `Deaths` × 1,000 |
| `Undernourished` can be the text `<2.5` | Kept as 2.5 with the flag `undernourished_censored` |
| Empty outcome cells | Kept as missing. Each analysis drops the incomplete countries and reports the count |

On the real files the loader reports 170 countries, 44 censored undernourishment values, and missing
values in `Obesity` (3), `Undernourished` (7), `Confirmed` and `Deaths` (6) and `Active` (8).

## 3. Covariates (optional)

`dietverse analyze --covariates file.csv` (or `DIETVERSE_COVARIATES`) adds control variables. The file needs
a `Country` column with the same names as the data set and one or more numeric columns, for example median
age, GDP per person or tests per 1,000 people. Good sources are the World Bank and Our World in Data. Check the
licence of each source.

## 4. Synthetic files

`dietverse synth --out data/synthetic` writes the four files for 60 invented countries ("Country 001" and so on),
a `covariates.csv` with an invented median age and a `SYNTHETIC` marker file. A hidden "development" value drives
the diet, obesity, age and deaths, so a raw correlation is larger than the partial correlation.
