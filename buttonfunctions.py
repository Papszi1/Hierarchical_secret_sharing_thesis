import tkinter as tk
from tkinter import messagebox
from models import Participant
from tkinter import simpledialog, messagebox
from decomposition import distribute_shares
from decryption import recover_secret
import json
from tkinter import filedialog
import random
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import lagrange

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
        messagebox.showwarning("Selection Required", "Please select participants from the list.")
        return

    all_stolen_shares = []
    total_power = 0
    participant_ids = []

    for item_id in selected_items:
        item = main_tree.item(item_id)
        p_id = item['values'][0] 

        found_participant = None
        for level, participants in hierarchy.levels.items():
            for p in participants:
                if str(p.i) == str(p_id):
                    found_participant = p
                    break
            if found_participant: break
        
        if found_participant and found_participant.shares:
            all_stolen_shares.extend(found_participant.shares)
            total_power += found_participant.j
            participant_ids.append(str(p_id))

    h = hierarchy.h
    required_power = h + 1

    if total_power >= required_power:
        messagebox.showinfo("Access Granted", f"Power {total_power} is sufficient to decrypt normally.")
        return

    if not all_stolen_shares:
        messagebox.showerror("Error", "Could not retrieve shares for the selected IDs.")
        return

    sim_win = tk.Toplevel()
    sim_win.title("Collusion Attack Simulator")
    sim_win.geometry("800x600")
    
    tk.Label(sim_win, text="UNAUTHORIZED ACCESS ATTEMPT", 
             font=("Courier New", 12, "bold"), fg="red").pack(pady=10)

    txt = tk.Text(sim_win, font=("Courier New", 9), bg="#0a0a0a", fg="#33ff33")
    txt.pack(expand=True, fill="both", padx=15, pady=10)
    
    txt.insert(tk.END, f"[LOG] Colluding IDs: {', '.join(participant_ids)}\n")
    txt.insert(tk.END, f"[LOG] Combined Power: {total_power} / {required_power}\n")
    txt.insert(tk.END, "="*75 + "\n\n")

    fake_x = 999999
    from decryption import recover_secret 

    for i in range(1, 51):
        guess_y = random.randint(1, q - 1)
        test_points = all_stolen_shares + [[fake_x, guess_y]]
        
        while len(test_points) < required_power:
            test_points.append([random.randint(100, 100000), random.randint(1, q-1)])
            
        reconstruction_subset = test_points[:required_power]
        recovered_int = recover_secret(reconstruction_subset, h, q)
        
        try:
            byte_len = (recovered_int.bit_length() + 7) // 8
            if byte_len > 0:
                r_bytes = recovered_int.to_bytes(byte_len, 'big')
                r_str = r_bytes.decode('utf-8', errors='replace')
                clean_str = "".join(c if c.isprintable() else "?" for c in r_str)[:25]
            else:
                clean_str = "[ZERO_RESULT]"
        except:
            clean_str = "[MATH_ERROR]"

        txt.insert(tk.END, f"Trial {i:02d} | Result: {clean_str}\n")

    txt.insert(tk.END, "\n" + "="*75 + "\n")
    txt.insert(tk.END, "[RESULT] Brute-force failed. Perfect Secrecy maintained.")
    txt.config(state="disabled")



def run_bracketed_sharing(secret_str, hierarchy, q, conn, set1_input, set2_input):
    try:
        s1_levels = [int(x.strip()) for x in set1_input.split(",") if x.strip()]
        s2_levels = [int(x.strip()) for x in set2_input.split(",") if x.strip()]
        
        original_levels = hierarchy.levels.copy()

        hierarchy.levels = {j: original_levels[j] for j in s1_levels if j in original_levels}
        if hierarchy.levels:
            distribute_shares(secret_str, hierarchy, q, conn, extra=0)

        hierarchy.levels = {j: original_levels[j] for j in s2_levels if j in original_levels}
        if hierarchy.levels:
            distribute_shares(secret_str, hierarchy, q, conn, extra=400)

        hierarchy.levels = original_levels
        
        messagebox.showinfo("Success", "Shares distributed with bracket offsets!")
        return True 
        
    except Exception as e:
        messagebox.showerror("Error", f"Bracket distribution failed: {e}")
        return False

