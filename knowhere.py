import streamlit as st
import plotly.express as px
import statsmodels.api as sm
import pandas as pd
import json

# Basic setup and app layout
st.set_page_config(layout="wide")
st.title("")
st.markdown(
    """
    # Spaceloot Knowhere Transfers 
    ### Created by [@lejimmy](https://twitter.com/lejimmy)
    If you found this useful and would like to support more of this type of work, consider contributing to my wallet here: *terra1m3sl9qea92km6mqm02yqxfygn8g9acl8wzj6x7*

    #### Instructions
    Open the side menu to filter by outliers and attributes.

    """
)

# load tax query into pandas
query_id = "7a881171-55a9-4d67-a170-355c7b6a5728"
df = pd.read_json(
    f"https://api.flipsidecrypto.com/api/v2/queries/{query_id}/data/latest",
    convert_dates=["BLOCK_TIMESTAMP"],
)

df.drop_duplicates(subset=["TX_ID", "EVENT_TYPE"], inplace=True)

# pivot table
df_pivot = df.pivot(
    index="TX_ID", columns="EVENT_TYPE", values=["EVENT_ATTRIBUTES", "BLOCK_TIMESTAMP"]
)

# reindex
df_pivot.columns = ["_".join(tup) for tup in df_pivot.columns.values]


# find messages with 'settle'
df_pivot = df_pivot[
    df_pivot["EVENT_ATTRIBUTES_from_contract"].fillna("").str.contains("settle")
]

# reset index
df_pivot.reset_index(inplace=True)

# extract columns of interest
df_pivot = df_pivot[
    [
        "TX_ID",
        "EVENT_ATTRIBUTES_from_contract",
        "EVENT_ATTRIBUTES_transfer",
        "BLOCK_TIMESTAMP_execute_contract",
    ]
]


# parse raw msg value
df_merge = pd.concat(
    [
        df_pivot,
        pd.json_normalize(df_pivot["EVENT_ATTRIBUTES_from_contract"].apply(json.loads)),
    ],
    axis=1,
)

# parse raw event attributes
df_merge = pd.concat(
    [
        df_merge,
        pd.json_normalize(df_merge["EVENT_ATTRIBUTES_transfer"].apply(json.loads)),
    ],
    axis=1,
)

# parse uluna amount
df_merge["amount"] = df_merge["amount"].explode()

# drop missing rows with amounts messages
# df_merge.dropna(axis=0, subset=["amount"], inplace=True)

# parse amount dict
df_merge["amount"] = pd.json_normalize(df_merge["amount"])["amount"] / 1_000_000

# drop missing rows with missing parsed amounts
df_merge.dropna(axis=0, subset=["amount"], inplace=True)

# drop duplicate sender column
df_merge = df_merge.iloc[:, :-1]

# drop duplicate contract sender columns
df_merge.drop(columns="sender", axis=1, inplace=True)

# extract columns of itnerest
df_merge = df_merge[
    ["TX_ID", "BLOCK_TIMESTAMP_execute_contract", "token_id", "amount", "recipient"]
]

# rename columns
df_merge.rename(columns={"recipient": "sender"}, inplace=True)
df_merge.columns = [*df_merge.columns[:-1], "recipient"]

# rename columns
df_merge.rename(
    columns={"TX_ID": "tx_id", "BLOCK_TIMESTAMP_execute_contract": "timestamp"},
    inplace=True,
)

# combine with rarity guide
df_rarity = pd.read_csv("SpaceLoot Rarity Guide w_ Colors - rarity.csv")
df_rarity = df_rarity[
    [
        "Token ID",
        "Bullish Bear Rating",
        "Vessel Type",
        "Class",
        "Weapon",
        "Secondary Weapon",
        "Shield",
        "Propulsion",
        "Material",
        "Extra",
    ]
]

# merge with rarity guide
df_merge = df_merge.merge(df_rarity, left_on="token_id", right_on="Token ID")
df_merge.drop("Token ID", axis=1, inplace=True)
df_merge.rename(columns={"Bullish Bear Rating": "rarity"}, inplace=True)

# reorder columns
df_merge = df_merge[
    [
        "tx_id",
        "timestamp",
        "sender",
        "recipient",
        "token_id",
        "rarity",
        "amount",
        "Vessel Type",
        "Class",
        "Weapon",
        "Secondary Weapon",
        "Shield",
        "Propulsion",
        "Material",
        "Extra",
    ]
]


# side menu
st.sidebar.header("Settings")

# address filter
st.sidebar.subheader("Wallet Filter")
wallet = st.sidebar.text_input(label="Filter by wallet address containing:")

if wallet:
    df_merge = df_merge[
        (df_merge["sender"].str.contains(wallet, regex=False))
        | (df_merge["recipient"].str.contains(wallet, regex=False))
    ]

# outlier filters
st.sidebar.subheader("Remove Outliers")
sd = st.sidebar.checkbox(
    "",
    value=True,
    help="Remove sales greater than 2 standard deviations.",
)

if sd > 0:
    df_merge = df_merge[df_merge["amount"] < df_merge["amount"].std() * 2 * sd]


# attribute filter
st.sidebar.subheader("Ship Attribute Filters")
filter_v = {}
for col in df_merge.loc[:, "Vessel Type":"Extra"]:

    # list all options
    options = sorted(df_merge[col].unique())
    atr = st.sidebar.selectbox(col, options=(None, *options))

    # add filter to dict
    if atr:
        filter_v[col] = atr

# if filter dictionary exists, filter by dict
if len(filter_v) > 0:
    print(filter_v)
    df_merge = df_merge.loc[
        (df_merge[list(filter_v)] == pd.Series(filter_v)).all(axis=1)
    ]

# length check
if len(df_merge) == 0:
    st.warning("Filters produced zero results.  Please try again.")

st.header("Sales Over Time")
st.write(
    "Completed sales over time with rarity rank as color.  Smaller ranks are more rare."
)
fig = px.scatter(
    df_merge,
    x="timestamp",
    y="amount",
    color="rarity",
    color_continuous_scale="sunsetdark",
)
st.plotly_chart(fig, use_container_width=True)

st.header("Distribution of Sales")
st.write("Histogram of auction settlements.")
fig = px.histogram(df_merge, x="amount", nbins=100, color_discrete_sequence=["#9c179e"])
st.plotly_chart(fig, use_container_width=True)

st.header("Sales Price vs. Rarity Rank")
st.markdown(
    "Spaceloot Rarity Rank plotted against [Bullish Bear](https://twitter.com/L_BullishBear)'s Rarity Rank Database.  Smaller ranks are more rare."
)
fig = px.scatter(
    df_merge,
    x="rarity",
    y="amount",
    color_discrete_sequence=["#9c179e"],
    trendline="ols",
    trendline_options=dict(log_x=True),
    trendline_color_override="#f0f921",
)
st.plotly_chart(fig, use_container_width=True)

st.header("Transactions Table")
st.write("History of completed auction transfers.")
st.write(df_merge)

st.markdown("## **Closing Thoughts**")
st.markdown(
    f"""
    I hope this was useful, perhaps a bit insightful, and as always, wagmi.

    Feel free to reach out to me on Twitter [@lejimmy](https://twitter.com/lejimmy) if you have any questions or feedback.
     
    If you're inclined to contribute directly, please fork the [Github Repo here](https://github.com/lejimmy/streamlit-dashboards).

    """
)
