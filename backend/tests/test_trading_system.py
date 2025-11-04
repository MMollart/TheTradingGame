"""
Tests for the Trading System
"""
from trading_system import DynamicPricingSystem, TradingManager, TradeOfferStatus


class TestDynamicPricingSystem:
    """Tests for dynamic pricing"""
    
    def test_initial_prices(self):
        """Test that initial prices are set correctly"""
        pricing = DynamicPricingSystem()
        
        # Check baseline prices exist
        assert 'food' in pricing.baseline_prices
        assert 'raw_materials' in pricing.baseline_prices
        assert 'electrical_goods' in pricing.baseline_prices
        assert 'medical_goods' in pricing.baseline_prices
        
        # Check multipliers are at 1.0
        for resource in pricing.baseline_prices.keys():
            assert pricing.price_multipliers[resource] == 1.0
    
    def test_buy_sell_spread(self):
        """Test that buy and sell prices have appropriate spread"""
        pricing = DynamicPricingSystem()
        
        for resource in pricing.baseline_prices.keys():
            buy_price = pricing.get_buy_price(resource)
            sell_price = pricing.get_sell_price(resource)
            
            # Sell price should be higher than buy price (bank profits)
            assert sell_price > buy_price, f"{resource}: sell {sell_price} should be > buy {buy_price}"
            
            # Spread should be approximately 15%
            spread_ratio = (sell_price - buy_price) / buy_price
            assert 0.10 < spread_ratio < 0.20, f"Spread ratio {spread_ratio} out of expected range"
    
    def test_price_increases_with_demand(self):
        """Test that prices increase when bank sells (high demand)"""
        pricing = DynamicPricingSystem()
        
        initial_price = pricing.get_sell_price('food')
        
        # Simulate high demand (bank sells a lot)
        for _ in range(10):
            pricing.update_prices_after_trade('food', 10, 'bank_sells')
        
        new_price = pricing.get_sell_price('food')
        
        # Price should increase with demand
        assert new_price > initial_price, f"Price should increase: {initial_price} -> {new_price}"
    
    def test_price_decreases_with_supply(self):
        """Test that prices decrease when bank buys (high supply)"""
        pricing = DynamicPricingSystem()
        
        initial_price = pricing.get_buy_price('raw_materials')
        
        # Simulate high supply (bank buys a lot)
        for _ in range(10):
            pricing.update_prices_after_trade('raw_materials', 10, 'bank_buys')
        
        new_price = pricing.get_buy_price('raw_materials')
        
        # Price should decrease with supply
        assert new_price < initial_price, f"Price should decrease: {initial_price} -> {new_price}"
    
    def test_price_bounds(self):
        """Test that prices stay within bounds (-50% to +100%)"""
        pricing = DynamicPricingSystem()
        baseline = pricing.baseline_prices['electrical_goods']
        
        # Try to push price very high
        for _ in range(100):
            pricing.update_prices_after_trade('electrical_goods', 100, 'bank_sells')
        
        max_price = pricing.get_sell_price('electrical_goods')
        assert max_price <= baseline * 2.0, "Price should not exceed 200% of baseline"
        
        # Reset
        pricing.price_multipliers['electrical_goods'] = 1.0
        
        # Try to push price very low
        for _ in range(100):
            pricing.update_prices_after_trade('electrical_goods', 100, 'bank_buys')
        
        min_price = pricing.get_buy_price('electrical_goods')
        assert min_price >= baseline * 0.5, "Price should not go below 50% of baseline"
    
    def test_price_history_tracking(self):
        """Test that price history is tracked"""
        pricing = DynamicPricingSystem()
        
        initial_history_length = len(pricing.price_history)
        
        # Make some trades
        pricing.update_prices_after_trade('food', 5, 'bank_sells')
        pricing.update_prices_after_trade('raw_materials', 3, 'bank_buys')
        
        # History should have grown
        assert len(pricing.price_history) > initial_history_length
        
        # Can get specific resource history
        food_history = pricing.get_price_history('food')
        assert len(food_history) > 0
        assert 'buy_price' in food_history[0]
        assert 'sell_price' in food_history[0]
    
    def test_serialization(self):
        """Test that pricing system can be serialized and deserialized"""
        pricing = DynamicPricingSystem()
        
        # Make some changes
        pricing.update_prices_after_trade('food', 10, 'bank_sells')
        pricing.update_prices_after_trade('medical_goods', 5, 'bank_buys')
        
        # Serialize
        data = pricing.to_dict()
        
        # Deserialize
        restored = DynamicPricingSystem.from_dict(data)
        
        # Should have same state
        assert restored.price_multipliers == pricing.price_multipliers
        assert restored.trade_volumes == pricing.trade_volumes
        assert len(restored.price_history) == len(pricing.price_history)


