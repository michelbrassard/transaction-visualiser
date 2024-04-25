import pandas as pd

previous_day = 0
previous_date = None
week_number = 1

# Helper function for defining the relative week
# Relative week is used as the y coordinate inside the pivot table
def get_relative_week_number(day, date):
    global previous_day
    global previous_date
    global week_number
    
    days_difference = (date - previous_date) // 7 
    week_number = week_number + days_difference.days
    
    if previous_day > day:
        week_number = week_number + 1
    
    previous_day = day
    previous_date = date
    
    return week_number

def get_grouped(df_transactions):
    global previous_day
    global previous_date
    global week_number
    
    df_grouped = df_transactions.groupby("date")["amount"].sum().reset_index()
    df_grouped['date'] = pd.to_datetime(df_grouped['date'])
    df_grouped['Day'] = df_grouped['date'].dt.weekday
    
    #setting the previous date, it is first created as None
    previous_date = df_grouped.iloc[0]['date']
    
    df_grouped['Week'] = df_grouped.apply(lambda row: get_relative_week_number(date=row["date"], day=row["Day"]), axis=1)
    
    #resetting values
    previous_day = 0
    week_number = 1
    previous_date = df_grouped.iloc[0]['date']
    
    df_grouped["day_name"] = df_grouped["date"].dt.day_name()
    
    
    #df_grouped["amount"] = df_grouped["amount"] * -1
    
    return df_grouped

# Receives the parsed dataframe
def get_pivot(df_transactions):
    grouped = get_grouped(df_transactions)
    pivot_table = grouped.pivot_table(index='Week', columns='Day', values='amount', aggfunc='sum')
    pivot_table = pivot_table.fillna(0)
    return pivot_table