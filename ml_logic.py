import joblib
import numpy as np
import random
from typing import Dict, List, Tuple, Optional

# Constants for RL
ALPHA = 0.1
GAMMA = 0.9
EPSILON = 0.1
EPISODES = 1000

# Karnataka Power Plant Data (Capacity in MW)
# Based on main-cesium.js
GENERATION_DATA = {
    "solar": {"capacity": 2150.0, "impact_value": 5, "damage_value": 0, "cost_value": 2},
    "wind": {"capacity": 76.0, "impact_value": 4, "damage_value": 0, "cost_value": 1},
    "hydro": {"capacity": 471.0, "impact_value": 3, "damage_value": 0, "cost_value": 3},
    "nuclear": {"capacity": 880.0, "impact_value": -1, "damage_value": -1, "cost_value": 8},
    "fossil": {"capacity": 5000.0, "impact_value": -5, "damage_value": -5, "cost_value": 9}, # Placeholder for import/backup
}

class DailyProfileGenerator:
    def __init__(self):
        self.solar_profile = self.generate_solar_profile()
        self.wind_profile = self.generate_wind_profile()

    def generate_solar_profile(self) -> np.ndarray:
        # 24h profile with 100 points per hour for smoothness? Or just per hour?
        # Let's do per hour for simplicity (0-23)
        hours = np.arange(24)
        
        # Base Bell Curve
        profile = np.zeros(24)
        day_mask = (hours > 6) & (hours < 18)
        profile[day_mask] = np.sin(((hours[day_mask] - 6) / 12) * np.pi)
        
        # Add "Clouds" (Noise)
        # Random drops in production
        noise = np.random.uniform(0.7, 1.0, 24)
        # Deep dip for a storm
        storm_start = np.random.randint(10, 15)
        noise[storm_start:storm_start+2] = 0.3 
        
        return profile * noise

    def generate_wind_profile(self) -> np.ndarray:
        hours = np.arange(24)
        # Diurnal: Low in morning, High in evening
        base = 0.4 + 0.3 * np.sin((hours - 14) / 24 * np.pi * 2)
        
        # Gusts (Random noise)
        gusts = np.random.uniform(-0.1, 0.2, 24)
        
        return np.clip(base + gusts, 0, 1.0)

# Global Generator
PROFILE_GENERATOR = DailyProfileGenerator()

class EnergyOptimizer:
    def __init__(self):
        self.q_table = {}
        self.model = self._load_model()
        self.epsilon = EPSILON

    def _load_model(self):
        try:
            return joblib.load("hgb_model.pkl")
        except FileNotFoundError:
            print("Warning: hgb_model.pkl not found.")
            return None

    def get_possible_actions(self, selected: set) -> List[str]:
        return [action for action in GENERATION_DATA.keys() if action not in selected]

    def get_reward(self, source: str, load_remaining: float, optimization_type: str = "cost") -> float:
        data = GENERATION_DATA[source]
        if optimization_type == "cost":
            cost = data["cost_value"]
            reward = -cost
            # Bonus for using cheaper/cleaner energy if it fits within capacity
            if load_remaining <= data["capacity"]:
                reward += 10
            reward += data["impact_value"]
        else:
            # Impact optimization (Eco-friendly)
            reward = abs(data["impact_value"] - data["damage_value"])
        return reward

    def choose_action(self, state: Tuple[str, float], epsilon: float, selected: set, optimization_type: str = "cost") -> Optional[str]:
        possible_actions = self.get_possible_actions(selected)
        if not possible_actions:
            return None

        if optimization_type == "cost":
            if random.random() < epsilon:
                return random.choice(possible_actions)
            return max(self.q_table.get(state, {}), key=self.q_table.get(state, {}).get, default=random.choice(possible_actions))
        else:
            # For impact, greedily choose the one with highest impact value (cleanest)
            return max(possible_actions, key=lambda action: GENERATION_DATA[action]["impact_value"])

    def update_q_table(self, state: Tuple[str, float], action: str, reward: float, next_state: Tuple[str, float]):
        current_q = self.q_table.get(state, {}).get(action, 0.0)
        next_max_q = max(self.q_table.get(next_state, {}).values(), default=0.0)
        self.q_table.setdefault(state, {})[action] = (1 - ALPHA) * current_q + ALPHA * (reward + GAMMA * next_max_q)

    def get_current_capacity(self, source: str, hour: float) -> float:
        data = GENERATION_DATA[source]
        max_cap = data["capacity"]
        
        # Use the pre-generated profiles
        # Interpolate for smoother values between hours
        h_idx = int(hour) % 24
        next_h_idx = (h_idx + 1) % 24
        frac = hour - int(hour)
        
        if source == "solar":
            val = PROFILE_GENERATOR.solar_profile[h_idx] * (1-frac) + PROFILE_GENERATOR.solar_profile[next_h_idx] * frac
            return max_cap * val
        
        elif source == "wind":
            val = PROFILE_GENERATOR.wind_profile[h_idx] * (1-frac) + PROFILE_GENERATOR.wind_profile[next_h_idx] * frac
            return max_cap * val
            
        return max_cap

    def train_agent(self, user_load: float, hour: float, optimization_type: str = "cost"):
        # Reset epsilon for training
        epsilon = self.epsilon
        
        if optimization_type == "cost":
             self.q_table = {}

        for _ in range(EPISODES):
            state = ("start", user_load)
            load_remaining = user_load
            selected = set()

            while load_remaining > 0:
                action = self.choose_action(state, epsilon, selected, optimization_type)
                if not action:
                    break

                selected.add(action)
                
                # Get realistic capacity for this hour
                current_capacity = self.get_current_capacity(action, hour)
                
                load_consumed = min(load_remaining, current_capacity)
                load_remaining -= load_consumed
                
                reward = self.get_reward(action, load_remaining, optimization_type)
                if load_consumed == 0:
                    reward -= 20 # Penalty for choosing unavailable source

                if optimization_type == "cost":
                    next_state = (action, load_remaining)
                    self.update_q_table(state, action, reward, next_state)
                    state = next_state
                else:
                    state = (action, load_remaining)

            epsilon = max(0.01, epsilon * 0.995)

    def optimize_distribution(self, current_load: float, hour: float, optimization_type: str = "cost") -> Dict[str, float]:
        """
        Returns a dictionary of source -> load_allocated (MW)
        """
        # Train first
        self.train_agent(current_load, hour, optimization_type)

        # Then execute policy
        state = ("start", current_load)
        load_remaining = current_load
        selected = set()
        distribution = {k: 0.0 for k in GENERATION_DATA.keys()}

        while load_remaining > 0:
            # Exploit only (epsilon=0)
            action = self.choose_action(state, 0.0, selected, optimization_type)
            if not action:
                if "fossil" not in selected:
                     action = "fossil"
                else:
                    break
            
            selected.add(action)
            
            current_capacity = self.get_current_capacity(action, hour)
            load_consumed = min(load_remaining, current_capacity)
            
            load_remaining -= load_consumed
            distribution[action] = load_consumed
            
            state = (action, load_remaining)

        return distribution
