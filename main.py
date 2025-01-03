import copy
import json
import logging
import tkinter as tk
from tkinter import Tk
from datetime import datetime
from tkinter import messagebox
import sqlite3
import requests
import multiprocessing


class VKBot:
    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'ru,en;q=0.9',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 YaBrowser/24.12.0.0 Safari/537.36',
    }
    params = {
        'auth_key': '3a548454f70391405932bf4769761acc',
        'viewer_id': '214163323'
    }
    def buy_lot(self, lot_id: int, user_id: int):
        param = copy.deepcopy(self.params)
        param['act'] = 'a_program_say'
        data = {
            'ch': f'u{user_id}',
            'text': f'Купить лот {lot_id}',
            'context': '1',
            'messages[0][message]': f'Купить лот {lot_id}',
        }
        requests.post(url="https://vip3.activeusers.ru/app.php", params=param, data=data, headers=self.headers)

    def monitoring(self, item_id: int, max_price: int, user_id: int):
        db_conn = sqlite3.connect('lots.db')
        cursor = db_conn.cursor()

        while True:
            cheapest_lot_id, price = self.get_cheapest_lot(item_id, max_price)
            if cheapest_lot_id:
                self.buy_lot(cheapest_lot_id, user_id)
                time_of_purchase = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute("INSERT INTO purchases (item_id, price, time) VALUES (?, ?, ?)",
                               (cheapest_lot_id, price, time_of_purchase))
                db_conn.commit()

    def get_cheapest_lot(self, item_id: int, max_price: int):
        param = copy.deepcopy(self.params)
        param['act'] = 'a_program_run'
        data = f"code=51132l145l691d2fbd8b124d57&context=1&vars[item][id]={item_id}"
        response = requests.post(url="https://vip3.activeusers.ru/app.php", params=param, data=data,
                                 headers=self.headers)
        messages = response.json()
        list_lots = messages['message'][0]['message']
        list_lots = list_lots.split("\n")
        for lot in list_lots:
            try:
                count = int(lot.split(" ")[0].split('*')[0])
                price = int(lot.split(" ")[2])
                lot_id = int(lot.split(" ")[4].strip().replace("(", '').replace(")", ''))
                price_for_one = price / count
                logging.debug(lot)
                if price_for_one <= max_price:
                    return lot_id, price_for_one
            except Exception as ex:
                continue
        return None, None


class VKBotGUI(Tk):
    def __init__(self):
        super().__init__()
        self._id_current_item: int
        self.bot = VKBot()
        self.monitoring_process = None
        self.title("VK Bot")
        self.geometry("400x400")
        self.configure(bg="#f0f0f0")

        self.create_widgets()

        self.db = sqlite3.connect('lots.db')
        self.cursor = self.db.cursor()
        self.create_table()

    def create_table(self):
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER,
            price INTEGER,
            time TEXT
        )
        ''')
        self.db.commit()

    def create_widgets(self):
        self.lots_button = tk.Button(self, text="View Lots", width=20)
        self.lots_button.pack(pady=10)

        self.user_id_label = tk.Label(self, text="Enter User ID", width=20)
        self.user_id_label.pack(pady=10)

        self.user_id_entry = tk.Entry(self, width=20)
        self.user_id_entry.pack(pady=10)

        self.create_items_button()

        self.price_label = tk.Label(self, text="Enter Max Price", bg="#f0f0f0")
        self.price_label.pack(pady=5)

        self.price_entry = tk.Entry(self, width=40)
        self.price_entry.pack(pady=5)

        self.monitor_button = tk.Button(self, text="Monitor Item", command=self.start_monitoring, width=20)
        self.monitor_button.pack(pady=10)

        self.stop_button = tk.Button(self, text="Stop", command=self.stop_monitoring, width=20)
        self.stop_button.pack(pady=10)

        self.logs_panel = tk.LabelFrame(self, )

    def create_items_button(self):
        with open("items.json", "r") as f:
            items = json.load(f)
            for item in items["items"]:
                item_id = item["id"]
                title = item["title"]
                tk.Button(self, text=title, command=lambda item_id=item_id: self.id_current_item(item_id)).pack(pady=5)

    # def view_lots(self):
    #     self.bot.cursor.execute("SELECT * FROM purchases")
    #     purchases = self.bot.cursor.fetchall()
    #     if purchases:
    #         lots_text = "Your purchases:\n"
    #         for purchase in purchases:
    #             lots_text +=
    #     else:
    #         messagebox.showinfo("Purchased Lots", "No purchases made yet.")

    def id_current_item(self, item_id):
        self._id_current_item = item_id

    def start_monitoring(self):
        user_id = self.user_id_entry.get()
        if not user_id.isdigit():
            messagebox.showerror("Error", "User ID should be a number.")
            return
        max_price = self.price_entry.get()
        if not max_price.isdigit():
            messagebox.showerror("Error", "Max Price should be a number.")
            return
        if not hasattr(self, '_id_current_item'):
            messagebox.showerror("Error", "Please select an item ID.")
            return

        item_id = self._id_current_item
        max_price = int(max_price)
        user_id = int(user_id)

        if self.monitoring_process and self.monitoring_process.is_alive():
            messagebox.showerror("Error", "Monitoring is already running.")
            return

        # Запуск нового процесса
        self.monitoring_process = multiprocessing.Process(target=self.bot.monitoring,
                                                          args=(item_id, max_price, user_id))
        self.monitoring_process.start()
        messagebox.showinfo("Monitoring", f"Started monitoring item ID {item_id} with max price {max_price}₽.")

    def stop_monitoring(self):
        if self.monitoring_process and self.monitoring_process.is_alive():
            self.monitoring_process.terminate()
            self.monitoring_process = None
            messagebox.showinfo("Stop", "Monitoring stopped.")
        else:
            messagebox.showerror("Error", "Monitoring is not running.")


if __name__ == '__main__':
    multiprocessing.freeze_support()  # Рекомендуется для Windows
    app = VKBotGUI()
    app.mainloop()

