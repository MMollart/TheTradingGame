"""
Manual test script for price fluctuation system

This script demonstrates the price fluctuation logic without requiring
a full database setup. Useful for quick validation and demonstration.
"""

import random
from datetime import datetime, timedelta


class MockPricingManager:
    """Mock version of PricingManager for testing"""
    
    MIN_MULTIPLIER = 0.5
    MAX_MULTIPLIER = 3.5  # Updated from 2.0
    SPREAD_PERCENTAGE = 0.2  # Updated from 0.1
    FLUCTUATION_PROBABILITY = 1.0  # Updated from 0.0333 (now 100% every 30 sec)
    FLUCTUATION_MAGNITUDE = 0.02
    MOMENTUM_WEIGHT = 0.6
    
    def _apply_spread(self, base_price: int, is_buy: bool) -> int:
        """Apply buy/sell spread"""
        spread = int(base_price * self.SPREAD_PERCENTAGE)
        spread = max(1, spread)
        if is_buy:
            return base_price + spread
        else:
            return max(1, base_price - spread)
    
    def _calculate_momentum_bias(self, price_history: list) -> float:
        """Calculate momentum from price history"""
        if len(price_history) < 2:
            return 0.0
        
        price_changes = []
        for i in range(1, len(price_history)):
            prev_price = price_history[i-1]
            curr_price = price_history[i]
            change_pct = (curr_price - prev_price) / prev_price if prev_price > 0 else 0.0
            price_changes.append(change_pct)
        
        if not price_changes:
            return 0.0
        
        avg_change = sum(price_changes) / len(price_changes)
        momentum = avg_change / 0.05
        momentum = max(-1.0, min(1.0, momentum))
        return momentum
    
    def _calculate_mean_reversion_pressure(self, current_price: int, baseline: int) -> float:
        """Calculate pressure to return to baseline"""
        if baseline == 0:
            return 0.0
        
        deviation = (current_price - baseline) / baseline
        pressure = -deviation
        max_deviation = max(self.MAX_MULTIPLIER - 1.0, 1.0 - self.MIN_MULTIPLIER)
        pressure = pressure / max_deviation
        pressure = max(-1.0, min(1.0, pressure))
        return pressure
    
    def apply_fluctuation_step(
        self,
        current_price: int,
        baseline: int,
        price_history: list,
        event_effect: float = 0.0
    ) -> tuple:
        """Apply one fluctuation step"""
        
        # Probability check - with 100% probability, this never skips
        if random.random() >= self.FLUCTUATION_PROBABILITY:
            return current_price, None
        
        # Calculate factors
        momentum = self._calculate_momentum_bias(price_history)
        reversion = self._calculate_mean_reversion_pressure(current_price, baseline)
        
        # Combine factors
        direction_bias = (
            self.MOMENTUM_WEIGHT * momentum +
            (1 - self.MOMENTUM_WEIGHT) * reversion +
            event_effect
        )
        
        # Random fluctuation with bias
        random_change = random.uniform(-self.FLUCTUATION_MAGNITUDE, self.FLUCTUATION_MAGNITUDE)
        
        if direction_bias > 0:
            biased_random = random.random()
            if biased_random < 0.5 + abs(direction_bias) * 0.5:
                random_change = abs(random_change)
        elif direction_bias < 0:
            biased_random = random.random()
            if biased_random < 0.5 + abs(direction_bias) * 0.5:
                random_change = -abs(random_change)
        
        # Apply change
        new_price = int(current_price * (1 + random_change))
        
        # Clamp to bounds
        min_price = int(baseline * self.MIN_MULTIPLIER)
        max_price = int(baseline * self.MAX_MULTIPLIER)
        new_price = max(min_price, min(max_price, new_price))
        
        return new_price, {
            'momentum': momentum,
            'reversion': reversion,
            'direction_bias': direction_bias,
            'random_change': random_change,
            'event_effect': event_effect
        }


