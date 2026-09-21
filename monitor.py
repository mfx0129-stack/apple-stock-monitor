import os
import requests

DISCORD_WEBHOOK = os.environ["DISCORD_WEBHOOK"]

APPLE_URL = "https://www.apple.com/jp/shop/fulfillment-messages"

# Apple 川崎
STORE = "R004"

# iPhone 18 Pro Max
# 256GB / 512GB
# ブラック / シルバー / グレイシャー / バーガンディ

PRODUCTS = [
    "iPhone 18 Pro Max 256GB ブラック",
    "iPhone 18 Pro Max 256GB シルバー",
    "iPhone 18 Pro Max 256GB グレイシャー",
    "iPhone 18 Pro Max 256GB バーガンディ",
    "iPhone 18 Pro Max 512GB ブラック",
    "iPhone 18 Pro Max 512GB シルバー",
    "iPhone 18 Pro Max 512GB グレイシャー",
    "iPhone 18 Pro Max 512GB バーガンディ",
]


def send_discord(message):
    response = requests.post(
        DISCORD_WEBHOOK,
        json={"content": message},
        timeout=20
    )

    response.raise_for_status()


def check_stock():

    params = {
        "location": "Kawasaki",
        "parts.0": "iPhone18ProMax"
    }

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(
        APPLE_URL,
        params=params,
        headers=headers,
        timeout=20
    )

    response.raise_for_status()

    data = response.json()

    print("Apple Store在庫情報を取得しました")

    stores = data.get("body", {}).get("content", {})

    print(stores)


def main():

    print("================================")
    print("Apple Store iPhone在庫監視")
    print("店舗：Apple 川崎")
    print("iPhone 18 Pro Max")
    print("256GB / 512GB")
    print("全カラー")
    print("================================")

    try:
        check_stock()

    except Exception as e:

        print("エラーが発生しました:")
        print(e)

        send_discord(
            "⚠️ Apple在庫監視でエラーが発生しました。\n"
            f"```{e}```"
        )


if __name__ == "__main__":
    main()
