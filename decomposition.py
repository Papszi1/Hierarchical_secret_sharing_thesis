import secrets
from initialization import Hierarchy
from models import Participant
import json

Q = 2**256 - 2**32 - 977
def string_to_int(secret_str):
    return int.from_bytes(secret_str.encode('utf-8'), byteorder='big')

def int_to_string(n):
    return n.to_bytes((n.bit_length() + 7) // 8, byteorder='big').decode('utf-8')

def generate_coefficients(secret_int, h, q):
    coeffs = [secrets.randbelow(q) for _ in range(h-1)]
    last_coeff = secret_int
    for c in coeffs:
        last_coeff ^= c
    coeffs.append(last_coeff)
    return coeffs

def evaluate_f(x, coeffs, a0, q):
    res = 0
    for k in reversed(coeffs):
        res = (res * x + k) % q
    
    res = (res * x + a0) % q
    return res

def distribute_shares(secret_str, hierarchy, q, conn):
    s_int = string_to_int(secret_str)
    h = hierarchy.h
    print(s_int)

    coeffs = generate_coefficients(s_int, h, q)
    a0 = secrets.randbelow(q)
    cursor = conn.cursor()

    for j in range(1, h + 1):
        participants_at_level = hierarchy.levels[j]

        for p in participants_at_level:
            p_points = []

            for m in range(1, j + 1):
                x_im = 1 + (m * p.i * h)
                y_im = evaluate_f(x_im, coeffs, a0, q)

                p_points.append((x_im, y_im))
            p.shares = p_points
            shares_str = json.dumps(p_points)

            cursor.execute("UPDATE participants SET shares = ? WHERE id = ?",(shares_str, p.i))

    conn.commit()


test_secret = "szia"
h_val = 3
hierarchy = Hierarchy(h_val)

# Add dummy participants to match your code
p1 = Participant(1, 1) # ID 1, Level 1 (Gets 1 point)
p2 = Participant(2, 2) # ID 2, Level 2 (Gets 2 points)
hierarchy.add_participant(p1)
hierarchy.add_participant(p2)

print(f"\n--- TEST START ---")
print(f"Original Secret String: {test_secret}")

# 2. Test Secret -> Int -> String
secret_int = string_to_int(test_secret)
print(f"Secret as Integer: {secret_int}")

# 3. Test XOR Coefficients
coeffs = generate_coefficients(secret_int, h_val, Q)
print(f"Generated {len(coeffs)} coefficients: {coeffs}")

recovered_int = 0
for c in coeffs:
    recovered_int ^= c

print(f"XOR Reconstruction Result: {recovered_int}")
print(f"XOR Success: {secret_int == recovered_int}")
print(f"Decoded String: {int_to_string(recovered_int)}")

# 4. Test Polynomial Evaluation (The "Share" Math)
a0_test = secrets.randbelow(Q)
print(f"\nRandom a0 generated: {a0_test}")

# Let's pick Participant 1 (ID=1, Level=1)
# According to your formula: x_im = 1 + (m * p.i * h)
# For m=1: x = 1 + (1 * 1 * 3) = 4
x_test = 1 + (1 * 1 * 3)
y_test = evaluate_f(x_test, coeffs, a0_test, Q)

print(f"Participant P_11 gets point: ({x_test}, {y_test})")

# 5. Manual Polynomial Verification
# f(x) = a0 + k1*x + k2*x^2 + k3*x^3
# Since coeffs = [k1, k2, k3]
k1, k2, k3 = coeffs
manual_calc = (a0_test + k1*x_test + k2*(x_test**2) + k3*(x_test**3)) % Q
print(f"Manual f({x_test}) calculation: {manual_calc}")
print(f"Curve Logic Success: {y_test == manual_calc}")

print(f"--- TEST END ---\n")