class TestTradingManager:
    """Tests for trading manager"""
    
    def test_bank_trade_buy(self):
        """Test buying resources from bank"""
        manager = TradingManager()
        
        team_resources = {
            'currency': 100,
            'food': 10
        }
        
        success, error, new_resources, cost = manager.execute_bank_trade(
            team_resources=team_resources,
            resource='food',
            amount=5,
            trade_type='buy'
        )
        
        assert success, f"Trade should succeed: {error}"
        assert new_resources['food'] == 15, "Should have 5 more food"
        assert new_resources['currency'] < 100, "Should have spent currency"
        assert cost > 0, "Cost should be positive"
    
    def test_bank_trade_sell(self):
        """Test selling resources to bank"""
        manager = TradingManager()
        
        team_resources = {
            'currency': 50,
            'raw_materials': 20
        }
        
        success, error, new_resources, revenue = manager.execute_bank_trade(
            team_resources=team_resources,
            resource='raw_materials',
            amount=10,
            trade_type='sell'
        )
        
        assert success, f"Trade should succeed: {error}"
        assert new_resources['raw_materials'] == 10, "Should have 10 less raw_materials"
        assert new_resources['currency'] > 50, "Should have gained currency"
        assert revenue > 0, "Revenue should be positive"
    
    def test_bank_trade_insufficient_currency(self):
        """Test that trade fails with insufficient currency"""
        manager = TradingManager()
        
        team_resources = {
            'currency': 5,  # Not enough
            'food': 10
        }
        
        success, error, new_resources, cost = manager.execute_bank_trade(
            team_resources=team_resources,
            resource='electrical_goods',
            amount=10,  # Expensive items
            trade_type='buy'
        )
        
        assert not success, "Trade should fail"
        assert 'Insufficient currency' in error
        assert new_resources is None
    
    def test_bank_trade_insufficient_resource(self):
        """Test that trade fails with insufficient resource"""
        manager = TradingManager()
        
        team_resources = {
            'currency': 100,
            'food': 5  # Not enough
        }
        
        success, error, new_resources, revenue = manager.execute_bank_trade(
            team_resources=team_resources,
            resource='food',
            amount=10,
            trade_type='sell'
        )
        
        assert not success, "Trade should fail"
        assert 'Insufficient food' in error
        assert new_resources is None
    
    def test_create_team_trade_offer(self):
        """Test creating a trade offer between teams"""
        manager = TradingManager()
        
        offer = manager.create_trade_offer(
            from_team=1,
            to_team=2,
            offering={'food': 10, 'currency': 20},
            requesting={'raw_materials': 15},
            message="Good deal!"
        )
        
        assert offer.from_team == 1
        assert offer.to_team == 2
        assert offer.offering == {'food': 10, 'currency': 20}
        assert offer.requesting == {'raw_materials': 15}
        assert offer.message == "Good deal!"
        assert offer.status == TradeOfferStatus.PENDING
    
    def test_counter_trade_offer(self):
        """Test countering a trade offer"""
        manager = TradingManager()
        
        offer = manager.create_trade_offer(
            from_team=1,
            to_team=2,
            offering={'food': 10},
            requesting={'raw_materials': 15}
        )
        
        # Counter the offer
        offer.counter(
            new_offering={'food': 10},
            new_requesting={'raw_materials': 10},  # Less requested
            message="How about less?"
        )
        
        assert offer.status == TradeOfferStatus.COUNTERED
        assert offer.counter_offer is not None
        assert offer.counter_offer['requesting'] == {'raw_materials': 10}
    
    def test_execute_team_trade(self):
        """Test executing a trade between teams"""
        manager = TradingManager()
        
        # Create offer
        offer = manager.create_trade_offer(
            from_team=1,
            to_team=2,
            offering={'food': 10},
            requesting={'raw_materials': 5}
        )
        
        # Team resources
        team1_resources = {'food': 20, 'raw_materials': 0, 'currency': 50}
        team2_resources = {'food': 0, 'raw_materials': 10, 'currency': 50}
        
        # Execute trade
        success, error, new_team1, new_team2 = manager.execute_team_trade(
            offer_id=offer.offer_id,
            from_team_resources=team1_resources,
            to_team_resources=team2_resources
        )
        
        assert success, f"Trade should succeed: {error}"
        
        # Team 1 should have less food, more raw_materials
        assert new_team1['food'] == 10
        assert new_team1['raw_materials'] == 5
        
        # Team 2 should have more food, less raw_materials
        assert new_team2['food'] == 10
        assert new_team2['raw_materials'] == 5
        
        # Offer should be accepted
        assert offer.status == TradeOfferStatus.ACCEPTED
    
    def test_execute_team_trade_insufficient_resources(self):
        """Test that trade fails if team lacks resources"""
        manager = TradingManager()
        
        # Create offer
        offer = manager.create_trade_offer(
            from_team=1,
            to_team=2,
            offering={'food': 100},  # Too much
            requesting={'raw_materials': 5}
        )
        
        # Team 1 doesn't have enough food
        team1_resources = {'food': 20, 'raw_materials': 0, 'currency': 50}
        team2_resources = {'food': 0, 'raw_materials': 10, 'currency': 50}
        
        # Execute trade
        success, error, new_team1, new_team2 = manager.execute_team_trade(
            offer_id=offer.offer_id,
            from_team_resources=team1_resources,
            to_team_resources=team2_resources
        )
        
        assert not success, "Trade should fail"
        assert 'insufficient' in error.lower()
    
    def test_reject_trade_offer(self):
        """Test rejecting a trade offer"""
        manager = TradingManager()
        
        offer = manager.create_trade_offer(
            from_team=1,
            to_team=2,
            offering={'food': 10},
            requesting={'raw_materials': 15}
        )
        
        offer.reject()
        
        assert offer.status == TradeOfferStatus.REJECTED
    
    def test_cancel_trade_offer(self):
        """Test cancelling a trade offer"""
        manager = TradingManager()
        
        offer = manager.create_trade_offer(
            from_team=1,
            to_team=2,
            offering={'food': 10},
            requesting={'raw_materials': 15}
        )
        
        offer.cancel()
        
        assert offer.status == TradeOfferStatus.CANCELLED
    
    def test_get_team_trade_offers(self):
        """Test retrieving trade offers for a team"""
        manager = TradingManager()
        
        # Create several offers
        offer1 = manager.create_trade_offer(1, 2, {'food': 10}, {'raw_materials': 5})
        manager.create_trade_offer(2, 3, {'currency': 20}, {'food': 10})
        offer3 = manager.create_trade_offer(3, 1, {'raw_materials': 10}, {'currency': 30})
        
        # Get offers for team 1
        team1_offers = manager.get_team_trade_offers(1)
        
        # Should include offers where team 1 is involved
        assert len(team1_offers) == 2
        assert offer1 in team1_offers
        assert offer3 in team1_offers
    
    def test_serialization(self):
        """Test that trading manager can be serialized"""
        manager = TradingManager()
        
        # Create some state
        manager.create_trade_offer(1, 2, {'food': 10}, {'raw_materials': 5})
        manager.execute_bank_trade(
            team_resources={'currency': 100, 'food': 10},
            resource='food',
            amount=5,
            trade_type='buy'
        )
        
        # Serialize
        data = manager.to_dict()
        
        # Deserialize
        restored = TradingManager.from_dict(data)
        
        # Should have same state
        assert len(restored.trade_offers) == len(manager.trade_offers)
        assert len(restored.pricing_system.price_history) == len(manager.pricing_system.price_history)
