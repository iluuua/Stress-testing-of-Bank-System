import tkinter as tk
from tkinter import Canvas, simpledialog, messagebox
import random
import copy


class Bank:
    def __init__(self, name, balance):
        self.name = name
        self.balance = balance
        self.debtors = {}
        self.creditors = {}

    def add_debt(self, bank, amount):
        self.debtors[bank] = amount
        bank.creditors[self] = amount


class BankSystemVisualizer:
    def __init__(self, lambda_c, lambda_f):
        self.banks = {}
        self.lambda_c = lambda_c
        self.lambda_f = lambda_f

        self.root = tk.Tk()
        self.root.title("Stress Testing Visualization")
        self.canvas = Canvas(self.root, width=800, height=600)
        self.canvas.pack()
        self.info_label = tk.Label(self.root, text="", font=("Arial", 14))
        self.info_label.pack()

        self.node_positions = {}
        self.node_shapes = {}
        self.lines = []
        self.paused = False
        self.previous_states = []
        self.bankrupt_banks = set()
        self.affected_banks = set()
        self.drag_data = {"x": 0, "y": 0, "item": None}

        self.setup_controls()

    def setup_controls(self):
        control_frame = tk.Frame(self.root)
        control_frame.pack()

        pause_button = tk.Button(control_frame, text="Пауза", command=self.pause)
        pause_button.grid(row=0, column=0)

        resume_button = tk.Button(control_frame, text="Продолжить", command=self.resume)
        resume_button.grid(row=0, column=1)

        rollback_button = tk.Button(control_frame, text="Откатить", command=self.rollback)
        rollback_button.grid(row=0, column=2)

        add_bank_button = tk.Button(control_frame, text="Добавить банк", command=self.add_bank)
        add_bank_button.grid(row=1, column=0)

        add_debt_button = tk.Button(control_frame, text="Добавить долг", command=self.add_debt)
        add_debt_button.grid(row=1, column=1)

        self.start_test_button = tk.Button(control_frame, text="Начать тест", command=self.start_stress_test)
        self.start_test_button.grid(row=1, column=2)

    def add_bank(self):
        name = simpledialog.askstring("Добавить банк", "Введите название банка:")
        balance = simpledialog.askinteger("Добавить банк", "Введите баланс банка:")
        if name and balance is not None:
            bank = Bank(name, balance)
            self.banks[name] = bank
            self.node_shapes[name] = {"oval": None, "text": None}  # Обновление для новых банков
            self.info_label.config(text=f"Банк '{name}' добавлен с балансом {balance}")
            self.draw_graph()

    def add_debt(self):
        from_bank = simpledialog.askstring("Добавить долг", "Введите банк-кредитор:")
        to_bank = simpledialog.askstring("Добавить долг", "Введите банк-дебитор:")
        amount = simpledialog.askinteger("Добавить долг", "Введите сумму долга:")
        if from_bank in self.banks and to_bank in self.banks and amount is not None:
            self.banks[from_bank].add_debt(self.banks[to_bank], amount)
            self.info_label.config(text=f"Долг в размере {amount} добавлен от {from_bank} к {to_bank}.")
            self.draw_graph()

    def start_stress_test(self):
        if not self.banks:
            messagebox.showwarning("Внимание", "Добавьте банки перед началом теста.")
            return
        start_bankrupt = simpledialog.askstring("Начать тест", "Введите банк, с которого начнется тест:")
        if start_bankrupt in self.banks:
            self.save_state()
            self.draw_graph()
            self.root.after(1000, lambda: self.stress_test(start_bankrupt))
            self.start_test_button.config(state=tk.DISABLED)
        else:
            messagebox.showwarning("Ошибка", "Выбранный банк не существует.")

    def draw_graph(self):
        self.canvas.delete("all")
        for bank_name, bank in self.banks.items():
            x, y = self.node_positions.get(bank_name, (random.randint(50, 750), random.randint(50, 550)))
            self.node_positions[bank_name] = (x, y)
            oval = self.canvas.create_oval(x - 30, y - 30, x + 30, y + 30, fill="green", tags="node")
            text = self.canvas.create_text(x, y, text=f"{bank_name}\n{bank.balance}", font=("Arial", 10), fill="white")
            self.node_shapes[bank_name] = {"oval": oval, "text": text}
            self.make_draggable(oval)

        for bank_name, bank in self.banks.items():
            for debtor, amount in bank.debtors.items():
                x1, y1 = self.node_positions[bank_name]
                x2, y2 = self.node_positions[debtor.name]
                line = self.canvas.create_line(x1, y1, x2, y2, arrow=tk.LAST, tags="line")
                amount_text = self.canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=str(amount), font=("Arial", 10))
                self.lines.append({"line": line, "amount_text": amount_text, "from": bank_name, "to": debtor.name})

    def update_bank_status(self, bank_name, status_text):
        bank = self.banks[bank_name]
        self.info_label.config(text=status_text)
        oval, text = self.node_shapes[bank_name]["oval"], self.node_shapes[bank_name]["text"]
        self.canvas.itemconfig(oval, fill="red")
        self.canvas.itemconfig(text, text=f"{bank_name}\n{bank.balance}")
        self.root.update_idletasks()

    def stress_test(self, bank_name):
        self.bankrupt_banks = {self.banks[bank_name]}
        self.affected_banks = self.bankrupt_banks.copy()

        self.update_bank_status(bank_name, f"Банк {bank_name} обанкротился!")

        def stress_test_step():
            if not self.paused and self.affected_banks:
                new_bankrupts = set()
                self.save_state()

                for bank in self.affected_banks:
                    losses = self.calculate_losses(bank)
                    for affected_bank, loss in losses.items():
                        affected_bank.balance -= loss
                        if affected_bank.balance < 0 and affected_bank not in self.bankrupt_banks:
                            new_bankrupts.add(affected_bank)
                            self.update_bank_status(affected_bank.name, f"Банк {affected_bank.name} обанкротился из-за потерь!")

                self.bankrupt_banks.update(new_bankrupts)
                self.affected_banks.clear()
                self.affected_banks.update(new_bankrupts)

            if self.affected_banks or self.paused:
                self.root.after(500, stress_test_step)

        stress_test_step()

    def calculate_losses(self, bank):
        losses = {}
        for creditor, debt_amount in bank.creditors.items():
            losses[creditor] = debt_amount * self.lambda_c
        for debtor, debt_amount in bank.debtors.items():
            losses[debtor] = debt_amount * self.lambda_f
        return losses

    def save_state(self):
        state_snapshot = copy.deepcopy({name: (bank.balance, bank.name) for name, bank in self.banks.items()})
        self.previous_states.append((state_snapshot, set(self.bankrupt_banks)))

    def rollback(self):
        if self.previous_states:
            last_state, last_bankrupts = self.previous_states.pop()
            for name, (balance, _) in last_state.items():
                self.banks[name].balance = balance
            self.bankrupt_banks = last_bankrupts.copy()
            self.affected_banks = self.bankrupt_banks.copy()
            self.refresh_display()
            self.info_label.config(text="Откат выполнен!")

    def refresh_display(self):
        for bank_name, shapes in self.node_shapes.items():
            bank = self.banks[bank_name]
            self.canvas.itemconfig(shapes["text"], text=f"{bank_name}\n{bank.balance}")
            fill_color = "red" if bank in self.bankrupt_banks else "green"
            self.canvas.itemconfig(shapes["oval"], fill=fill_color)

        for line in self.lines:
            bank_from = self.banks[line["from"]]
            bank_to = self.banks[line["to"]]
            x1, y1 = self.node_positions[line["from"]]
            x2, y2 = self.node_positions[line["to"]]
            self.canvas.coords(line["line"], x1, y1, x2, y2)
            self.canvas.coords(line["amount_text"], (x1 + x2) / 2, (y1 + y2) / 2)

    def pause(self):
        self.paused = True
        self.info_label.config(text="Стресс-тест приостановлен.")

    def resume(self):
        self.paused = False
        self.info_label.config(text="Стресс-тест продолжен.")

    def make_draggable(self, oval):
        oval_id = self.canvas.find_withtag(oval)[0]  # Получаем ID овала
        self.canvas.tag_bind(oval_id, "<ButtonPress-1>", self.on_start_drag)
        self.canvas.tag_bind(oval_id, "<B1-Motion>", self.on_drag)
        self.canvas.tag_bind(oval_id, "<ButtonRelease-1>", self.on_stop_drag)

    def on_start_drag(self, event):
        self.drag_data["item"] = self.canvas.find_closest(event.x, event.y)[0]
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

    def on_drag(self, event):
        item = self.drag_data["item"]
        dx = event.x - self.drag_data["x"]
        dy = event.y - self.drag_data["y"]
        self.canvas.move(item, dx, dy)

        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

        self.update_connected_lines(item)

    def on_stop_drag(self, event):
        item = self.drag_data["item"]
        self.update_positions_after_drag(item)

        self.drag_data["item"] = None

    def update_connected_lines(self, item):
        for line in self.lines:
            if line["from"] == self.canvas.gettags(item)[0] or line["to"] == self.canvas.gettags(item)[0]:
                from_coords = self.node_positions[line["from"]]
                to_coords = self.node_positions[line["to"]]
                self.canvas.coords(line["line"], from_coords[0], from_coords[1], to_coords[0], to_coords[1])
                self.canvas.coords(line["amount_text"], (from_coords[0] + to_coords[0]) / 2, (from_coords[1] + to_coords[1]) / 2)

    def update_positions_after_drag(self, item):
        for bank_name, shapes in self.node_shapes.items():
            if shapes["oval"] == item:
                x, y = self.canvas.coords(item)[:2]
                self.node_positions[bank_name] = (x + 30, y + 30)
                break

    def run(self):
        self.root.mainloop()


# Настройка параметров
bank_system = BankSystemVisualizer(lambda_c=1, lambda_f=0.5)
bank_system.run()
