import requests

url = "http://127.0.0.1:5000/api/chat"

data = {
    "message": "Summarized the abstract of The evolution of electricity price on the German day-ahead market before and after the energy switch?"
}

try:
    response = requests.post(
        url,
        json=data,
        proxies={"http": None, "https": None}  # ✅ Disable proxies here
    )
    response.raise_for_status()
    reply = response.json()
    print("Assistant reply:", reply["reply"])
except requests.exceptions.RequestException as e:
    print("Request failed:", e)
