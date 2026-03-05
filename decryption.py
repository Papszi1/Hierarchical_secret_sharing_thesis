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