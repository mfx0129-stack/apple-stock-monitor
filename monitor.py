import os
import requests
from datetime import datetime, timezone, timedelta

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")

APPLE_URL = "https://www.apple.com/jp/shop/retail/pickup-message"

# Apple 川崎
STORE = "R004"

# iPhone 18 Pro Max
# 256GB / 512GB
# ブラック / シルバー / グレイシャー / バーガンディ
#
# Appleの実際の販売SKUは変更される可能性があるため、
# 下記SKUをAppleの商品ページから取得して確認する方式にしています。

PRODUCT_NAMES = [
    "iPhone 18 Pro Max 256GB ブラック",
    "iPhone 18 Pro Max 256GB シルバー",
    "iPhone 18 Pro Max 256GB グレイシャー",
    "iPhone 18 Pro Max 256GB バーガンディ",
    "iPhone 18 Pro Max 512GB ブラック",
    "iPhone 18 Pro Max 512GB シルバー",
    "iPhone 18 Pro Max 512GB グレイシャー",
    "iPhone 18 Pro Max 512GB バーガンディ",
]

# Appleの日本向けiPhone 18 Pro Max SKU
# ここはAppleの販売ページで確認できたSKUに差し替えて使用します。
PART_NUMBERS = []


def send_discord(message):
    if not DISCORD_WEBHOOK:
        print("DISCORD_WEBHOOKが設定されていません。")
        return

    response = requests.post(
        DISCORD_WEBHOOK,
        json={"content": message},
        timeout=20
    )

    response.raise_for_status()


def check_stock(part_numbers):
    if not part_numbers:
        raise RuntimeError(
            "AppleのiPhone 18 Pro Maxの販売SKUが設定されていません。"
        )

    params = {
        "pl": "true",
        "mts.0": "regular",
        "store": STORE,
    }

    for i, part_number in enumerate(part_numbers):
        params[f"parts.{i}"] = part_number

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/140.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.apple.com/jp/",
    }

    response = requests.get(
        APPLE_URL,
        params=params,
        headers=headers,
        timeout=30
    )

    print("Apple API HTTP:", response.status_code)

    response.raise_for_status()

    data = response.json()

    body = data.get("body", {})
    stores = body.get("stores", [])
    availability = body.get("partsAvailability", {})

    found = []

    for store in stores:
        store_number = store.get("storeNumber")

        if store_number != STORE:
            continue

        for part_number in part_numbers:
            part_data = availability.get(part_number, {})
            pickup = part_data.get("pickupDisplay")

            if pickup == "available":
                found.append(part_number)

    return found


def main():
    print("==========================================")
    print("Apple Store iPhone在庫監視")
    print("==========================================")
    print("店舗：Apple 川崎")
    print("機種：iPhone 18 Pro Max")
    print("容量：256GB / 512GB")
    print("カラー：ブラック / シルバー / グレイシャー / バーガンディ")
    print("==========================================")

    try:
        stock = check_stock(PART_NUMBERS)

        if stock:
            message = (
                "🚨 **Apple Store 在庫あり！**\n\n"
                "📱 iPhone 18 Pro Max\n"
                "🏬 Apple 川崎\n\n"
                "在庫ありSKU:\n"
                + "\n".join(f"・{x}" for x in stock)
                + "\n\n"
                "🔗 https://www.apple.com/jp/shop/buy-iphone/iphone-18-pro"
            )

            print(message)
            send_discord(message)

        else:
            print("現在、在庫はありません。")

    except Exception as e:
        print("==========================================")
        print("エラー")
        print(e)
        print("==========================================")

        send_discord(
            "⚠️ **Apple在庫監視エラー**\n\n"
            f"```{e}```"
        )


if __name__ == "__main__":
    main()
