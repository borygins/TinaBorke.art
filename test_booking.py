import requests
import json


def test_booking():
    """Тестирование создания заявки"""
    url = "http://127.0.0.1:8000/api/booking"

    test_data = {
        "name": "Тестовый Клиент",
        "phone": "+79161234567",
        "service": "Тестовая услуга",
        "message": "Тестовое сообщение"
    }

    print("Отправка тестовой заявки...")
    try:
        response = requests.post(url, json=test_data, timeout=10)
        print(f"Статус код: {response.status_code}")
        print(f"Ответ сервера: {response.text}")

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Заявка создана! ID: {result.get('booking_id')}")
        else:
            print(f"❌ Ошибка: {response.status_code}")

    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")


if __name__ == "__main__":
    test_booking()