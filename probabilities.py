import math
import random

def get_expected_goals(elo_a, elo_b):
    """Calculate Expected Goals (xG) based on Elo difference."""
    diff = elo_a - elo_b
    # Map Elo difference to xG. 
    # Average team scores ~1.3 goals per game.
    # An Elo diff of 400 is approximately a 10x difference in strength,
    # so we scale the xG up/down logarithmically.
    xg_a = 1.3 * (10.0 ** (diff / 800.0))
    xg_b = 1.3 * (10.0 ** (-diff / 800.0))
    
    # Cap xG to avoid extreme edge cases breaking the math
    xg_a = min(max(xg_a, 0.1), 8.0)
    xg_b = min(max(xg_b, 0.1), 8.0)
    return xg_a, xg_b

def poisson_prob(lambda_, k):
    """Calculate the Poisson probability of k events given expected value lambda_."""
    return (math.exp(-lambda_) * (lambda_ ** k)) / math.factorial(k)

def generate_random_score(elo_a, elo_b, scale=1.0):
    """
    Generate a realistic scoreline using a Bivariate Poisson distribution 
    (with Dixon-Coles adjustment for full matches).
    `scale` parameter allows generating scores for Extra Time (e.g. scale=0.33)
    """
    xg_a, xg_b = get_expected_goals(elo_a, elo_b)
    xg_a *= scale
    xg_b *= scale
    
    # Apply Dixon-Coles adjustment only for full matches (scale == 1.0)
    rho = 0.15 if scale == 1.0 else 0.0
    
    max_goals = 10
    probs = {}
    
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            prob = poisson_prob(xg_a, i) * poisson_prob(xg_b, j)
            
            # Dixon-Coles adjustment for low-scoring draws
            if rho > 0:
                if i == 0 and j == 0:
                    prob *= max(0, 1 - xg_a * xg_b * rho)
                elif i == 0 and j == 1:
                    prob *= max(0, 1 + xg_a * rho)
                elif i == 1 and j == 0:
                    prob *= max(0, 1 + xg_b * rho)
                elif i == 1 and j == 1:
                    prob *= max(0, 1 - rho)
                    
            probs[(i, j)] = prob
            
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
