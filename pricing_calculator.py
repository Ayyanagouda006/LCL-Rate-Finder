import pandas as pd
from datetime import datetime
import pandas as pd

def build_port_lookup(file_path):
    sheets = [
        "OF Direct", "DC Direct",
        "OF 2nd Leg", "DC 2nd Leg"
    ]
    name_unloc_pairs = set()

    for sheet in sheets:
        try:
            df = pd.read_excel(file_path, sheet_name=sheet)

            if "Port of Loading" in df.columns and "POL UNLOC" in df.columns:
                pairs = df[["Port of Loading", "POL UNLOC"]].dropna().values.tolist()
                name_unloc_pairs.update(map(tuple, pairs))

            if "Port of Discharge" in df.columns and "POD UNLOC" in df.columns:
                pairs = df[["Port of Discharge", "POD UNLOC"]].dropna().values.tolist()
                name_unloc_pairs.update(map(tuple, pairs))

            if "Reworking Port" in df.columns and "TS UNLOC" in df.columns:
                pairs = df[["Reworking Port", "TS UNLOC"]].dropna().values.tolist()
                name_unloc_pairs.update(map(tuple, pairs))

        except Exception as e:
            print(f"Error reading {sheet}: {e}")

    # Create name → UNLOC dictionary
    port_lookup = {name.strip(): code.strip() for name, code in name_unloc_pairs}
    
    # Add UNLOC → UNLOC mapping
    for name, code in list(port_lookup.items()):
        port_lookup[code] = code

    return port_lookup

def lclpricing(origin, destination, transhipment='Direct'):
    file_path = r"Data/LCL Pricing Navexel2 2.xlsx"

    # Load sheets
    of_direct = pd.read_excel(file_path, "OF Direct")
    dc_direct = pd.read_excel(file_path, "DC Direct")
    dc_direct['Charge Head'] = dc_direct['Charge Head'].str.upper()
    of_2nd_leg = pd.read_excel(file_path, "OF 2nd Leg")
    dc_2nd_leg = pd.read_excel(file_path, "DC 2nd Leg")
    dc_2nd_leg['Charge Head'] = dc_2nd_leg['Charge Head'].str.upper()
    agent = pd.read_excel(file_path, "Agent details")

    try:
        of_direct_row = of_direct[
            (of_direct["POL UNLOC"] == origin) & (of_direct["POD UNLOC"] == destination)
        ]
        if of_direct_row.empty:
            return None

        of_direct_rate = of_direct_row['MRG (Per W/M)'].values[0]
        of_direct_bl = of_direct_row['MRG (Per BL)'].values[0]
        of_direct_limit = of_direct_row['Limit'].values[0]
        of_direct_1st = of_direct_row['1st Leg'].values[0]

        if transhipment != 'Direct':
            of_2nd_leg_row = of_2nd_leg[
                (of_2nd_leg["TS UNLOC"] == transhipment) & (of_2nd_leg["POD UNLOC"] == destination)
            ]
            if of_2nd_leg_row.empty:
                return None
            of_2nd_leg_rate = of_2nd_leg_row['MRG (Per W/M)'].values[0]

            dc_2nd_leg_match = dc_2nd_leg[
                (dc_2nd_leg["TS UNLOC"] == transhipment) &
                (dc_2nd_leg["POD UNLOC"] == destination) &
                (dc_2nd_leg["Charge Head"] != "ALL IN RATE")
            ][["Charge Head", "Currency", "MRG (Per W/M)", "Remarks"]].fillna("")

            dc_2nd_leg_match_allin = dc_2nd_leg[
                (dc_2nd_leg["TS UNLOC"] == transhipment) &
                (dc_2nd_leg["POD UNLOC"] == destination) &
                (dc_2nd_leg["Charge Head"] == "ALL IN RATE")
            ][["Charge Head", "Currency", "MRG (Per W/M)", "Remarks"]].fillna("")

            agent_details = agent[
                (agent['POL/Reworking'] == transhipment) & (agent['POD'] == destination)
            ][['Agent Name', 'Address', 'Contact Person', 'Email', 'Phone']].fillna("")

            return {
                "OF": float(of_direct_1st) + float(of_2nd_leg_rate),
                "DC 2nd Leg": dc_2nd_leg_match,
                "DC 2nd Leg(All in Rate)": dc_2nd_leg_match_allin,
                "Agent": agent_details
            }

        else:
            dc_match = dc_direct[
                (dc_direct["POL UNLOC"] == origin) &
                (dc_direct["POD UNLOC"] == destination) &
                (dc_direct["Charge Head"] != "ALL IN RATE")
            ][["Charge Head", "Currency", "MRG (Per W/M)", "Remarks"]].fillna("")

            dc_allin = dc_direct[
                (dc_direct["POL UNLOC"] == origin) &
                (dc_direct["POD UNLOC"] == destination) &
                (dc_direct["Charge Head"] == "ALL IN RATE")
            ][["Charge Head", "Currency", "MRG (Per W/M)", "Remarks"]].fillna("")

            agent_details = agent[
                (agent['POL/Reworking'] == origin) & (agent['POD'] == destination)
            ][['Agent Name', 'Address', 'Contact Person', 'Email', 'Phone']].fillna("")

            return {
                "OF": float(of_direct_rate),
                "Limit": float(of_direct_limit),
                "BL": of_direct_bl,
                "DC": dc_match,
                "DC (All in Rate)": dc_allin,
                "Agent": agent_details
            }

    except Exception as e:
        return None


