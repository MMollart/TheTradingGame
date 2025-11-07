"""
Tests for kindness-based trade scoring system
"""
import pytest
from trade_manager import TradeMarginCalculator
from game_constants import calculate_kindness_modifier, KINDNESS_FACTOR


class TestTradeMarginCalculator:
    """Test trade margin calculation logic"""
    
    def test_calculate_resource_value_with_currency(self):
        """Test calculating value of resources including currency"""
        resources = {
            'food': 10,
            'currency': 50
        }
        bank_prices = {
            'food': {'baseline': 10, 'buy_price': 11, 'sell_price': 9},
            'raw_materials': {'baseline': 5, 'buy_price': 6, 'sell_price': 4}
        }
        
        # Should use sell_price for food (9) and face value for currency
        # 10 * 9 + 50 = 140
        value = TradeMarginCalculator.calculate_resource_value(resources, bank_prices)
        assert value == 140.0
    
    def test_calculate_resource_value_multiple_resources(self):
        """Test calculating value with multiple resource types"""
        resources = {
            'food': 5,
            'raw_materials': 10,
            'electrical_goods': 3
        }
        bank_prices = {
            'food': {'baseline': 10, 'sell_price': 9},
            'raw_materials': {'baseline': 5, 'sell_price': 4},
            'electrical_goods': {'baseline': 15, 'sell_price': 13}
        }
        
        # 5*9 + 10*4 + 3*13 = 45 + 40 + 39 = 124
        value = TradeMarginCalculator.calculate_resource_value(resources, bank_prices)
        assert value == 124.0
    
    def test_calculate_trade_margin_fair_trade(self):
        """Test margin calculation for a fair trade (equal value)"""
        offered = {'food': 10}  # Value: 10 * 9 = 90
        requested = {'currency': 90}  # Value: 90
        bank_prices = {
            'food': {'baseline': 10, 'sell_price': 9}
        }
        
        margin_data = TradeMarginCalculator.calculate_trade_margin(
            offered, requested, bank_prices
        )
        
        assert margin_data['margin'] == 0.0
        assert margin_data['trade_value'] == 90.0
    
    def test_calculate_trade_margin_generous_trade(self):
        """Test margin calculation for generous trade (trading at a loss)"""
        offered = {'food': 10}  # Value: 10 * 9 = 90
        requested = {'currency': 50}  # Value: 50
        bank_prices = {
            'food': {'baseline': 10, 'sell_price': 9}
        }
        
        margin_data = TradeMarginCalculator.calculate_trade_margin(
            offered, requested, bank_prices
        )
        
        # Margin = (50 - 90) / 90 = -40/90 = -0.4444
        assert margin_data['margin'] < 0  # Negative margin = loss
        assert abs(margin_data['margin'] - (-0.4444)) < 0.01
    
    def test_calculate_trade_margin_profitable_trade(self):
        """Test margin calculation for profitable trade"""
        offered = {'food': 5}  # Value: 5 * 9 = 45
        requested = {'currency': 100}  # Value: 100
        bank_prices = {
            'food': {'baseline': 10, 'sell_price': 9}
        }
        
        margin_data = TradeMarginCalculator.calculate_trade_margin(
            offered, requested, bank_prices
        )
        
        # Margin = (100 - 45) / 45 = 55/45 = 1.2222
        assert margin_data['margin'] > 0  # Positive margin = profit
        assert abs(margin_data['margin'] - 1.2222) < 0.01
    
    def test_calculate_trade_margin_zero_given(self):
        """Test margin calculation when giving nothing"""
        offered = {}
        requested = {'currency': 100}
        bank_prices = {}
        
        margin_data = TradeMarginCalculator.calculate_trade_margin(
            offered, requested, bank_prices
        )
        
        # Should return 0 margin when giving nothing
        assert margin_data['margin'] == 0.0
        assert margin_data['trade_value'] == 100.0


