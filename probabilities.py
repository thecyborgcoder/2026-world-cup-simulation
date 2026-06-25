import math
import random

def get_expected_goals(elo_a, elo_b):
    """Calculate Expected Goals (xG) based on Elo difference."""
    diff = elo_a - elo_b
    xg_a = 1.3 * (2.0 ** (diff / 400.0))
    xg_b = 1.3 * (2.0 ** (-diff / 400.0))
    
    # Cap xG to avoid extreme edge cases breaking the math
    xg_a = min(max(xg_a, 0.1), 8.0)
    xg_b = min(max(xg_b, 0.1), 8.0)
    return xg_a, xg_b

def nbinom_prob(lambda_, r, k):
    """Calculate the Negative Binomial probability of k events given expected value lambda_ and dispersion r."""
    if lambda_ == 0:
        return 1.0 if k == 0 else 0.0
    p = lambda_ / (r + lambda_)
    coeff = math.exp(math.lgamma(k + r) - math.lgamma(k + 1) - math.lgamma(r))
    return coeff * (p ** k) * ((1 - p) ** r)

def generate_random_score(elo_a, elo_b, scale=1.0, is_knockout=False):
    """
    Generate a realistic scoreline using a Bivariate Poisson distribution 
    (with Dixon-Coles adjustment for full matches).
    `scale` parameter allows generating scores for Extra Time (e.g. scale=0.33)
    """
    xg_a, xg_b = get_expected_goals(elo_a, elo_b)
    
    if is_knockout:
        xg_a *= 0.80
        xg_b *= 0.80
        
    xg_a *= scale
    xg_b *= scale
    
    # Apply Dixon-Coles adjustment only for full matches (scale == 1.0)
    # A negative rho increases the probability of low-scoring draws.
    # rho = -0.10 yields ~28.9% draws for evenly matched teams (safely under 30%).
    rho = -0.10 if scale == 1.0 else 0.0
    
    max_goals = 10
    probs = {}
    r_dispersion = 5.0
    
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            prob = nbinom_prob(xg_a, r_dispersion, i) * nbinom_prob(xg_b, r_dispersion, j)
            
            # Dixon-Coles adjustment for low-scoring draws
            if rho != 0:
                if i == 0 and j == 0:
                    prob *= max(0, 1 - xg_a * xg_b * rho)
                elif i == 0 and j == 1:
                    prob *= max(0, 1 + xg_a * rho)
                elif i == 1 and j == 0:
                    prob *= max(0, 1 + xg_b * rho)
                elif i == 1 and j == 1:
                    prob *= max(0, 1 - rho)
                    
            probs[(i, j)] = prob
            
    # Cap draw probability for 300+ mismatches
    if abs(elo_a - elo_b) >= 300:
        draw_keys = [(i, i) for i in range(max_goals + 1)]
        current_draw_prob = sum(probs[k] for k in draw_keys)
        if current_draw_prob > 0.12:
            scale_factor = 0.12 / current_draw_prob
            excess = current_draw_prob - 0.12
            for k in draw_keys:
                probs[k] *= scale_factor
            
            # Re-distribute the excess probability to the favorite winning by 1 goal
            if elo_a >= elo_b:
                probs[(1, 0)] += excess
            else:
                probs[(0, 1)] += excess
                
    # Sample from the distribution
    total_prob = sum(probs.values())
    r = random.random() * total_prob
    cumulative = 0.0
    
    for (i, j), p in probs.items():
        cumulative += p
        if r <= cumulative:
            return i, j
            
    return 0, 0

if __name__ == '__main__':
    # Test
    print("Equal teams 90 mins:", [generate_random_score(1500, 1500) for _ in range(5)])
    print("A=+400 90 mins:", [generate_random_score(1900, 1500) for _ in range(5)])
    print("Equal teams ET:", [generate_random_score(1500, 1500, scale=0.33) for _ in range(5)])
