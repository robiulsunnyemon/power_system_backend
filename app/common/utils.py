import math

def calculate_trust_score(raw_score: float) -> float:
    """
    Normalizes raw points into a trust score (0-100) using a logistic function.
    Formula: 100 / (1 + exp(-raw / 1000))
    """
    if raw_score <= 0:
        return 50.0  # Base score for new/neutral users
    
    # Using the provided formula
    score = 100 / (1 + math.exp(-raw_score / 1000))
    return round(score, 2)
