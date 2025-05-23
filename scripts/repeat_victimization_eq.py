import numpy as np
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt

x = np.arange(1, 69)
y = np.array([80, 50, 37, 29, 24, 30, 32, 18, 24, 27, 39, 20, 25, 15, 21, 25, 5, 11,
              11, 20, 11, 12, 10, 18, 14,  8,  7,  5, 10, 10,  4, 13,  9,  5,  8,  7,
              14,  9,  4, 10, 11,  4,  8,  5,  9,  2,  5, 10,  4,  4,  4,  5,  2,  3,
               4,  6,  2,  5,  0,  1,  1,  3,  2,  2,  1,  2,  2,  2])

y_pct = np.array(y/np.sum(y))

mask = y_pct > 0
x_fit, y_fit = x[mask], y_pct[mask]

exp_model = lambda x, a, b, c: a * np.exp(b * x) + c
pow_model = lambda x, a, b, c: a * x**b + c
r2 = lambda y_true, y_pred: 1 - np.sum((y_true - y_pred)**2) / np.sum((y_true - np.mean(y_true))**2)

def fit(model, p0):
    popt, _ = curve_fit(model, x_fit, y_fit, p0=p0, bounds=([0, -np.inf, -np.inf], [np.inf, 0, np.inf]), maxfev=1000)
    return popt, r2(y_fit, model(x_fit, *popt))

c0 = np.median(y_fit[-10:])
a0 = max(y_fit.max() - c0, y_fit.max())
exp_popt, exp_r2 = fit(exp_model, [a0, -0.1, c0])
pow_popt, pow_r2 = fit(pow_model, [a0, -1.0, c0])

print(f"{'Exponential fit:':<20} y = {exp_popt[0]:.3f} * e^({exp_popt[1]:.3f}) + {exp_popt[2]:.3f}\n(R² = {exp_r2:.3f})")
print(f"{'Power law fit:':<20} y = {pow_popt[0]:.3f} * x^({pow_popt[1]:.3f}) + {pow_popt[2]:.3f}\n(R² = {pow_r2:.3f})")

# Plot part
plt.figure(figsize=(9, 5))
ax = plt.gca()

x_dense = np.linspace(x.min(), x.max(), 400)
plt.bar(x, y_pct, label="Data", alpha=0.7, edgecolor="black", color="#ABABAB")
ax.plot(x_dense, exp_model(x_dense, *exp_popt), "--", label=f"exp fit (R²={exp_r2:.3f})", color="#DC267F", linewidth=2.5)
ax.plot(x_dense, pow_model(x_dense, *pow_popt), "-.", label=f"pow fit (R²={pow_r2:.3f})", color="#648FFF", linewidth=2.5)

# Add fitted equation text
a_e, b_e, c_e = exp_popt
a_p, b_p, c_p = pow_popt

ax.text(0.98, 0.75, f"Exponential\n$y = {a_e:.3f} \\, e^{{{b_e:.3f}x}} {c_e:+.3f}$\n$R^2 = {exp_r2:.3f}$",
         transform=plt.gca().transAxes, ha="right", va="top", fontsize=9, color="#DC267F",
         bbox=dict(facecolor='white', edgecolor='#DC267F', boxstyle='round,pad=0.3'))

ax.text(0.98, 0.58, f"Power Law\n$y = {a_p:.3f} \\, x^{{{b_p:.3f}}} {c_p:+.3f}$\n$R^2 = {pow_r2:.3f}$",
         transform=plt.gca().transAxes, ha="right", va="top", fontsize=9, color="#648FFF",
         bbox=dict(facecolor='white', edgecolor='#648FFF', boxstyle='round,pad=0.3'))

plt.xlabel("Time before revictimization (months)", fontsize=14, fontweight="bold")
plt.ylabel("Relative Frequency (%)", fontsize=14, fontweight="bold")
plt.title("Model Fit (on Kleemans data)", fontsize=16, fontweight="bold")
plt.legend()
ax.grid(True, which='major')
ax.minorticks_on()
ax.grid(True, which='minor', linestyle=':', linewidth=0.5, alpha=0.6)
plt.tight_layout()
plt.show(dpi=300)