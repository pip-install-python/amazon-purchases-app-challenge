import polars as pl
import json
import random
import uuid
import os


# Function to generate random HSL color
def random_hsl_color():
    hue = random.randint(0, 359)
    return f"hsl({hue}, 70%, 50%)"


# Load the CSV file
df = pl.read_csv('assets/processed_amazon_purchases.csv')

# Ensure numeric columns are the right type and handle NaN values
df = df.with_columns([
    pl.col('Purchase Price Per Unit').cast(pl.Float64).fill_null(0),
    pl.col('Quantity').cast(pl.Float64).fill_null(0),
    pl.col('Shipping Address State').fill_null('Unknown')  # Fill null states with 'Unknown'
])

# Calculate the total value for each purchase
df = df.with_columns(
    (pl.col('Purchase Price Per Unit') * pl.col('Quantity')).alias('Total Value')
)

# Create states directory if it doesn't exist
os.makedirs('assets/states', exist_ok=True)

# Process data for each state
for state in df['Shipping Address State'].unique():
    state_df = df.filter(pl.col('Shipping Address State') == state)

    # Save CSV for the state
    state_df.write_csv(f'assets/states/{state}_purchases.csv')

    # Create hierarchical data for the state
    state_data = {
        "name": state,
        "id": str(uuid.uuid4()),
        "children": []
    }

    for category in state_df['Category'].unique():
        category_data = {
            "name": category,
            "id": str(uuid.uuid4()),
            "children": []
        }
        category_df = state_df.filter(pl.col('Category') == category)

        grouped_df = category_df.group_by('Title').agg([
            (pl.col('Purchase Price Per Unit') * pl.col('Quantity')).sum().alias('Total Value'),
            pl.count('Title').alias('Purchase Count')
        ])

        for row in grouped_df.to_dicts():
            title_data = {
                "name": f"{row['Title']} (x{row['Purchase Count']})",
                "id": str(uuid.uuid4()),
                "color": random_hsl_color(),
                "loc": round(row['Total Value'], 2)
            }
            category_data["children"].append(title_data)

        state_data["children"].append(category_data)

    # Save JSON for the state
    with open(f'assets/states/{state}_hierarchy.json', 'w') as f:
        json.dump(state_data, f, indent=2)

print("State-wise data saved in 'assets/states/' directory")

# Create and save the main hierarchical structure
main_hierarchy = {
    "name": "All Orders",
    "id": str(uuid.uuid4()),
    "children": []
}

for state in df['Shipping Address State'].unique():
    with open(f'assets/states/{state}_hierarchy.json', 'r') as f:
        state_data = json.load(f)
    main_hierarchy["children"].append(state_data)

with open('assets/hierarchical_purchases.json', 'w') as f:
    json.dump(main_hierarchy, f, indent=2)

print("Main hierarchical data saved to 'assets/hierarchical_purchases.json'")