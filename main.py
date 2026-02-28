from initialization import Hierarchy
from models import Participant
import sqlite3
import tkinter as tk
from tkinter import ttk

conn = sqlite3.connect("hierarchy.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS hierarchy_settings (
    h INTEGER NOT NULL
)
""")

cursor.execute("SELECT h FROM hierarchy_settings")
row = cursor.fetchone()
h = 3
if row is None:
    cursor.execute("INSERT INTO hierarchy_settings (h) VALUES (?)", (h,))
    conn.commit()
    print(f"Hierarchy height stored: {h}")
else:
    h = row[0]
    print(f"Hierarchy height loaded from DB: {h}")
hierarchy = Hierarchy(h)


cursor.execute("""
CREATE TABLE IF NOT EXISTS participants (
    id INTEGER PRIMARY KEY,
    level INTEGER NOT NULL,
    shares TEXT
)
""")
cursor.execute("SELECT id, level, shares FROM participants")
rows = cursor.fetchall()

for row in rows:
    p_id, level, shares_str = row
    participant = Participant(p_id, level)

    if shares_str:
        participant.shares = [int(s) for s in shares_str.split(",")] 

    hierarchy.add_participant(participant)

def open_add_participants():
    popup = tk.Toplevel(root)
    popup.title("Add Participant")
    popup.geometry("300x150")

    tk.Label(popup, text=f"Add Participant (Level 1-{hierarchy.h})").pack(pady=5)
    level_entry = tk.Entry(popup)
    level_entry.pack(pady=5)

    def add_participant():
        try:
            level = int(level_entry.get())
            if not (1 <= level <= hierarchy.h):
                raise ValueError

            cursor = conn.cursor()
            cursor.execute("SELECT MAX(id) FROM participants")
            max_id = cursor.fetchone()[0]
            next_id = 1 if max_id is None else max_id + 1

            cursor.execute("INSERT INTO participants (id, level, shares) VALUES (?, ?, ?)", 
                           (next_id, level, None))
            conn.commit()
            participant = Participant(next_id, level)
            hierarchy.add_participant(participant)
            tree.insert("", tk.END, values=(participant.i, participant.j, ""))
            level_entry.delete(0, tk.END)

        except ValueError:
            tk.messagebox.showerror("Error", f"Level must be an integer between 1 and {hierarchy.h}.")

    tk.Button(popup, text="Add Participant", command=add_participant).pack(pady=10)

def open_delete_participant():
    popup = tk.Toplevel(root)
    popup.title("Delete Participant")
    popup.geometry("300x150")

    tk.Label(popup, text="Delete Participant (Enter ID)").pack(pady=5)
    delete_entry = tk.Entry(popup)
    delete_entry.pack(pady=5)

    def delete_participant():
        try:
            p_id = int(delete_entry.get())

            cursor = conn.cursor()
            cursor.execute("DELETE FROM participants WHERE id = ?", (p_id,))
            if cursor.rowcount == 0:
                raise ValueError("Participant ID not found")
            conn.commit()

            for level_list in hierarchy.levels.values():
                level_list[:] = [p for p in level_list if p.i != p_id]
            for item in tree.get_children():
                if int(tree.item(item, "values")[0]) == p_id:
                    tree.delete(item)
                    break

            delete_entry.delete(0, tk.END)

        except ValueError as e:
            tk.messagebox.showerror("Error", str(e))

    tk.Button(popup, text="Delete Participant", command=delete_participant).pack(pady=10)

def open_new_simulation():
    popup = tk.Toplevel(root)
    popup.title("New Simulation")
    popup.geometry("300x150")

    tk.Label(popup, text="Enter new hierarchy height (h)").pack(pady=5)
    height_entry = tk.Entry(popup)
    height_entry.pack(pady=5)

    def reset_hierarchy():
        try:
            new_h = int(height_entry.get())
            if new_h <= 0:
                raise ValueError

            cursor = conn.cursor()

            cursor.execute("DELETE FROM participants")
            conn.commit()
            cursor.execute("DELETE FROM hierarchy_settings")
            cursor.execute("INSERT INTO hierarchy_settings (h) VALUES (?)", (new_h,))
            conn.commit()

            hierarchy.h = new_h
            hierarchy.levels = {j: [] for j in range(1, new_h + 1)}

            for item in tree.get_children():
                tree.delete(item)

            h = new_h
            label_h.config(text=f"Hierarchy height (h): {new_h}")

            height_entry.delete(0, tk.END)
            popup.destroy()  

        except ValueError:
            tk.messagebox.showerror("Error", "Hierarchy height must be a positive integer.")

    
    tk.Button(popup, text="Start New Simulation", command=reset_hierarchy).pack(pady=10)

conn.commit()

root = tk.Tk()
root.title("Hierarchy Manager")
root.geometry("600x400")

label_h = tk.Label(root, text=f"Hierarchy height (h): {h}", font=("Arial", 14))
label_h.pack(pady=10)

button_frame = tk.Frame(root)
button_frame.pack(pady=10)

btn_add = tk.Button(button_frame, text="Add Participants", command=open_add_participants)
btn_delete = tk.Button(button_frame, text="Delete Participant", command=open_delete_participant)
btn_new_sim = tk.Button(button_frame, text="New simulation", command=open_new_simulation)

btn_distribute = tk.Button(button_frame, text="Distribute Shares")
btn_decrypt = tk.Button(button_frame, text="Decrypt Shares")

btn_add.pack(side=tk.LEFT, padx=5)
btn_delete.pack(side=tk.LEFT, padx=5)
btn_new_sim.pack(side=tk.LEFT, padx=5)
btn_distribute.pack(side=tk.LEFT, padx=5)
btn_decrypt.pack(side=tk.LEFT, padx=5)

label = tk.Label(root, text="Participants")
label.pack(anchor="w", padx=10)
columns = ("ID", "Level", "Shares")

tree = ttk.Treeview(root, columns=columns, show="headings")
tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

for col in columns:
    tree.heading(col, text=col)
    tree.column(col, anchor="center")

for level, participants in hierarchy.levels.items():
    for p in participants:
        shares_str = ", ".join(map(str, p.shares)) if p.shares else ""
        tree.insert("", tk.END, values=(p.i, p.j, shares_str))

scrollbar = ttk.Scrollbar(root, orient="vertical", command=tree.yview)
tree.configure(yscrollcommand=scrollbar.set)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

root.mainloop()
conn.close()