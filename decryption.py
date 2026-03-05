import json

def modular_inverse(n, q):
    return pow(n, -1, q)


def lagrange_interpolation(points, q):
    n = len(points)

    final_poly = [0] * n
    for i in range(n):
        xi, yi = points[i]

        basis = [1]
        denominator = 1
        
        for j in range(n):
            if i == j:
                continue
            xj, yj = points[j]

            new_basis = [0] * (len(basis) + 1)
            for deg, coeff in enumerate(basis):
                new_basis[deg] = (new_basis[deg] + coeff * (-xj)) % q
                new_basis[deg + 1] = (new_basis[deg + 1] + coeff) % q
            
            basis = new_basis

            denominator = (denominator * (xi - xj)) % q
        
        inv_den = modular_inverse(denominator, q)
        multiplier = (yi * inv_den) % q

        for deg in range(len(basis)):
            final_poly[deg] = (final_poly[deg] + basis[deg] * multiplier) % q
        
    return final_poly

def recover_secret(points, h, q):
    all_coeffs = lagrange_interpolation(points, q)

    secret_coeffs = all_coeffs[1:h+1]
    recovered_int = 0
    for k in secret_coeffs:
        recovered_int ^= k
    
    return recovered_int




if __name__ == "__main__":
    # --- SETUP ---
    Q_TEST = 2**256 - 2**32 - 977
    H_HEIGHT = 3
    SECRET_STR = "goat"
    
    # 1. Convert secret to int
    s_int = int.from_bytes(SECRET_STR.encode('utf-8'), byteorder='big')
    print(f"Original Secret Int: {s_int}")

    # 2. Manually create coefficients (k1, k2, k3)
    # k1 ^ k2 ^ k3 must = s_int
    import secrets
    k1 = secrets.randbelow(Q_TEST)
    k2 = secrets.randbelow(Q_TEST)
    k3 = s_int ^ k1 ^ k2
    coeffs = [k1, k2, k3]
    
    # 3. Random a0
    a0 = secrets.randbelow(Q_TEST)
    
    # 4. Create f(x) = a0 + k1*x + k2*x^2 + k3*x^3
    def f(x):
        return (a0 + k1*x + k2*x**2 + k3*x**3) % Q_TEST

    # 5. Generate points (We need h+1 = 4 points)
    # Let's pick random x values
    test_points = []
    for i in range(1, 5):
        x = i * 10 # Just some x values
        test_points.append([x, f(x)])
    
    print(f"Generated 4 points for the curve.")

    # --- THE RECOVERY TEST ---
    print("\n--- Running Recovery ---")
    recovered_s_int = recover_secret(test_points, H_HEIGHT, Q_TEST)
    
    print(f"Recovered Int: {recovered_s_int}")
    
    if s_int == recovered_s_int:
        print("SUCCESS! The secret was perfectly reconstructed.")
        # Convert back to string
        final_str = recovered_s_int.to_bytes((recovered_s_int.bit_length() + 7) // 8, 'big').decode('utf-8')
        print(f"Recovered String: {final_str}")
    else:
        print("FAILURE. The integers do not match.")
