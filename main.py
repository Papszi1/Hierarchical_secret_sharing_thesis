from buttonfunctions import open_add_participants, open_delete_participant, open_new_simulation, handle_decryption, handle_manual_input, handle_file_input, open_attack_panel, run_collusion_brute_force, open_bracket_sharing_ui, visualize_cubic_discovery
from initialization import Hierarchy
from models import Participant
from tkinter import ttk
import tkinter as tk
import sqlite3
import json

Q = 2**256 - 2**32 - 977
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
    print(f"Hierarchy height stored: {h}, points needed to decrypt the data: {h+1}")
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
        try:
            participant.shares = json.loads(shares_str)
            print(participant.shares)
        except json.JSONDecodeError:
            print(f"Warning: Old data format found for ID {p_id}, skipping shares.")
            participant.shares = []

    hierarchy.add_participant(participant)
conn.commit()

root = tk.Tk()
root.title("Hierarchy Manager")
root.geometry("2000x400")

label_h = tk.Label(root, text=f"Hierarchy height (h): {hierarchy.h}, points needed to decrypt the data: {hierarchy.h + 1}", font=("Arial", 14))
label_h.pack(pady=10)

button_frame = tk.Frame(root)
button_frame.pack(pady=10)

btn_add = tk.Button(button_frame, text="Add Participant",
                    command=lambda: open_add_participants(root, tree, hierarchy, conn))
btn_delete = tk.Button(button_frame, text="Delete Participant",
                       command=lambda: open_delete_participant(root, tree, hierarchy, conn))
btn_new_sim = tk.Button(button_frame, text="New Simulation",
                        command=lambda: open_new_simulation(root, tree, hierarchy, conn, label_h))
btn_distribute = tk.Button(
    button_frame, 
    text="Type Secret",
    command=lambda: handle_manual_input(hierarchy, conn, tree, Q)
)
btn_file = tk.Button(
    button_frame, 
    text="Upload Key File",
    command=lambda: handle_file_input(hierarchy, conn, tree, Q)
)
btn_decrypt = tk.Button(button_frame, text="Decrypt Secret",
    command=lambda: handle_decryption(hierarchy, tree, Q))
btn_attack = tk.Button(
    button_frame, 
    text="Security Sandbox",
    command=lambda: open_attack_panel(hierarchy, Q), 
    bg="#f44336", 
    fg="white"
)
btn_brute = tk.Button(
    button_frame, 
    text="Brute-Force Sim", 
    command=lambda: run_collusion_brute_force(tree, hierarchy, Q),
    bg="#607D8B", 
    fg="white",
    font=("Arial", 10, "bold")
)
bracket_btn = tk.Button(
    button_frame, 
    text="Bracketed Sharing", 
    command=lambda: open_bracket_sharing_ui(hierarchy, Q, conn, tree)
)
visual_btn = tk.Button(
    button_frame, 
    text="Visual Demo", 
    command=lambda: visualize_cubic_discovery(),
    bg="#3498db", 
    fg="white",
    font=("Arial", 10, "bold")
)
btn_add.pack(side=tk.LEFT, padx=5)
btn_delete.pack(side=tk.LEFT, padx=5)
btn_new_sim.pack(side=tk.LEFT, padx=5)
btn_distribute.pack(side=tk.LEFT, padx=5)
btn_file.pack(side=tk.LEFT, padx=5)
btn_decrypt.pack(side=tk.LEFT, padx=5)
btn_attack.pack(side=tk.LEFT, padx=5)
btn_brute.pack(side=tk.LEFT, padx=5)
bracket_btn.pack(side=tk.LEFT, padx=5)
visual_btn.pack(side=tk.LEFT, padx=10, pady=10)

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
        shares_display = json.dumps(p.shares) if p.shares else ""
        tree.insert("", tk.END, values=(p.i, p.j, shares_display))
root.mainloop()
conn.close()