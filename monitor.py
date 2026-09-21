import json
import os
from pathlib import Path

from curl_cffi import requests

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "").strip()
TEST_DISCORD = os.environ.get("TEST_DISCORD", "0").strip()

APPLE_URL = "https://www.apple.com/jp/shop/retail/pickup-message"

STORE_NUMBER = "R710"
STORE_NAME = "Apple 川崎"

PRODUCTS = {
    "MJX54J/A": "iPhone 18 Pro Max 256GB ブラック",
    "MJX64J/A": "iPhone 18 Pro Max 256GB シルバー",
    "MJX74J/A": "iPhone 18 Pro Max 256GB バーガンディ",
    "MJX84J/A": "iPhone 18 Pro Max 256GB グレイシャー",
    "MJX94J/A": "iPhone 18 Pro Max 512GB ブラック",
    "MJXA4J/A": "iPhone 18 Pro Max 512GB シルバー",
    "MJXC4J/A": "iPhone 18 Pro Max 512GB バーガンディ",
    "MJXD4J/A": "iPhone 18 Pro Max 512GB グレイシャー",
}

STATE_FILE = Path("stock_state.json")


def send_discord(message):
    if not DISCORD_WEBHOOK:
        raise RuntimeError("DISCORD_WEBHOOK が設定されていません。")

    response = requests.post(
        DISCORD_WEBHOOK,
        json={"content": message},
        timeout=20,
        impersonate="chrome",
    )

    response.raise_for_status()


def test_discord():
    print("==========================================")
    print("Discord テスト通知")
    print("==========================================")

    message = (
        "🔔 **Apple在庫監視 テスト通知**\n\n"
        "Discord Webhookの接続テストに成功しました。\n"
        "この通知はテスト用です。\n\n"
        "🏬 Apple 川崎\n"
        "📱 iPhone 18 Pro Max\n"
        "💾 256GB / 512GB\n"
    )

    send_discord(message)

    print("Discordへのテスト通知に成功しました。")


def load_state():
    if not STATE_FILE.exists():
        return {}

    try:
        return json.loads(
            STATE_FILE.read_text(encoding="utf-8")
        )
    except Exception:
        return {}


def save_state(state):
    STATE_FILE.write_text(
        json.dumps(
            state,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8",
    )


def check_stock():
    params = {
        "pl": "true",
        "mts.0": "regular",
        "store": STORE_NUMBER,
    }

    for index, part_number in enumerate(PRODUCTS):
        params[f"parts.{index}"] = part_number

    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": (
            "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7"
        ),
        "Referer": (
            "https://www.apple.com/jp/shop/buy-iphone/"
            "iphone-18-pro"
        ),
    }

    session = requests.Session(
        impersonate="chrome"
    )

    response = session.get(
        APPLE_URL,
        params=params,
        headers=headers,
        timeout=30,
    )

    print("Apple API HTTP:", response.status_code)
    print("Apple API URL:", response.url)

    if response.status_code == 541:
        raise RuntimeError(
            "AppleからHTTP 541でブロックされました。"
            "在庫なしとは判定していません。"
        )

    response.raise_for_status()

    data = response.json()

    stores = data.get(
        "body",
        {}
    ).get(
        "stores",
        []
    )

    if not isinstance(stores, list):
        raise RuntimeError(
            "Apple APIのstores形式が想定と異なります。"
        )

    target_store = next(
        (
            store
            for store in stores
            if store.get("storeNumber") == STORE_NUMBER
        ),
        None,
    )

    if target_store is None:
        raise RuntimeError(
            f"{STORE_NAME} ({STORE_NUMBER}) が"
            "Apple APIの応答にありません。"
        )

    parts_availability = target_store.get(
        "partsAvailability",
        {}
    )

    results = {}

    for part_number, product_name in PRODUCTS.items():

        part_data = parts_availability.get(
            part_number,
            {}
        )

        pickup_display = part_data.get(
            "pickupDisplay"
        )

        if pickup_display == "available":
            status = "available"

        elif pickup_display in (
            "unavailable",
            "ineligible",
            "ships-to-store",
        ):
            status = "unavailable"

        else:
            status = "unknown"

        results[part_number] = {
            "name": product_name,
            "status": status,
            "pickup_display": pickup_display,
        }

        print(
            f"{product_name}: "
            f"{pickup_display or 'unknown'}"
        )

    return results


def make_stock_message(items):

    lines = [
        "🚨 **Apple Store 在庫あり！**",
        "",
        f"🏬 {STORE_NAME}",
        "📱 iPhone 18 Pro Max",
        "",
    ]

    for item in items:
        lines.append(
            f"✅ {item['name']}"
        )

    lines.extend(
        [
            "",
            "🛒 Apple公式",
            "https://www.apple.com/jp/shop/buy-iphone/iphone-18-pro",
        ]
    )

    return "\n".join(lines)


def main():

    # ------------------------------------------
    # Discordテストモード
    # ------------------------------------------

    if TEST_DISCORD == "1":
        test_discord()
        return

    # ------------------------------------------
    # 通常の在庫監視
    # ------------------------------------------

    print("==========================================")
    print("Apple Store iPhone 在庫監視")
    print("==========================================")

    print(
        f"店舗：{STORE_NAME} ({STORE_NUMBER})"
    )

    print("機種：iPhone 18 Pro Max")
    print("容量：256GB / 512GB")
    print(
        "カラー：ブラック / シルバー / "
        "グレイシャー / バーガンディ"
    )

    print("==========================================")

    old_state = load_state()

    try:

        results = check_stock()

        newly_available_items = []

        for part_number, item in results.items():

            old_status = old_state.get(
                part_number,
                {}
            ).get(
                "status",
                "unavailable"
            )

            # 前回在庫なし
            # ↓
            # 今回在庫あり
            if (
                item["status"] == "available"
                and old_status != "available"
            ):
                newly_available_items.append(item)

        # 現在の状態を保存
        new_state = {
            part_number: {
                "name": item["name"],
                "status": item["status"],
            }
            for part_number, item in results.items()
        }

        save_state(new_state)

        # --------------------------------------
        # 新しく在庫が出た
        # --------------------------------------

        if newly_available_items:

            message = make_stock_message(
                newly_available_items
            )

            print(message)

            send_discord(message)

            print(
                "Discordへ在庫通知を送信しました。"
            )

        # --------------------------------------
        # 在庫はあるが前回から変化なし
        # --------------------------------------

        elif any(
            item["status"] == "available"
            for item in results.values()
        ):

            print(
                "在庫あり（前回から変化なし）。"
            )

            print(
                "Discord通知は送りません。"
            )

        # --------------------------------------
        # 在庫なし
        # --------------------------------------

        else:

            print(
                "現在、Apple 川崎に"
                "対象商品の在庫はありません。"
            )

    except Exception as e:

        print("==========================================")
        print("エラー")
        print(e)
        print("==========================================")

        # エラー時はDiscordへ通知
        # ただしWebhook自体がない場合は送信しない

        if DISCORD_WEBHOOK:

            try:

                send_discord(
                    "⚠️ **Apple在庫監視エラー**\n\n"
                    f"~~~{e}~~~\n\n"
                    "※このエラー発生時は"
                    "在庫状態を変更していません。"
                )

                print(
                    "Discordへエラー通知を送信しました。"
                )

            except Exception as discord_error:

                print(
                    "Discord通知にも失敗しました：",
                    discord_error
                )

        raise


if __name__ == "__main__":
    main()