def run_simulation():
    """Run a simulation of price fluctuations"""
    
    print("=" * 80)
    print("PRICE FLUCTUATION SIMULATION")
    print("=" * 80)
    print()
    
    manager = MockPricingManager()
    
    # Test scenarios
    scenarios = [
        {
            'name': 'Neutral Market (No Events)',
            'baseline': 100,
            'starting_price': 100,
            'event_effect': 0.0,
            'steps': 10  # 10 checks at 100% = 10 changes (represents ~5 minutes at 30s intervals)
        },
        {
            'name': 'Economic Recession (+0.3 effect)',
            'baseline': 100,
            'starting_price': 100,
            'event_effect': 0.3,
            'steps': 10
        },
        {
            'name': 'Automation Breakthrough (-0.2 effect)',
            'baseline': 100,
            'starting_price': 100,
            'event_effect': -0.2,
            'steps': 10
        },
        {
            'name': 'Mean Reversion Test (Starting High)',
            'baseline': 100,
            'starting_price': 180,
            'event_effect': 0.0,
            'steps': 20  # 20 checks = ~10 minutes
        }
    ]
    
    for scenario in scenarios:
        print(f"\n{'='*80}")
        print(f"Scenario: {scenario['name']}")
        print(f"Baseline: {scenario['baseline']}, Starting: {scenario['starting_price']}")
        print(f"Event Effect: {scenario['event_effect']:+.2f}")
        print(f"{'='*80}\n")
        
        baseline = scenario['baseline']
        current_price = scenario['starting_price']
        price_history = [current_price]
        
        change_count = 0
        total_steps = scenario['steps']
        
        for step in range(total_steps):
            new_price, info = manager.apply_fluctuation_step(
                current_price,
                baseline,
                price_history[-10:],  # Last 10 prices for momentum
                scenario['event_effect']
            )
            
            if info:  # Price changed
                change_count += 1
                current_price = new_price
                price_history.append(new_price)
                
                # Print every 5th change
                if change_count % 5 == 0:
                    deviation = ((current_price - baseline) / baseline) * 100
                    print(f"Change #{change_count:2d}: ${current_price:3d} ({deviation:+6.2f}% from baseline)")
                    print(f"  Momentum: {info['momentum']:+.3f}, Reversion: {info['reversion']:+.3f}, "
                          f"Bias: {info['direction_bias']:+.3f}")
        
        # Summary
        final_deviation = ((current_price - baseline) / baseline) * 100
        expected_changes = total_steps * manager.FLUCTUATION_PROBABILITY
        
        print(f"\nSummary:")
        print(f"  Total checks: {total_steps}")
        print(f"  Actual changes: {change_count} ({change_count/total_steps*100:.2f}%)")
        print(f"  Expected changes: ~{expected_changes:.1f} ({expected_changes/total_steps*100:.2f}%)")
        print(f"  Starting price: ${scenario['starting_price']}")
        print(f"  Final price: ${current_price}")
        print(f"  Final deviation: {final_deviation:+.2f}%")
        print(f"  Min price seen: ${min(price_history)}")
        print(f"  Max price seen: ${max(price_history)}")


def test_spread_maintenance():
    """Test that buy/sell spread is always maintained"""
    print("\n" + "="*80)
    print("SPREAD MAINTENANCE TEST")
    print("="*80 + "\n")
    
    manager = MockPricingManager()
    
    test_prices = [1, 5, 10, 50, 100, 200, 500, 1000]
    
    print("Testing buy/sell spread for various base prices:")
    print(f"{'Base Price':>12} | {'Sell Price':>12} | {'Buy Price':>12} | {'Spread':>12}")
    print("-" * 60)
    
    for base_price in test_prices:
        buy_price = manager._apply_spread(base_price, is_buy=True)
        sell_price = manager._apply_spread(base_price, is_buy=False)
        spread = buy_price - sell_price
        
        assert buy_price > sell_price, f"Buy price must be > sell price!"
        
        print(f"${base_price:10d} | ${sell_price:10d} | ${buy_price:10d} | ${spread:10d}")
    
    print("\n✓ All spreads maintain buy > sell constraint")


if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                     PRICE FLUCTUATION SYSTEM TEST                          ║
║                                                                            ║
║  This demonstrates the dynamic bank price fluctuation logic including:    ║
║  - Random variations (100% probability every 30 seconds, ±2% magnitude)   ║
║  - Momentum tracking (recent trends influence direction)                  ║
║  - Mean reversion (pull back to baseline over time)                       ║
║  - Event effects (game events bias price direction)                       ║
║  - Spread maintenance (buy price always > sell price)                     ║
║  - Increased bounds (0.5x to 3.5x baseline, 20% spread)                   ║
╚════════════════════════════════════════════════════════════════════════════╝
    """)
    
    random.seed(42)  # For reproducible results
    
    # Run tests
    test_spread_maintenance()
    run_simulation()
    
    print("\n" + "="*80)
    print("ALL TESTS COMPLETE")
    print("="*80)