def run_bracketed_sharing(secret_str, hierarchy, q, conn, tree, set1_input, set2_input):
    try:
        s1_levels = [int(x.strip()) for x in set1_input.split(",") if x.strip()]
        s2_levels = [int(x.strip()) for x in set2_input.split(",") if x.strip()]
        
        h = hierarchy.h
        original_levels = hierarchy.levels.copy()

        set1_hierarchy_levels = {j: [] for j in range(1, h + 1)}
        for j in s1_levels:
            if j in original_levels:
                set1_hierarchy_levels[j] = original_levels[j]
        
        hierarchy.levels = set1_hierarchy_levels
        distribute_shares(secret_str, hierarchy, q, conn, extra=0)

        set2_hierarchy_levels = {j: [] for j in range(1, h + 1)}
        for j in s2_levels:
            if j in original_levels:
                set2_hierarchy_levels[j] = original_levels[j]
        
        hierarchy.levels = set2_hierarchy_levels
        distribute_shares(secret_str, hierarchy, q, conn, extra=400)

        hierarchy.levels = original_levels

        for item in tree.get_children():
            tree.delete(item)
            
        cursor = conn.cursor()
        cursor.execute("SELECT id, level, shares FROM participants")
        for row in cursor.fetchall():
            p_id, p_level, shares_json = row
            display_shares = (shares_json[:30] + "...") if shares_json else ""
            tree.insert("", "end", values=(p_id, p_level, display_shares))
            
        messagebox.showinfo("Success", "Bracketed shares distributed successfully!")

    except Exception as e:
        hierarchy.levels = original_levels
        messagebox.showerror("Error", f"An error occurred: {str(e)}")

def open_bracket_sharing_ui(hierarchy, q, conn, tree):
    top = tk.Toplevel()
    top.title("Bracketed Distribution")
    top.geometry("400x380")

    tk.Label(top, text="Secret to Share:", font=("Arial", 10, "bold")).pack(pady=10)
    secret_entry = tk.Entry(top, width=40)
    secret_entry.pack(pady=5)
    secret_entry.focus_set()

    tk.Label(top, text="Set 1 (No Offset):\n(e.g., 1,2)").pack(pady=5)
    set1_entry = tk.Entry(top, width=20)
    set1_entry.insert(0, "1,2")
    set1_entry.pack(pady=5)

    tk.Label(top, text="Set 2 (Offset +400):\n(e.g., 3,4,5)").pack(pady=5)
    set2_entry = tk.Entry(top, width=20)
    set2_entry.insert(0, "3,4,5")
    set2_entry.pack(pady=5)

    def start_process():
        print("Button Clicked!")
        val_secret = secret_entry.get()
        val_s1 = set1_entry.get()
        val_s2 = set2_entry.get()

        if not val_secret:
            messagebox.showwarning("Warning", "Secret is empty.")
            return
        
        run_bracketed_sharing(val_secret, hierarchy, q, conn, tree, val_s1, val_s2)
        
        top.destroy()

    btn = tk.Button(top, text="Execute Bracketed Distribution", 
                    command=start_process, 
                    bg="#2ecc71", fg="white", 
                    font=("Arial", 11, "bold"), 
                    padx=10, pady=10)
    btn.pack(pady=20)



def visualize_cubic_discovery():
    try:
        true_coeffs = [42, 5, 10, -4] 
        
        def f_true(x):
            return (true_coeffs[3] * x**3 + 
                    true_coeffs[2] * x**2 + 
                    true_coeffs[1] * x + 
                    true_coeffs[0])

        x_points = [0.5, 1.5, 3.0, 4.5] 
        y_points = [f_true(x) for x in x_points]

        plt.figure(figsize=(12, 8))
        x_plot = np.linspace(-1, 5.5, 250)

        colors = ['red', 'orange', 'purple', 'green']
        styles = [':', '--', '-.', '-']
        labels = [
            '1 Point (Constant/Flat)', 
            '2 Points (Linear Guess)', 
            '3 Points (Quadratic Guess)', 
            '4 Points (TRUE CUBIC LOCKED)'
        ]

        for i in range(1, 5):
            subset_x = x_points[:i]
            subset_y = y_points[:i]
            
            lp = lagrange(subset_x, subset_y)
            y_plot = lp(x_plot)
            
            plt.plot(x_plot, y_plot, linestyle=styles[i-1], color=colors[i-1], 
                     linewidth=2.5, label=labels[i-1], alpha=0.8)
            
            plt.scatter(subset_x, subset_y, color=colors[i-1], s=120, 
                        edgecolors='black', zorder=5)

        plt.title(f"Reconstructing a Cubic Secret (h=3)\n$f(x) = {true_coeffs[3]}x^3 + {true_coeffs[2]}x^2 + {true_coeffs[1]}x + {true_coeffs[0]}$", 
                  fontsize=14, fontweight='bold')
        plt.xlabel("X (Participant IDs)", fontsize=12)
        plt.ylabel("Y (Computed Shares)", fontsize=12)
        
        
        plt.axvline(0, color='black', linewidth=1, alpha=0.5)
        plt.axhline(0, color='black', linewidth=1, alpha=0.5)
        
        # Adjusting limits so the S-curve is visible
        plt.ylim(-200, 200) 
        plt.legend(loc='upper right')
        plt.grid(True, linestyle='--', alpha=0.4)
        
        plt.show()

    except Exception as e:
        messagebox.showerror("Error", f"Visualization failed: {e}")