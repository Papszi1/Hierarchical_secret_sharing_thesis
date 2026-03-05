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
            print(p_points)
            shares_str = json.dumps(p_points)

            cursor.execute("UPDATE participants SET shares = ? WHERE id = ?",(shares_str, p.i))

    conn.commit()