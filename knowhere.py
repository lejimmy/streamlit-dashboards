import streamlit as st
import plotly.express as px
import pandas as pd
import json

# Basic setup and app layout
st.set_page_config(layout="wide")
st.title("Spaceloot Knowhere Transfers")

# load tax query into pandas
query_id = "e33b0d90-af51-4b41-bc21-1da822567446"
df = pd.read_json(
    f"https://api.flipsidecrypto.com/api/v2/queries/{query_id}/data/latest",
    convert_dates=["BLOCK_TIMESTAMP"],
)

# parse raw msg value
df_merge = pd.concat([df, pd.json_normalize(df["MSG_VALUE"].apply(json.loads))], axis=1)

# parse raw event attributes
df_merge = pd.concat(
    [df_merge, pd.json_normalize(df_merge["EVENT_ATTRIBUTES"].apply(json.loads))],
    axis=1,
)

# parse uluna amount
df_merge["amount"] = df_merge["amount"].explode()

# parse amount dict
df_merge["amount"] = pd.json_normalize(df_merge["amount"])["amount"]

# convert to luna
df_merge["amount"] = df_merge["amount"] / 1_000_000

# drop duplicate sender column
df_merge = df_merge.iloc[:, :-1]

# extract columns of itnerest
df_merge = df_merge[
    [
        "BLOCK_ID",
        "BLOCK_TIMESTAMP",
        "sender",
        "execute_msg.settle.auction_id",
        "amount",
        "recipient",
    ]
]

# rename columns
df_merge.rename(
    columns={
        "BLOCK_ID": "block_id",
        "BLOCK_TIMESTAMP": "timestamp",
        "execute_msg.settle.auction_id": "loot_id",
    },
    inplace=True,
)

# combine with rarity guide
df_rarity = pd.read_csv("SpaceLoot Rarity Guide w_ Colors - rarity.csv")
df_rarity = df_rarity[["Token ID", "Bullish Bear Rating"]]

# merge with rarity guide
df_merge = df_merge.merge(df_rarity, left_on="loot_id", right_on="Token ID")
df_merge.drop("Token ID", axis=1, inplace=True)
df_merge.rename(columns={"Bullish Bear Rating": "rarity"}, inplace=True)

# reorder columns
df_merge = df_merge[
    ["block_id", "timestamp", "sender", "recipient", "loot_id", "rarity", "amount"]
]

col1, col2 = st.columns(2)

col1.header("Distribution of Sales")
fig = px.histogram(df_merge, x="amount", nbins=20)
col1.plotly_chart(fig, use_container_width=True)

col2.header("Sales Price vs. Rarity")
fig = px.scatter(df_merge, x="rarity", y="amount")
col2.plotly_chart(fig, use_container_width=True)

st.header("Transactions Table")
st.write(df_merge)