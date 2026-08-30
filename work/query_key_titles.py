from pathlib import Path
import pandas as pd

root = Path(__file__).resolve().parents[1]
x = pd.read_excel(root / "data/raw/bemp/metadata/bemp_variable_list_full.xlsx", dtype=str).fillna("")

patterns = [
    r"^(Latitude|Longitude|GPS|Coordinate)$",
    r"^(District|Household Origin (Village|City|Country|Rural Urban|Domestic Abroad|Village Existence|Village River Distance|Village River Side)|Residence Type|Current Location Residence Duration)$",
    r"^(Distance from Previous Location|House Shift Distance|Migration Distance)$",
    r"^Migration Respondent (Domestic Abroad|Rural Urban|Same District|Same or Different Village|Village|City|Country|Individual or Household|Reasons|Return Plans|Return Plans Time|Return Reasons|Seasonal Pattern|Seasonal Pattern Days|Seasonal Pattern Months|Seasonal Pattern Weeks|Still Away|Duration|Frequency|Year|Month|Month Part)$",
    r"^Migration Family Member (Domestic Abroad|Rural Urban|Same District|Same or Different Village|Village|City|Country|Individual or Household|Reasons|Return Plans|Return Plans Time|Return Reasons|Seasonal Pattern|Seasonal Pattern Days|Seasonal Pattern Months|Seasonal Pattern Weeks|Still Away|Duration|Frequency|Year|Month|Month Part)$",
    r"^(Household Member Migration|Household Member Migration \(Follow-Up\)|Household Migration Frequency|Household Migration Reasons|Migration Participants|Migration Respondent Current Destination Choice Relatives|Migration Respondent Current Destination Choice Reasons|Migration Respondent Destination Choice Reasons|Migration Family Member Destination Choice Reasons)$",
]
mask = pd.Series(False, index=x.index)
for pattern in patterns:
    mask |= x["variable_title"].str.contains(pattern, regex=True, case=False, na=False)

cols = ["variable_title", "variable_label", "appears_in", "w1", "w6_M", "w12_M", "w14_M"]
y = x.loc[mask, cols].sort_values(["variable_title", "variable_label"])
y.to_csv(root / "work/key_title_mappings.csv", index=False)
print(y.to_string(index=False, max_colwidth=160))
