
from typing import List

def maxProfit( prices: List[int]) -> int:
        
        max_dif_old = 0

        while len(prices) > 1:
            min_price = min(prices)
            min_id = prices.index(min_price)
            if min_id != len(prices) - 1:
                max_dif = max(prices[min_id:]) - min_price
                if max_dif_old < max_dif:
                    max_dif_old = max_dif
            prices.remove(min_price)
        return max_dif_old
    
height = [5,1,5,6,7,1,10]
maxProfit(height)