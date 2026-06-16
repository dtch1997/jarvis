"""
Worked example of the eNTK and its eigenvalue-driven decay -- every number printed.

Model:  f(x; w) = w1 * x  +  w2 * x^2      (2 parameters)
Data:   3 points.  So the eNTK is 3x3 but rank <= 2  =>  one eigenvalue is 0.
Because f is linear in its features, the eNTK is EXACTLY constant during
training, so the decay law c_i(t) = c_i(0) * (1 - lr*lambda_i)^t is exact.
"""
import numpy as np
np.set_printoptions(precision=4, suppress=True)

# ----- data
x = np.array([1.0, 0.5, -1.0])
y = np.array([0.8, 0.5, 1.3])            # targets
print("x =", x, "   y =", y, "\n")

# ----- the gradient of f w.r.t. w at each point IS the feature vector [x, x^2]
#   grad_w f(x) = [ d f/d w1 , d f/d w2 ] = [ x , x^2 ]
J = np.stack([x, x**2], axis=1)          # Jacobian, shape [3 points, 2 params]
print("Jacobian J  (row i = grad_w f(x_i) = [x_i, x_i^2]):")
print(J, "\n")

# ----- empirical NTK:  K_ij = grad f(x_i) . grad f(x_j)  =  J J^T
K = J @ J.T
print("eNTK  K = J J^T   (K_ij = how much a step on point j moves prediction i):")
print(K, "\n")

# ----- eigendecomposition
lam, V = np.linalg.eigh(K)               # ascending
order = np.argsort(lam)[::-1]            # descending
lam, V = lam[order], V[:, order]
print("eigenvalues (descending):", lam)
print("  -> note the 3rd is ~0: only 2 params, so K is 'blind' to one direction\n")

# ----- start at w = 0  =>  f(X) = 0, residual r = f - y = -y
w = np.array([0.0, 0.0])
def predict(w): return J @ w
r0 = predict(w) - y
print("initial residual r0 = f - y =", r0)
c0 = V.T @ r0                            # residual written in the eigenbasis: r = sum_i c_i v_i
print("r0 in the eigenbasis,  c_i = v_i . r0 :", c0)
print("  -> c_3 (the lambda~0 mode) is the part NO gradient step can ever remove\n")

# ----- train with plain gradient descent, MSE sum-loss  =>  w <- w - lr * J^T r
lr = 0.25
print(f"predicted per-step shrink factor (1 - lr*lambda_i) with lr={lr}:")
print("   ", 1 - lr * lam, "\n")

print(f"{'step':>4} | {'c_1 (lam=%.2f)':>16} | {'c_2 (lam=%.2f)':>16} | {'c_3 (lam=%.2f)':>16} | {'train MSE':>10}"
      % (lam[0], lam[1], lam[2]))
print("-" * 78)
for t in range(0, 13):
    r = predict(w) - y
    c = V.T @ r
    if t in (0, 1, 2, 4, 8, 12):
        print(f"{t:>4} | {c[0]:>16.4f} | {c[1]:>16.4f} | {c[2]:>16.4f} | {(r**2).mean():>10.5f}")
    w = w - lr * (J.T @ r)               # gradient step

print()
print("Compare actual c_i(12) to the closed form c_i(0)*(1-lr*lambda_i)^12:")
pred12 = c0 * (1 - lr * lam) ** 12
print("   predicted:", pred12)
r = predict(w) - y; print("   actual:   ", V.T @ r)
print()
print(f"Irreducible (trapped) MSE  =  c_3^2 / n  =  {c0[2]**2 / 3:.5f}")
print(f"Final train MSE            =                {(r**2).mean():.5f}")
