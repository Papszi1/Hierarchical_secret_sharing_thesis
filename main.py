from initialization import Hierarchy
from models import Participant
import sqlite3

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



conn.commit()
import tkinter as tk
from tkinter import ttk

root = tk.Tk()
root.title("Hierarchy Manager")
root.geometry("600x400")

label_h = tk.Label(root, text=f"Hierarchy height (h): {h}", font=("Arial", 14))
label_h.pack(pady=10)

# --- Top buttons ---
button_frame = tk.Frame(root)
button_frame.pack(pady=10)

btn_update = tk.Button(button_frame, text="Update Participants")
btn_distribute = tk.Button(button_frame, text="Distribute Shares")
btn_decrypt = tk.Button(button_frame, text="Decrypt Shares")

btn_update.pack(side=tk.LEFT, padx=5)
btn_distribute.pack(side=tk.LEFT, padx=5)
btn_decrypt.pack(side=tk.LEFT, padx=5)

# --- Participants label ---
label = tk.Label(root, text="Participants")
label.pack(anchor="w", padx=10)

# --- Table for participants ---
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

root.mainloop()
conn.close()