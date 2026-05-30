import os
class config():
    NEWS_API_URL = "https://mboum-finance.p.rapidapi.com/v1/markets/news"
    HISTORY_API_URL = "https://mboum-finance.p.rapidapi.com/v1/markets/stock/history"
    API_Key = os.environ.get('9db85b5507msh1b60f7a0cd05f3ep179f98jsn6a12768d1c96')
    RapidAPI_Host = "mboum-finance.p.rapidapi.com"

    headers = {
        "X-RapidAPI-Key": API_Key,
        "X-RapidAPI-Host": RapidAPI_Host
    }
