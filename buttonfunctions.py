import tkinter as tk
from tkinter import messagebox
from models import Participant
from tkinter import simpledialog, messagebox
from decomposition import distribute_shares
from decryption import recover_secret
import json
from tkinter import filedialog
import random

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



def handle_distribution_logic(secret, hierarchy, conn, tree, q):
    max_chars = q.bit_length() // 8 
    
    if len(secret.encode('utf-8')) > max_chars:
        messagebox.showerror("Secret Too Long", 
            f"The secret is {len(secret)} characters long.\n"
            f"Because we use a 256-bit prime (Q), the maximum length is {max_chars} characters.\n\n"
            "Please use a shorter secret or a smaller key file.")
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

def handle_manual_input(hierarchy, conn, tree, q):
    secret = simpledialog.askstring("Input", "Enter the secret to share:", show='*')
    if secret:
        handle_distribution_logic(secret, hierarchy, conn, tree, q)

def handle_file_input(hierarchy, conn, tree, q):
    file_path = filedialog.askopenfilename(
        title="Select Secret File",
        filetypes=[("Text files", "*.txt"), ("Key files", "*.key"), ("All files", "*.*")]
    )
    if file_path:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                secret_content = f.read().strip() 
            handle_distribution_logic(secret_content, hierarchy, conn, tree, q)
        except Exception as e:
            messagebox.showerror("File Error", f"Could not read file: {e}")


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


def open_attack_panel(hierarchy, q):
    attack_win = tk.Toplevel()
    attack_win.title("Security Sandbox: Manual Attack Simulation")
    attack_win.geometry("500x400")

    tk.Label(attack_win, text="Input manual shares to test the system's resilience", font=("Arial", 10, "bold")).pack(pady=10)
    
    tk.Label(attack_win, text="Enter shares as JSON list: [[x1, y1], [x2, y2], ...]").pack()
    input_area = tk.Text(attack_win, height=10, width=50)
    input_area.pack(padx=10, pady=5)

    def run_manual_test():
        try:
            raw_data = input_area.get("1.0", tk.END).strip()
            manual_points = json.loads(raw_data)
            
            recovered_int = recover_secret(manual_points, hierarchy.h, q)
            
            try:
                recovered_str = recovered_int.to_bytes((recovered_int.bit_length() + 7) // 8, 'big').decode('utf-8', errors='replace')
            except:
                recovered_str = "[Binary Data / Non-readable]"

            messagebox.showwarning("Reconstruction Result", 
                f"Recovered Integer: {str(recovered_int)[:50]}...\n\n"
                f"Decoded String: {recovered_str}\n\n"
                "As you can see, unauthorized or fake data results in total gibberish.")
                
        except Exception as e:
            messagebox.showerror("Format Error", "Please enter valid JSON points: [[x,y],...]")

    tk.Button(attack_win, text="Attempt Recovery", command=run_manual_test, bg="red", fg="white").pack(pady=10)


def run_collusion_brute_force(main_tree, hierarchy, q):
    selected_items = main_tree.selection()
    if not selected_items:
        messagebox.showwarning("Selection Required", "Please select the group of colluding participants from the list.")
        return

    all_stolen_shares = []
    total_power = 0
    participant_ids = []

    for item_id in selected_items:
        item = main_tree.item(item_id)
        p_id = item['values'][0]
        p_power = int(item['values'][1]) 
        p_shares = json.loads(item['values'][2]) 
        participant_ids.append(str(p_id))
        total_power += p_power
        all_stolen_shares.extend(p_shares)

    h = hierarchy.h
    required_power = h + 1

    if total_power >= required_power:
        messagebox.showinfo("Access Granted", 
            f"This group has Power {total_power} (Threshold {required_power}).\n"
            "They don't need to brute-force; they can just decrypt normally!")
        return

    sim_win = tk.Toplevel()
    sim_win.title("Collusion Attack Simulator")
    sim_win.geometry("800x600")
    
    tk.Label(sim_win, text="CRIMINAL COLLUSION LOG: UNAUTHORIZED ACCESS ATTEMPT", 
             font=("Courier New", 12, "bold"), fg="red").pack(pady=10)

    txt = tk.Text(sim_win, font=("Courier New", 9), bg="#0a0a0a", fg="#33ff33")
    txt.pack(expand=True, fill="both", padx=15, pady=10)
    
    missing_points = required_power - total_power
    txt.insert(tk.END, f"[LOG] Colluding IDs: {', '.join(participant_ids)}\n")
    txt.insert(tk.END, f"[LOG] Combined Power: {total_power} / Required: {required_power}\n")
    txt.insert(tk.END, f"[LOG] Security Gap: {missing_points} share(s) missing.\n")
    txt.insert(tk.END, f"[LOG] Initializing Brute-Force on Prime Field GF(Q)...\n")
    txt.insert(tk.END, "="*75 + "\n\n")

    fake_x = 123456789 
    from decryption import recover_secret 

    for i in range(1, 51):
        guess_y = random.randint(1, q - 1)
        
        test_points = all_stolen_shares + [[fake_x, guess_y]]
        
        reconstruction_subset = test_points[:required_power]
        
        recovered_int = recover_secret(reconstruction_subset, h, q)
        
        try:
            r_bytes = recovered_int.to_bytes((recovered_int.bit_length() + 7) // 8, 'big')
            r_str = r_bytes.decode('utf-8', errors='replace')
            clean_str = "".join(c if c.isprintable() else "?" for c in r_str)[:25]
        except:
            clean_str = "[NULL_DATA]"

        txt.insert(tk.END, f"Trial {i:02d} | Random Y Guess | Secret: {clean_str}\n")
        txt.see(tk.END)

    txt.insert(tk.END, "\n" + "="*75 + "\n")
    txt.insert(tk.END, "[RESULT] Brute-force failed. Zero information leaked.\n")
    txt.insert(tk.END, "[THEORY] Perfect Secrecy: T-1 shares yield no more info than 0 shares.")
    txt.config(state="disabled")