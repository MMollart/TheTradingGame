"""
Tests for price fluctuation system
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from pricing_manager import PricingManager
from models import GameSession, PriceHistory, GameStatus
from game_constants import ResourceType, BANK_INITIAL_PRICES


class TestPriceFluctuationLogic:
    """Test the core price fluctuation logic"""
    
    def test_momentum_calculation_upward(self, db: Session, sample_game):
        """Test momentum calculation with upward trend"""
        game_code = sample_game["game_code"]
        
        # Get game
        game = db.query(GameSession).filter(
            GameSession.game_code == game_code.upper()
        ).first()
        
        pricing_mgr = PricingManager(db)
        
        # Create upward price trend
        baseline = 100
        prices = [90, 95, 100, 105, 110]  # Steadily increasing
        
        for i, price in enumerate(prices):
            record = PriceHistory(
                game_session_id=game.id,
                resource_type='food',
                buy_price=price + 5,
                sell_price=price - 5,
                baseline_price=baseline,
                triggered_by_trade=False,
                timestamp=datetime.utcnow() - timedelta(minutes=2-i*0.5)
            )
            db.add(record)
        db.commit()
        
        # Calculate momentum
        momentum = pricing_mgr._calculate_momentum_bias(game.id, 'food')
        
        # Should be positive (upward momentum)
        assert momentum > 0, "Upward trend should produce positive momentum"
    
    def test_momentum_calculation_downward(self, db: Session, sample_game):
        """Test momentum calculation with downward trend"""
        game_code = sample_game["game_code"]
        
        game = db.query(GameSession).filter(
            GameSession.game_code == game_code.upper()
        ).first()
        
        pricing_mgr = PricingManager(db)
        
        # Create downward price trend
        baseline = 100
        prices = [110, 105, 100, 95, 90]  # Steadily decreasing
        
        for i, price in enumerate(prices):
            record = PriceHistory(
                game_session_id=game.id,
                resource_type='food',
                buy_price=price + 5,
                sell_price=price - 5,
                baseline_price=baseline,
                triggered_by_trade=False,
                timestamp=datetime.utcnow() - timedelta(minutes=2-i*0.5)
            )
            db.add(record)
        db.commit()
        
        momentum = pricing_mgr._calculate_momentum_bias(game.id, 'food')
        
        # Should be negative (downward momentum)
        assert momentum < 0, "Downward trend should produce negative momentum"
    
    def test_momentum_calculation_flat(self, db: Session, sample_game):
        """Test momentum calculation with stable prices"""
        game_code = sample_game["game_code"]
        
        game = db.query(GameSession).filter(
            GameSession.game_code == game_code.upper()
        ).first()
        
        pricing_mgr = PricingManager(db)
        
        # Create flat price trend
        baseline = 100
        prices = [100, 100, 100, 100, 100]
        
        for i, price in enumerate(prices):
            record = PriceHistory(
                game_session_id=game.id,
                resource_type='food',
                buy_price=price + 5,
                sell_price=price - 5,
                baseline_price=baseline,
                triggered_by_trade=False,
                timestamp=datetime.utcnow() - timedelta(minutes=2-i*0.5)
            )
            db.add(record)
        db.commit()
        
        momentum = pricing_mgr._calculate_momentum_bias(game.id, 'food')
        
        # Should be close to zero
        assert abs(momentum) < 0.1, "Flat trend should produce near-zero momentum"
    
    def test_mean_reversion_above_baseline(self, db: Session):
        """Test mean reversion when price is above baseline"""
        pricing_mgr = PricingManager(db)
        
        baseline = 100
        current_price = 150  # 50% above baseline
        
        pressure = pricing_mgr._calculate_mean_reversion_pressure(current_price, baseline)
        
        # Should be negative (pressure to decrease)
        assert pressure < 0, "Price above baseline should have downward pressure"
    
    def test_mean_reversion_below_baseline(self, db: Session):
        """Test mean reversion when price is below baseline"""
        pricing_mgr = PricingManager(db)
        
        baseline = 100
        current_price = 70  # 30% below baseline
        
        pressure = pricing_mgr._calculate_mean_reversion_pressure(current_price, baseline)
        
        # Should be positive (pressure to increase)
        assert pressure > 0, "Price below baseline should have upward pressure"
    
    def test_mean_reversion_at_baseline(self, db: Session):
        """Test mean reversion when price is at baseline"""
        pricing_mgr = PricingManager(db)
        
        baseline = 100
        current_price = 100
        
        pressure = pricing_mgr._calculate_mean_reversion_pressure(current_price, baseline)
        
        # Should be zero
        assert pressure == 0, "Price at baseline should have no pressure"
    
    def test_price_spread_maintained(self, db: Session):
        """Test that buy price is always greater than sell price"""
        pricing_mgr = PricingManager(db)
        
        # Test various base prices
        for base_price in [1, 10, 50, 100, 500, 1000]:
            buy_price = pricing_mgr._apply_spread(base_price, is_buy=True)
            sell_price = pricing_mgr._apply_spread(base_price, is_buy=False)
            
            assert buy_price > sell_price, \
                f"Buy price ({buy_price}) must be > sell price ({sell_price}) for base {base_price}"
    
    def test_fluctuation_respects_bounds(self, db: Session, sample_game):
        """Test that fluctuations stay within MIN/MAX multipliers"""
        game_code = sample_game["game_code"]
        
        game = db.query(GameSession).filter(
            GameSession.game_code == game_code.upper()
        ).first()
        
        pricing_mgr = PricingManager(db)
        
        # Initialize prices
        prices = pricing_mgr.initialize_bank_prices(game_code)
        game.game_state = {'bank_prices': prices}
        db.commit()
        
        # Apply many fluctuations
        for _ in range(100):
            prices, changed = pricing_mgr.apply_random_fluctuation(game_code, prices)
        
        # Check all prices are within bounds
        for resource_type, price_info in prices.items():
            baseline = price_info['baseline']
            buy_price = price_info['buy_price']
            sell_price = price_info['sell_price']
            
            min_price = baseline * pricing_mgr.MIN_MULTIPLIER
            max_price = baseline * pricing_mgr.MAX_MULTIPLIER
            
            assert buy_price >= min_price, \
                f"{resource_type} buy price {buy_price} below minimum {min_price}"
            assert buy_price <= max_price, \
                f"{resource_type} buy price {buy_price} above maximum {max_price}"
            assert sell_price >= min_price, \
                f"{resource_type} sell price {sell_price} below minimum {min_price}"
            assert sell_price <= max_price, \
                f"{resource_type} sell price {sell_price} above maximum {max_price}"


class TestEventPriceEffects:
    """Test game event effects on prices"""
    
    def test_event_effect_positive(self, db: Session, sample_game):
        """Test that positive event effect increases prices"""
        game_code = sample_game["game_code"]
        
        game = db.query(GameSession).filter(
            GameSession.game_code == game_code.upper()
        ).first()
        
        pricing_mgr = PricingManager(db)
        
        # Initialize prices
        prices = pricing_mgr.initialize_bank_prices(game_code)
        
        # Add economic recession (positive price effect)
        game.game_state = {
            'bank_prices': prices,
            'active_events': {
                'recession': {
                    'severity': 3,
                    'cycles_remaining': 2
                }
            }
        }
        db.commit()
        
        # Get event effects
        event_effects = pricing_mgr._load_event_price_effects()
        resource_effects = pricing_mgr._get_active_event_effect(game, event_effects)
        
        # Should have positive effects on all resources (recession increases prices)
        assert len(resource_effects) > 0, "Should have event effects"
        for resource, effect in resource_effects.items():
            assert effect > 0, f"Recession should have positive price effect on {resource}"
    
    def test_event_effect_negative(self, db: Session, sample_game):
        """Test that negative event effect decreases prices"""
        game_code = sample_game["game_code"]
        
        game = db.query(GameSession).filter(
            GameSession.game_code == game_code.upper()
        ).first()
        
        pricing_mgr = PricingManager(db)
        
        # Initialize prices
        prices = pricing_mgr.initialize_bank_prices(game_code)
        
        # Add automation breakthrough (negative price effect)
        game.game_state = {
            'bank_prices': prices,
            'active_events': {
                'automation_breakthrough': {
                    'target_team': '1',
                    'severity': 3,
                    'cycles_remaining': 2
                }
            }
        }
        db.commit()
        
        # Get event effects
        event_effects = pricing_mgr._load_event_price_effects()
        resource_effects = pricing_mgr._get_active_event_effect(game, event_effects)
        
        # Should have negative effects on all resources (automation reduces prices)
        assert len(resource_effects) > 0, "Should have event effects"
        for resource, effect in resource_effects.items():
            assert effect < 0, f"Automation breakthrough should have negative price effect on {resource}"
    
    def test_event_effect_resource_specific(self, db: Session, sample_game):
        """Test that resource-specific events only affect those resources"""
        game_code = sample_game["game_code"]
        
        game = db.query(GameSession).filter(
            GameSession.game_code == game_code.upper()
        ).first()
        
        pricing_mgr = PricingManager(db)
        
        # Initialize prices
        prices = pricing_mgr.initialize_bank_prices(game_code)
        
        # Add drought (affects only food and raw_materials)
        game.game_state = {
            'bank_prices': prices,
            'active_events': {
                'drought': {
                    'severity': 3,
                    'cycles_remaining': 2
                }
            }
        }
        db.commit()
        
        # Get event effects
        event_effects = pricing_mgr._load_event_price_effects()
        resource_effects = pricing_mgr._get_active_event_effect(game, event_effects)
        
        # Should only affect food and raw_materials
        assert 'food' in resource_effects, "Drought should affect food"
        assert 'raw_materials' in resource_effects, "Drought should affect raw_materials"
        assert 'electrical_goods' not in resource_effects, "Drought should not affect electrical goods"
        assert 'medical_goods' not in resource_effects, "Drought should not affect medical goods"
    
    def test_no_event_effects(self, db: Session, sample_game):
        """Test that no events means no effects"""
        game_code = sample_game["game_code"]
        
        game = db.query(GameSession).filter(
            GameSession.game_code == game_code.upper()
        ).first()
        
        pricing_mgr = PricingManager(db)
        
        # Initialize prices with no events
        prices = pricing_mgr.initialize_bank_prices(game_code)
        game.game_state = {'bank_prices': prices}
        db.commit()
        
        # Get event effects
        event_effects = pricing_mgr._load_event_price_effects()
        resource_effects = pricing_mgr._get_active_event_effect(game, event_effects)
        
        # Should be empty
        assert len(resource_effects) == 0, "No events should mean no effects"


class TestFluctuationProbability:
    """Test fluctuation probability mechanics"""
    
    def test_fluctuation_probability_range(self, db: Session, sample_game):
        """Test that fluctuation probability is reasonable"""
        game_code = sample_game["game_code"]
        
        game = db.query(GameSession).filter(
            GameSession.game_code == game_code.upper()
        ).first()
        
        pricing_mgr = PricingManager(db)
        
        # Initialize prices
        prices = pricing_mgr.initialize_bank_prices(game_code)
        game.game_state = {'bank_prices': prices}
        db.commit()
        
        # Run many iterations and count changes
        total_iterations = 1000
        total_changes = 0
        
        for _ in range(total_iterations):
            prices, changed = pricing_mgr.apply_random_fluctuation(game_code, prices)
            total_changes += len(changed)
        
        # Expected changes per resource: 1000 * 0.0333 = ~33 changes
        # With 4 resources: ~132 total changes
        # Allow for statistical variance (20-50 changes per resource)
        expected_per_resource = total_iterations * pricing_mgr.FLUCTUATION_PROBABILITY
        assert 20 < (total_changes / 4) < 50, \
            f"Change frequency {total_changes/4} per resource outside expected range"
    
    def test_fluctuation_magnitude(self, db: Session, sample_game):
        """Test that individual fluctuations are within ±2%"""
        game_code = sample_game["game_code"]
        
        game = db.query(GameSession).filter(
            GameSession.game_code == game_code.upper()
        ).first()
        
        pricing_mgr = PricingManager(db)
        
        # Initialize prices
        prices = pricing_mgr.initialize_bank_prices(game_code)
        game.game_state = {'bank_prices': prices}
        db.commit()
        
        # Track price changes
        for _ in range(100):
            old_prices = prices.copy()
            prices, changed = pricing_mgr.apply_random_fluctuation(game_code, prices)
            
            for resource in changed:
                old_middle = (old_prices[resource]['buy_price'] + old_prices[resource]['sell_price']) / 2
                new_middle = (prices[resource]['buy_price'] + prices[resource]['sell_price']) / 2
                
                if old_middle > 0:
                    change_pct = abs((new_middle - old_middle) / old_middle)
                    # Allow slightly more than 2% due to rounding and spread adjustments
                    assert change_pct <= 0.025, \
                        f"Change {change_pct*100:.2f}% exceeds maximum 2.5%"


class TestPriceHistory:
    """Test price history recording"""
    
    def test_fluctuation_records_history(self, db: Session, sample_game):
        """Test that fluctuations are recorded in price history"""
        game_code = sample_game["game_code"]
        
        game = db.query(GameSession).filter(
            GameSession.game_code == game_code.upper()
        ).first()
        
        pricing_mgr = PricingManager(db)
        
        # Initialize prices
        prices = pricing_mgr.initialize_bank_prices(game_code)
        game.game_state = {'bank_prices': prices}
        db.commit()
        
        # Get initial history count
        initial_count = db.query(PriceHistory).filter(
            PriceHistory.game_session_id == game.id
        ).count()
        
        # Apply fluctuations until we get a change
        max_attempts = 100
        for _ in range(max_attempts):
            prices, changed = pricing_mgr.apply_random_fluctuation(game_code, prices)
            if changed:
                break
        
        # Check history increased
        final_count = db.query(PriceHistory).filter(
            PriceHistory.game_session_id == game.id
        ).count()
        
        assert final_count > initial_count, "Fluctuation should record price history"
    
    def test_history_not_triggered_by_trade(self, db: Session, sample_game):
        """Test that fluctuation history is marked as not trade-triggered"""
        game_code = sample_game["game_code"]
        
        game = db.query(GameSession).filter(
            GameSession.game_code == game_code.upper()
        ).first()
        
        pricing_mgr = PricingManager(db)
        
        # Initialize prices
        prices = pricing_mgr.initialize_bank_prices(game_code)
        game.game_state = {'bank_prices': prices}
        db.commit()
        
        # Apply fluctuations
        for _ in range(100):
            prices, changed = pricing_mgr.apply_random_fluctuation(game_code, prices)
            if changed:
                break
        
        # Check recent history entries
        recent_fluctuations = db.query(PriceHistory).filter(
            PriceHistory.game_session_id == game.id,
            PriceHistory.triggered_by_trade == False
        ).order_by(PriceHistory.timestamp.desc()).limit(10).all()
        
        assert len(recent_fluctuations) > 0, "Should have non-trade fluctuation records"
