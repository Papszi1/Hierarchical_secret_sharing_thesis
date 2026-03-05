import tkinter as tk
from tkinter import messagebox
from models import Participant
from tkinter import simpledialog, messagebox
from decomposition import distribute_shares
from decryption import recover_secret

def open_add_participants(root, tree, hierarchy, conn):
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
            messagebox.showerror("Error", f"Level must be an integer between 1 and {hierarchy.h}.")

    tk.Button(popup, text="Add Participant", command=add_participant).pack(pady=10)


def open_delete_participant(root, tree, hierarchy, conn):
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
            messagebox.showerror("Error", str(e))

    tk.Button(popup, text="Delete Participant", command=delete_participant).pack(pady=10)


def open_new_simulation(root, tree, hierarchy, conn, label_h):
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

            label_h.config(text=f"Hierarchy height (h): {new_h}")

            height_entry.delete(0, tk.END)
            popup.destroy()

        except ValueError:
            messagebox.showerror("Error", "Hierarchy height must be a positive integer.")

    tk.Button(popup, text="Start New Simulation", command=reset_hierarchy).pack(pady=10)



def handle_distribution(hierarchy, conn, tree, q):
    secret = simpledialog.askstring("Input", "Enter the secret to share:", show='*')
    
    if not secret:
        return
    try:
        distribute_shares(secret, hierarchy, q, conn)
        
        for item in tree.get_children():
            tree.delete(item)
            
        cursor = conn.cursor()
        cursor.execute("SELECT id, level, shares FROM participants")
        rows = cursor.fetchall()
        
        for row in rows:
            p_id, level, shares_json = row
            
            display_shares = shares_json[:30] + "..." if shares_json else ""
            tree.insert("", "end", values=(p_id, level, display_shares))
            
        messagebox.showinfo("Success", "Secret has been distributed to all participants!")
        
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {str(e)}")





def handle_decryption(hierarchy, tree, q):
    selected_items = tree.selection()
    
    if not selected_items:
        messagebox.showwarning("Selection Error", "Please select participants to decrypt.")
        return

    chosen_participants = []
    all_points = []
    
    for item in selected_items:
        row_values = tree.item(item)['values']
        p_id = row_values[0]
        
        participant = None
        for level in hierarchy.levels.values():
            for p in level:
                if p.i == p_id:
                    participant = p
                    break

        if participant and participant.shares:
            chosen_participants.append(participant)
            all_points.extend(participant.shares)
    print(chosen_participants)
    print(hierarchy.is_qualified(chosen_participants))
    if not hierarchy.is_qualified(chosen_participants)[0]:
        messagebox.showerror("Not Qualified", "The selected participants do not have enough power to decrypt.")
        return

    try:
        h = hierarchy.h
        recovered_int = recover_secret(all_points, h, q)
        
        recovered_str = recovered_int.to_bytes((recovered_int.bit_length() + 7) // 8, 'big').decode('utf-8')
        
        messagebox.showinfo("Secret Recovered", f"The hidden secret is:\n\n{recovered_str}")
        
    except Exception as e:
        messagebox.showerror("Decryption Failed", f"Could not recover secret. Error: {str(e)}")