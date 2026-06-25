import math

def nbinom_prob(lambda_, r, k):
    if lambda_ == 0:
        return 1.0 if k == 0 else 0.0
    p = lambda_ / (r + lambda_)
    coeff = math.exp(math.lgamma(k + r) - math.lgamma(k + 1) - math.lgamma(r))
    return coeff * (p ** k) * ((1 - p) ** r)

print("r=500 sum:", sum(nbinom_prob(1.3, 500, i) for i in range(10)))
print("r=500 k=0 vs poisson:", nbinom_prob(1.3, 500, 0), math.exp(-1.3))
print("r=2 k=0:", nbinom_prob(1.3, 2, 0))
print("r=2 k=3:", nbinom_prob(1.3, 2, 3))
