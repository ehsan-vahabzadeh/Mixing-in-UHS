# This script demonstrates the use of methods from the GenerationForecastApi
# to retrieve day-ahead forecast data for wind and solar generation from the Elexon API.

# from datetime import datetime
# import pandas as pd
# import elexonpy
# import numpy as np
# # Initialize API client
# api_client = elexonpy.ApiClient()
# DemandApi = elexonpy.DemandApi(api_client)

# # Define date range for fetching day-ahead wind and solar forecast data
# from_date = datetime(2024, 7, 1,0,0,0)
# to_date = datetime(2024, 7, 2,0,0,0)  # Note: Maximum data output range is 7 days

# # Fetch day-ahead forecast data for wind and solar from API
# df_demand = DemandApi.demand_actual_total_get(
#     _from=from_date,
#     to=to_date,
#     format='dataframe'
# )
# df_demand["settlement_period"] = np.arange(0, len(df_demand))
# df_demand.sort_values(by=['start_time'], inplace=True)
# print(df_demand)
# imbalance_settlement_api = elexonpy.IndicativeImbalanceSettlementApi()
# df_price = imbalance_settlement_api.balancing_settlement_system_prices_settlement_date_get(
#     settlement_date = '2024-07-01',
#     format='dataframe'
# )
# print(df_price)
# df_price_minus7 = imbalance_settlement_api.balancing_settlement_system_prices_settlement_date_get(
#     settlement_date = '2024-06-24',
#     format='dataframe'
# )
# print(df_price_minus7)

def isPalindrome( x):
        """
        :type x: int
        :rtype: bool
        """
        if x < 10:
            return False
        str_x = str(x)
        x_no = len(str_x)
        mid = int(x_no/2)
        print(str_x[0:mid])
        print(str_x[-1:mid:-1])
        print(str_x)
        if x_no % 2 == 0 and str_x[0:mid] == str_x[-1:mid-1:-1]:
            return True 
        
        elif x_no % 2 == 1 and str_x[0:mid] == str_x[-1:mid:-1]:
            return True
        else:
            return False

xx = isPalindrome(121)        