import json
import os
from pathlib import Path

from curl_cffi import requests

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "").strip()
TEST_DISCORD = os.environ.get("TEST_DISCORD", "0").strip()

APPLE_URL = "https://www.apple.com/jp/shop/retail/pickup-message"

STORES = {
    "R710": "Apple 川崎",
    "R119": "Apple 渋谷",
}

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
        "🏬 Apple 川崎 / Apple 渋谷\n"
        "📱 iPhone 18 Pro Max\n"
        "💾 256GB / 512GB\n"
    )

    send_discord(message)

    print("Discordへのテスト通知に成功しました。")


def load_state():
    if not STATE_FILE.exists():
        return {}

    try:
        state = json.loads(
            STATE_FILE.read_text(encoding="utf-8")
        )

        # 旧形式
        # {
        #   "MJX54J/A": {"name": "...", "status": "..."}
        # }
        #
        # を新形式に移行する。
        if any(
            part_number in state
            for part_number in PRODUCTS
        ):
            return {
                "R710": state
            }

        return state

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


def check_stock(store_number, store_name):
    params = {
        "pl": "true",
        "mts.0": "regular",
        "store": store_number,
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

    print(f"Apple API HTTP ({store_name}):", response.status_code)
    print("Apple API URL:", response.url)

    if response.status_code == 541:
        raise RuntimeError(
            f"{store_name}：AppleからHTTP 541でブロックされました。"
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
            f"{store_name}：Apple APIのstores形式が想定と異なります。"
        )

    target_store = next(
        (
            store
            for store in stores
            if store.get("storeNumber") == store_number
        ),
        None,
    )

    if target_store is None:
        raise RuntimeError(
            f"{store_name} ({store_number}) が"
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
            f"{store_name} / {product_name}: "
            f"{pickup_display or 'unknown'}"
        )

    return results


def make_stock_message(store_name, items):
    lines = [
        "🚨 **Apple Store 在庫あり！**",
        "",
        f"🏬 {store_name}",
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


def make_error_message(store_name, error):
    return (
        "⚠️ **Apple在庫監視エラー**\n\n"
        f"🏬 {store_name}\n"
        f"~~~{error}~~~\n\n"
        "※このエラー発生時は、その店舗の在庫状態を変更していません。"
    )


def main():

    # ------------------------------------------
    # Discordテストモード
    # ------------------------------------------

    if TEST_DISCORD.lower() in ("1", "true"):
        test_discord()
        return

    # ------------------------------------------
    # 通常の在庫監視
    # ------------------------------------------

    print("==========================================")
    print("Apple Store iPhone 在庫監視")
    print("==========================================")

    print("監視店舗：")
    for store_number, store_name in STORES.items():
        print(f"  ・{store_name} ({store_number})")

    print("機種：iPhone 18 Pro Max")
    print("容量：256GB / 512GB")
    print(
        "カラー：ブラック / シルバー / "
        "グレイシャー / バーガンディ"
    )

    print("==========================================")

    old_state = load_state()
    new_state = dict(old_state)
    errors = []

    for store_number, store_name in STORES.items():

        try:
            print("------------------------------------------")
            print(f"{store_name} ({store_number}) を確認中")
            print("------------------------------------------")

            results = check_stock(
                store_number,
                store_name
            )

            old_store_state = old_state.get(
                store_number,
                {}
            )

            newly_available_items = []

            for part_number, item in results.items():

                old_status = old_store_state.get(
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

            # 現在の状態を店舗別に保存
            new_state[store_number] = {
                part_number: {
                    "name": item["name"],
                    "status": item["status"],
                }
                for part_number, item in results.items()
            }

            # --------------------------------------
            # 新しく在庫が出た
            # --------------------------------------

            if newly_available_items:

                message = make_stock_message(
                    store_name,
                    newly_available_items
                )

                print(message)

                send_discord(message)

                print(
                    f"{store_name}：Discordへ在庫通知を送信しました。"
                )

            # --------------------------------------
            # 在庫はあるが前回から変化なし
            # --------------------------------------

            elif any(
                item["status"] == "available"
                for item in results.values()
            ):

                print(
                    f"{store_name}：在庫あり（前回から変化なし）。"
                )

                print(
                    "Discord通知は送りません。"
                )

            # --------------------------------------
            # 在庫なし
            # --------------------------------------

            else:

                print(
                    f"{store_name}：現在、対象商品の在庫はありません。"
                )

        except Exception as e:

            errors.append(
                (store_name, e)
            )

            print("------------------------------------------")
            print(f"{store_name}：エラー")
            print(e)
            print("------------------------------------------")

            # エラー時は、その店舗の状態を変更しない
            # ただし他店舗の監視は継続する。

            if DISCORD_WEBHOOK:

                try:

                    send_discord(
                        make_error_message(
                            store_name,
                            e
                        )
                    )

                    print(
                        f"{store_name}：Discordへエラー通知を送信しました。"
                    )

                except Exception as discord_error:

                    print(
                        "Discord通知にも失敗しました：",
                        discord_error
                    )

    # 成功した店舗の状態だけ保存
    save_state(new_state)

    if errors:
        raise RuntimeError(
            "一部の店舗で在庫確認に失敗しました。"
        )


if __name__ == "__main__":
    main()
