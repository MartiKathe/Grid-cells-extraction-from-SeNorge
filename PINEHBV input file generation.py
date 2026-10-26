import pandas as pd

# modify average altitude (avgalt) to the one number extracted by the script in "precipitation and temperature gridded extraction.py"
# good to change
stations = [
    ("ExampleCatchment daily precipitation grid cells.csv", "ExampleCatchment daily temperature grid cells.csv",
     "P_avgalt_masl", "T_avgalt_masl",
     "ExampleCatchment_ready_for_PINEHBV.xlsx")  # change ExampleCatchment to your catchment name, and avgalt to catchment extracted average altitude
]


def load_data(filepath):
    try:
        # Read the CSV, skipping the metadata row (#)
        df = pd.read_csv(filepath, sep=';', comment='#')

        # Split the first column into date and time
        datetime_split = df.iloc[:, 0].astype(str).str.split(' ', expand=True)
        date_col = datetime_split[0]
        time_col = datetime_split[1]

        value_col = df.iloc[:, 1]

        return date_col, time_col, value_col
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return None, None, None


for prec_f, temp_f, p_lab, t_lab, out_name in stations:
    print(f"--- Creating {out_name} ---")

    prec_date, prec_time, prec_val = load_data(prec_f)
    _, _, temp_val = load_data(temp_f)

    if prec_date is None or prec_val is None or temp_val is None:
        print(f"Skipping {out_name} due to missing files.")
        continue

    final_rows = []

    # Row 1 headers
    final_rows.append(["Dato", "Tid", p_lab, t_lab, t_lab, "Runoff"])

    # Row 2 units
    final_rows.append(["dd.mm.yyyy", "hh:mm:ss", "mm", "C", "C", "m3/s"])

    for i in range(len(prec_date)):
        # Convert YYYY-MM-DD to DD.MM.YYYY for PINEHBV
        raw_date = prec_date.iloc[i]
        formatted_date = pd.to_datetime(raw_date, dayfirst=True).strftime('%d.%m.%Y')

        final_rows.append([
            formatted_date,  # Date (From CSV)
            prec_time.iloc[i],  # Time (From CSV)
            prec_val.iloc[i],  # P
            temp_val.iloc[i],  # T
            temp_val.iloc[i],  # T Duplicate
            0.0  # <--- Runoff set to exactly 0
        ])

    pd.DataFrame(final_rows).to_excel(out_name, index=False, header=False)
    print(f"Successfully saved {out_name}")

print("\nDone!")