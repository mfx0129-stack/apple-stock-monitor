import os
import requests
import json

# =========================
# 設定
# =========================

DISCORD_WEBHOOK = os.environ["DISCORD_WEBHOOK"]

# Apple Store Japan
APPLE_URL = "https://www.apple.com/jp/shop/fulfillment-messages"

# 監視するApple製品
# 後からiPhoneのモデル・容量・カラーを追加できます
PRODUCTS = {
    "iPhone": [
        # 例：
        # "MXXXXJ/A"
    ]
}


def send_discord(message):
    data = {
        "content": message
    }

    response = requests.post(
        DISCORD_WEBHOOK,
        json=data,
        timeout=20
    )

    response.raise_for_status()


def check_stock(product_name, part_numbers):
    for part_number in part_numbers:

        params = {
            "pl": part_number,
            "mts": "regular"
        }

        response = requests.get(
            APPLE_URL,
            params=params,
            headers={
                "User-Agent": "Mozilla/5.0"
            },
            timeout=20
        )

        response.raise_for_status()

        data = response.json()

        stores = data.get("body", {}).get("content", {}).get("pickupMessage", {})

        if stores:
            print(f"{product_name} {part_number}")
            print(json.dumps(stores, ensure_ascii=False, indent=2))

            message = (
                "🍎 **Apple Store 在庫チェック**\n\n"
                f"商品: {product_name}\n"
                f"型番: {part_number}\n\n"
                "Apple Storeの在庫情報を確認してください。\n"
                "https://www.apple.com/jp/shop/buy-iphone"
            )

            send_discord(message)


def main():
    print("🍎 Apple Store iPhone在庫監視開始")

    for product_name, part_numbers in PRODUCTS.items():
        check_stock(product_name, part_numbers)

    print("チェック完了")


if __name__ == "__main__":
    main()