class TestKindnessModifier:
    """Test kindness modifier calculation for final scoring"""
    
    def test_kindness_modifier_no_trades(self):
        """Test modifier when team has no trade history"""
        trade_margins = []
        
        result = calculate_kindness_modifier(trade_margins)
        
        assert result['modifier'] == 1.0
        assert result['avg_margin'] == 0.0
        assert result['label'] == 'No Trades'
    
    def test_kindness_modifier_generous_trader(self):
        """Test modifier for team that trades generously"""
        trade_margins = [
            {'margin': -0.25, 'trade_value': 100},  # 25% loss
            {'margin': -0.30, 'trade_value': 150},  # 30% loss
            {'margin': -0.20, 'trade_value': 80}    # 20% loss
        ]
        
        result = calculate_kindness_modifier(trade_margins)
        
        # Weighted avg: (-0.25*100 + -0.30*150 + -0.20*80) / 330 = -0.2636
        # Modifier: 1 - (-0.2636 * 0.15) = 1 + 0.0395 = 1.0395
        assert result['avg_margin'] < 0
        assert result['modifier'] > 1.0  # Bonus for generous trading
        assert result['label'] == 'Generous Trader'
    
    def test_kindness_modifier_shrewd_trader(self):
        """Test modifier for team that trades for profit"""
        trade_margins = [
            {'margin': 0.15, 'trade_value': 100},  # 15% profit
            {'margin': 0.25, 'trade_value': 150},  # 25% profit
            {'margin': 0.10, 'trade_value': 80}    # 10% profit
        ]
        
        result = calculate_kindness_modifier(trade_margins)
        
        # Weighted avg should be positive
        # Modifier should be less than 1.0 (penalty)
        assert result['avg_margin'] > 0
        assert result['modifier'] < 1.0  # Penalty for profit-focused trading
        assert result['label'] in ['Shrewd Trader', 'Profit-Focused']
    
    def test_kindness_modifier_fair_trader(self):
        """Test modifier for team that trades fairly"""
        trade_margins = [
            {'margin': -0.05, 'trade_value': 100},
            {'margin': 0.02, 'trade_value': 100},
            {'margin': -0.08, 'trade_value': 100}
        ]
        
        result = calculate_kindness_modifier(trade_margins)
        
        # Small negative average should give small bonus
        assert abs(result['avg_margin']) < 0.1
        assert result['modifier'] >= 1.0  # Small bonus or neutral
        assert result['label'] in ['Fair Trader', 'Balanced Trader']
    
    def test_kindness_modifier_weighted_by_trade_value(self):
        """Test that larger trades have more influence on modifier"""
        trade_margins = [
            {'margin': -0.50, 'trade_value': 1000},  # Large generous trade
            {'margin': 0.50, 'trade_value': 10}      # Small profitable trade
        ]
        
        result = calculate_kindness_modifier(trade_margins)
        
        # Weighted avg: (-0.50*1000 + 0.50*10) / 1010 = -495/1010 = -0.49
        # Should be heavily influenced by the large generous trade
        assert result['avg_margin'] < -0.4
        assert result['modifier'] > 1.05  # Significant bonus
    
    def test_kindness_modifier_bounds(self):
        """Test that modifier is bounded to prevent extreme values"""
        # Extreme generous trading
        generous_margins = [
            {'margin': -0.90, 'trade_value': 100},
            {'margin': -0.95, 'trade_value': 100}
        ]
        
        result = calculate_kindness_modifier(generous_margins)
        # Modifier should not exceed MAX_KINDNESS_MODIFIER (1.5)
        assert result['modifier'] <= 1.5
        
        # Extreme profit-focused trading
        profit_margins = [
            {'margin': 0.90, 'trade_value': 100},
            {'margin': 0.95, 'trade_value': 100}
        ]
        
        result = calculate_kindness_modifier(profit_margins)
        # Modifier should not go below MIN_KINDNESS_MODIFIER (0.5)
        assert result['modifier'] >= 0.5
    
    def test_kindness_factor_impact(self):
        """Test that KINDNESS_FACTOR properly scales the modifier"""
        # With KINDNESS_FACTOR = 0.15 (15% impact)
        trade_margins = [
            {'margin': -0.20, 'trade_value': 100}  # 20% loss
        ]
        
        result = calculate_kindness_modifier(trade_margins)
        
        # Modifier = 1 - (-0.20 * 0.15) = 1 + 0.03 = 1.03
        expected_modifier = 1.0 - (-0.20 * KINDNESS_FACTOR)
        assert abs(result['modifier'] - expected_modifier) < 0.01


class TestEndToEndScoring:
    """Test complete scoring with kindness modifier"""
    
    def test_scoring_with_generous_trades(self):
        """Test that generous trading increases final score"""
        from game_constants import calculate_final_score
        
        # Team state with some resources and generous trade history
        nation_state = {
            'resources': {
                'food': 50,
                'currency': 200,
                'raw_materials': 30
            },
            'buildings': {
                'farm': 3,
                'mine': 2
            },
            'bank_prices': {
                'food': {'baseline': 10, 'sell_price': 9},
                'raw_materials': {'baseline': 5, 'sell_price': 4}
            },
            'trade_margins': [
                {'margin': -0.20, 'trade_value': 100},
                {'margin': -0.25, 'trade_value': 150}
            ]
        }
        
        score = calculate_final_score(nation_state)
        
        # Should have positive kindness modifier (bonus)
        assert score['kindness_modifier'] > 1.0
        assert score['kindness_label'] == 'Generous Trader'
        
        # Total should be greater than base_total
        assert score['total'] > score['base_total']
    
    def test_scoring_with_shrewd_trades(self):
        """Test that profit-focused trading decreases final score"""
        from game_constants import calculate_final_score
        
        nation_state = {
            'resources': {
                'food': 50,
                'currency': 200
            },
            'buildings': {
                'farm': 3
            },
            'bank_prices': {
                'food': {'baseline': 10, 'sell_price': 9}
            },
            'trade_margins': [
                {'margin': 0.30, 'trade_value': 100},
                {'margin': 0.25, 'trade_value': 150}
            ]
        }
        
        score = calculate_final_score(nation_state)
        
        # Should have negative kindness modifier (penalty)
        assert score['kindness_modifier'] < 1.0
        assert score['kindness_label'] in ['Shrewd Trader', 'Profit-Focused']
        
        # Total should be less than base_total
        assert score['total'] < score['base_total']
    
    def test_scoring_without_trades(self):
        """Test scoring for team with no trades"""
        from game_constants import calculate_final_score
        
        nation_state = {
            'resources': {
                'food': 50,
                'currency': 200
            },
            'buildings': {
                'farm': 3
            },
            'bank_prices': {
                'food': {'baseline': 10, 'sell_price': 9}
            },
            'trade_margins': []
        }
        
        score = calculate_final_score(nation_state)
        
        # Should have neutral modifier
        assert score['kindness_modifier'] == 1.0
        assert score['kindness_label'] == 'No Trades'
        
        # Total should equal base_total
        assert score['total'] == score['base_total']
