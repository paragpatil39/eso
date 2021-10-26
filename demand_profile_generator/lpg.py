import pandas as pd

# Initialize the load profile generator
number_of_time_steps = 24*365
date_rng = pd.date_range('1/1/2020', periods=number_of_time_steps,freq='H')
index=pd.Index(date_rng)

#Import the daily demand file
demand=pd.read_excel("demand_24.xlsx")
df_load_profile_yearly=pd.concat([demand]*365).set_index(index)

df_load_profile_yearly.to_csv("elec_demand.csv")
print(df_load_profile_yearly)
