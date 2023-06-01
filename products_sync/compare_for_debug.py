import pandas as pd

store_df = pd.concat(
    pd.read_csv(f'../samples/products_export_{i}.csv', usecols=['Title', 'Variant Barcode'], dtype=str)
    for i in range(1, 3)
).dropna(subset=['Variant Barcode']).set_index('Variant Barcode')

store_df.index = store_df.index.str.replace(r"\D", "", regex=True)

sup_df = pd.read_csv(f'../samples/suppliers_data.csv', usecols=['upc'], dtype=str).dropna(subset=['upc']).set_index('upc')


mdf = store_df.join(sup_df, how='inner')

print(mdf)
