# U.S. Elections Analysis (1976–2020)

Analyzes U.S. Presidential and Senate election data using SQLite, pandas, and matplotlib. Built as the final project for CSC271H1.

## What it does
- Loads and cleans MIT Election Lab presidential and Senate data
- Stores the cleaned data in a SQLite database
- Runs SQL queries: Senate seats won per party, the presidential "coattail" effect, and net seat change per cycle
- Visualizes the results with matplotlib

## How to run
1. Install the dependencies: pip install -r requirements.txt
2. Open project.ipynb in Jupyter and run all cells. This builds elections.db from the CSVs in data/.

## Files
- `project.py`: functions for loading, querying, and plotting
- `project.ipynb`: notebook that runs the analysis
- `data/`: source CSV files (MIT Election Data and Science Lab)

## Author
Arshad Saleh