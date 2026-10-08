#!/usr/bin/env python3

import pandas as pd
df = pd.read_csv('dataset/combined/combined_evaluator_dataset.csv')
print(f'Dataset has {len(df)} rows')
print(f'Columns: {list(df.columns)}')