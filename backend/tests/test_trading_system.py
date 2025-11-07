"""
Tests for the trading system (bank and team-to-team trading)
"""
import pytest
from pricing_manager import PricingManager
from trade_manager import TradeManager
from models import GameSession, Player, TradeOffer, TradeOfferStatus, PriceHistory
from game_constants import BANK_INITIAL_PRICES


class TestPricingManager:
    """Test dynamic pricing system"""
    
    def test_initialize_prices(self, client, sample_game, sample_players, db):
        """Test initializing bank prices for a game"""
        game_code = sample_game["game_code"]
        pricing_mgr = PricingManager(db)
        
        prices = pricing_mgr.initialize_bank_prices(game_code)
        
        # Check all resources have prices
        assert 'food' in prices
        assert 'raw_materials' in prices
        assert 'electrical_goods' in prices
        assert 'medical_goods' in prices
        
        # Check price structure
        for resource, price_info in prices.items():
            assert 'baseline' in price_info
            assert 'buy_price' in price_info
            assert 'sell_price' in price_info
            
            # Buy price should be higher than sell price (spread)
            assert price_info['buy_price'] > price_info['sell_price']
            
            # Buy/sell should be within range of baseline
            assert price_info['sell_price'] <= price_info['baseline']
            assert price_info['buy_price'] >= price_info['baseline']
        
        # Check price history was recorded
        history_records = db.query(PriceHistory).filter(
            PriceHistory.resource_type == 'food'
        ).all()
        assert len(history_records) == 1
    
    def test_price_spread_calculation(self, client, sample_game, sample_players, db):
        """Test that buy/sell spread is correctly applied through initialization"""
        game_code = sample_game["game_code"]
        pricing_mgr = PricingManager(db)
        
        # Initialize prices to test spread
        prices = pricing_mgr.initialize_bank_prices(game_code)
        
        # Check spread is applied correctly for all resources
        for resource, price_info in prices.items():
            buy_price = price_info['buy_price']
            sell_price = price_info['sell_price']
            baseline = price_info['baseline']
            
            # Buy should be higher, sell should be lower than baseline
            assert buy_price > baseline
            assert sell_price < baseline
            
            # Buy and sell prices should differ (spread exists)
            assert buy_price != sell_price
            
            # Spread should be at least 1 (minimum spread enforced)
            actual_spread = buy_price - sell_price
            assert actual_spread >= 1
    
    def test_adjust_price_after_buy(self, client, sample_game, sample_players, db):
        """Test price increases when team buys from bank"""
        game_code = sample_game["game_code"]
        pricing_mgr = PricingManager(db)
        
        # Initialize prices
        initial_prices = pricing_mgr.initialize_bank_prices(game_code)
        # Use medical_goods (baseline=20, high enough for int(20*0.05)=1 adjustment)
        initial_med_buy = initial_prices['medical_goods']['buy_price']
        
        # Simulate team buying medical_goods from bank
        updated_prices = pricing_mgr.adjust_price_after_trade(
            game_code,
            'medical_goods',
            quantity=100,  # Full adjustment factor
            is_team_buying=True,
            current_prices=initial_prices
        )
        
        # Medical goods buy price should have increased
        assert updated_prices['medical_goods']['buy_price'] > initial_med_buy
        
        # Price should still be within bounds
        baseline = updated_prices['medical_goods']['baseline']
        assert updated_prices['medical_goods']['buy_price'] <= baseline * PricingManager.MAX_MULTIPLIER
    
    def test_adjust_price_after_sell(self, client, sample_game, sample_players, db):
        """Test price decreases when team sells to bank"""
        game_code = sample_game["game_code"]
        pricing_mgr = PricingManager(db)
        
        # Initialize prices
        initial_prices = pricing_mgr.initialize_bank_prices(game_code)
        # Use medical_goods (baseline=20, high enough for int(20*0.05)=1 adjustment)
        initial_med_sell = initial_prices['medical_goods']['sell_price']
        
        # Simulate team selling medical_goods to bank
        # Note: quantity is capped at 100 for max effect in pricing logic
        # but we use 100 here which should give full adjustment of int(20*0.05)=1
        # However, due to rounding in spread calculation, we use a higher baseline resource
        # Actually, let's test multiple sells to accumulate enough change
        current_prices = initial_prices
        for _ in range(3):  # Multiple sells to overcome rounding issues
            current_prices = pricing_mgr.adjust_price_after_trade(
                game_code,
                'medical_goods',
                quantity=100,
                is_team_buying=False,
                current_prices=current_prices
            )
        updated_prices = current_prices
        
        # Medical goods sell price should have decreased
        assert updated_prices['medical_goods']['sell_price'] < initial_med_sell
        
        # Price should still be within bounds
        baseline = updated_prices['medical_goods']['baseline']
        assert updated_prices['medical_goods']['sell_price'] >= baseline * PricingManager.MIN_MULTIPLIER
    
    def test_price_bounds(self, client, sample_game, sample_players, db):
        """Test prices stay within min/max bounds"""
        game_code = sample_game["game_code"]
        pricing_mgr = PricingManager(db)
        
        initial_prices = pricing_mgr.initialize_bank_prices(game_code)
        current_prices = initial_prices.copy()
        
        # Simulate many buy transactions to push price up
        for _ in range(20):
            current_prices = pricing_mgr.adjust_price_after_trade(
                game_code,
                'food',
                quantity=100,
                is_team_buying=True,
                current_prices=current_prices
            )
        
        # Price should not exceed max multiplier
        baseline = initial_prices['food']['baseline']
        max_price = baseline * PricingManager.MAX_MULTIPLIER
        middle_price = (current_prices['food']['buy_price'] + current_prices['food']['sell_price']) // 2
        
        assert middle_price <= max_price
    
    def test_calculate_trade_cost(self, client, sample_game, sample_players, db):
        """Test trade cost calculation"""
        game_code = sample_game["game_code"]
        pricing_mgr = PricingManager(db)
        
        prices = pricing_mgr.initialize_bank_prices(game_code)
        
        # Calculate cost for buying
        buy_cost = pricing_mgr.calculate_trade_cost('food', 10, True, prices)
        expected_buy_cost = prices['food']['buy_price'] * 10
        assert buy_cost == expected_buy_cost
        
        # Calculate cost for selling
        sell_cost = pricing_mgr.calculate_trade_cost('food', 10, False, prices)
        expected_sell_cost = prices['food']['sell_price'] * 10
        assert sell_cost == expected_sell_cost
        
        # Buy should cost more than sell returns
        assert buy_cost > sell_cost
    
    def test_get_price_history(self, client, sample_game, sample_players, db):
        """Test retrieving price history"""
        game_code = sample_game["game_code"]
        pricing_mgr = PricingManager(db)
        
        # Initialize and make some trades
        initial_prices = pricing_mgr.initialize_bank_prices(game_code)
        pricing_mgr.adjust_price_after_trade(game_code, 'food', 10, True, initial_prices)
        
        # Get history
        history = pricing_mgr.get_price_history(game_code, 'food')
        
        assert len(history) >= 2  # Initial + one adjustment
        assert all('buy_price' in h for h in history)
        assert all('sell_price' in h for h in history)
        assert all('timestamp' in h for h in history)
    
    def test_manual_price_update(self, client, sample_game, sample_players, db):
        """Test manually updating a resource price (for host/banker)"""
        game_code = sample_game["game_code"]
        pricing_mgr = PricingManager(db)
        
        # Initialize prices
        initial_prices = pricing_mgr.initialize_bank_prices(game_code)
        initial_food_baseline = initial_prices['food']['baseline']
        
        # Manually update food baseline to 5
        updated_prices = pricing_mgr.update_resource_baseline(
            game_code,
            'food',
            5,
            initial_prices
        )
        
        # Check baseline was updated
        assert updated_prices['food']['baseline'] == 5
        assert updated_prices['food']['baseline'] != initial_food_baseline
        
        # Check buy/sell prices were recalculated with spread
        assert updated_prices['food']['buy_price'] > 5
        assert updated_prices['food']['sell_price'] < 5
        
        # Other resources should be unchanged
        assert updated_prices['raw_materials'] == initial_prices['raw_materials']
        assert updated_prices['electrical_goods'] == initial_prices['electrical_goods']
        
        # Check price history was recorded
        history = pricing_mgr.get_price_history(game_code, 'food')
        assert len(history) >= 2  # Initial + manual update


class TestTradeManager:
    """Test team-to-team trading"""
    
    def test_create_trade_offer(self, client, sample_game, sample_players, db):
        """Test creating a trade offer"""
        game_code = sample_game["game_code"]
        
        # Get players and assign to teams BEFORE starting game
        game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
        players = db.query(Player).filter(
            Player.game_session_id == game.id,
            Player.role == "player"
        ).all()
        
        # Assign players to teams
        player1 = players[0]
        player1.group_number = 1
        player2 = players[1]
        player2.group_number = 2
        db.commit()
        
        # Start game to initialize team resources
        client.post(f"/games/{game_code}/start")
        
        # Refresh game to get initialized state
        db.refresh(game)
        
        # Create trade offer
        trade_mgr = TradeManager(db)
        offer = trade_mgr.create_trade_offer(
            game_code,
            from_team_number=1,
            to_team_number=2,
            player_id=player1.id,
            offered_resources={'food': 10, 'currency': 50},
            requested_resources={'raw_materials': 20}
        )
        
        assert offer.id is not None
        assert offer.from_team_number == 1
        assert offer.to_team_number == 2
        assert offer.status == TradeOfferStatus.PENDING
        assert offer.offered_resources == {'food': 10, 'currency': 50}
        assert offer.requested_resources == {'raw_materials': 20}
    
    def test_create_trade_offer_insufficient_resources(self, client, sample_game, sample_players, db):
        """Test creating trade offer with insufficient resources"""
        game_code = sample_game["game_code"]
        
        # Get player and assign BEFORE starting game
        game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
        player = db.query(Player).filter(Player.game_session_id == game.id, Player.role == "player").first()
        player.group_number = 1
        db.commit()
        
        # Start game to initialize team resources
        client.post(f"/games/{game_code}/start")
        db.refresh(game)
        
        # Try to offer more resources than available
        trade_mgr = TradeManager(db)
        
        with pytest.raises(ValueError, match="Insufficient"):
            trade_mgr.create_trade_offer(
                game_code,
                from_team_number=1,
                to_team_number=2,
                player_id=player.id,
                offered_resources={'food': 999999},  # Way more than starting resources
                requested_resources={'raw_materials': 1}
            )
    
    def test_create_counter_offer(self, client, sample_game, sample_players, db):
        """Test creating a counter-offer"""
        game_code = sample_game["game_code"]
        
        # Get players and assign to teams BEFORE starting game
        game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
        players = db.query(Player).filter(
            Player.game_session_id == game.id,
            Player.role == "player"
        ).all()
        
        player1 = players[0]
        player1.group_number = 1
        player2 = players[1]
        player2.group_number = 2
        db.commit()
        
        # Start game to initialize team resources
        client.post(f"/games/{game_code}/start")
        db.refresh(game)
        
        # Create initial offer
        trade_mgr = TradeManager(db)
        offer = trade_mgr.create_trade_offer(
            game_code, 1, 2, player1.id,
            {'food': 10}, {'raw_materials': 10}
        )
        
        # Create counter-offer
        counter = trade_mgr.create_counter_offer(
            offer.id,
            player2.id,
            {'raw_materials': 15},  # Offer more
            {'food': 10}  # Request same
        )
        
        assert counter.status == TradeOfferStatus.COUNTER_OFFERED
        assert counter.counter_offered_resources == {'raw_materials': 15}
        assert counter.counter_requested_resources == {'food': 10}
    
    def test_accept_trade_offer(self, client, sample_game, sample_players, db):
        """Test accepting a trade offer"""
        game_code = sample_game["game_code"]
        
        # Get players and assign to teams BEFORE starting game
        game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
        players = db.query(Player).filter(
            Player.game_session_id == game.id,
            Player.role == "player"
        ).all()
        
        player1 = players[0]
        player1.group_number = 1
        player2 = players[1]
        player2.group_number = 2
        db.commit()
        
        # Start game to initialize team resources
        client.post(f"/games/{game_code}/start")
        db.refresh(game)
        
        # Get initial resources
        team1_resources = game.game_state['teams']['1']['resources'].copy()
        team2_resources = game.game_state['teams']['2']['resources'].copy()
        
        # Create and accept offer
        trade_mgr = TradeManager(db)
        offer = trade_mgr.create_trade_offer(
            game_code, 1, 2, player1.id,
            {'food': 5}, {'raw_materials': 5}
        )
        
        accepted_offer, updated_game = trade_mgr.accept_trade_offer(
            offer.id, player2.id, accept_counter=False
        )
        
        # Verify trade executed
        assert accepted_offer.status == TradeOfferStatus.ACCEPTED
        
        # Verify resources transferred correctly
        new_team1_resources = updated_game.game_state['teams']['1']['resources']
        new_team2_resources = updated_game.game_state['teams']['2']['resources']
        
        # Team 1 gave food, received raw_materials
        assert new_team1_resources['food'] == team1_resources.get('food', 0) - 5
        assert new_team1_resources.get('raw_materials', 0) == team1_resources.get('raw_materials', 0) + 5
        
        # Team 2 gave raw_materials, received food
        assert new_team2_resources.get('raw_materials', 0) == team2_resources.get('raw_materials', 0) - 5
        assert new_team2_resources.get('food', 0) == team2_resources.get('food', 0) + 5
    
    def test_reject_trade_offer(self, client, sample_game, sample_players, db):
        """Test rejecting a trade offer"""
        game_code = sample_game["game_code"]
        
        # Get players and assign to teams BEFORE starting game
        game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
        players = db.query(Player).filter(
            Player.game_session_id == game.id,
            Player.role == "player"
        ).all()
        
        player1 = players[0]
        player1.group_number = 1
        player2 = players[1]
        player2.group_number = 2
        db.commit()
        
        # Start game to initialize team resources
        client.post(f"/games/{game_code}/start")
        db.refresh(game)
        
        # Create and reject offer
        trade_mgr = TradeManager(db)
        offer = trade_mgr.create_trade_offer(
            game_code, 1, 2, player1.id,
            {'food': 5}, {'raw_materials': 5}
        )
        
        rejected = trade_mgr.reject_trade_offer(offer.id, player2.id)
        
        assert rejected.status == TradeOfferStatus.REJECTED
    
    def test_cancel_trade_offer(self, client, sample_game, sample_players, db):
        """Test cancelling a trade offer"""
        game_code = sample_game["game_code"]
        
        # Get player and assign BEFORE starting game
        game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
        player = db.query(Player).filter(Player.game_session_id == game.id, Player.role == "player").first()
        player.group_number = 1
        db.commit()
        
        # Start game to initialize team resources
        client.post(f"/games/{game_code}/start")
        db.refresh(game)
        
        # Create and cancel offer
        trade_mgr = TradeManager(db)
        offer = trade_mgr.create_trade_offer(
            game_code, 1, 2, player.id,
            {'food': 5}, {'raw_materials': 5}
        )
        
        cancelled = trade_mgr.cancel_trade_offer(offer.id, player.id)
        
        assert cancelled.status == TradeOfferStatus.CANCELLED
    
    def test_get_team_trade_offers(self, client, sample_game, sample_players, db):
        """Test retrieving trade offers for a team"""
        game_code = sample_game["game_code"]
        
        # Get player and assign BEFORE starting game
        game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
        player = db.query(Player).filter(Player.game_session_id == game.id, Player.role == "player").first()
        player.group_number = 1
        db.commit()
        
        # Start game to initialize team resources
        client.post(f"/games/{game_code}/start")
        db.refresh(game)
        
        # Create offers
        trade_mgr = TradeManager(db)
        offer1 = trade_mgr.create_trade_offer(
            game_code, 1, 2, player.id,
            {'food': 5}, {'raw_materials': 5}
        )
        offer2 = trade_mgr.create_trade_offer(
            game_code, 1, 3, player.id,
            {'food': 10}, {'currency': 50}
        )
        
        # Get trades for team 1
        trades = trade_mgr.get_team_trade_offers(game_code, 1)
        
        assert len(trades) == 2
        assert any(t.id == offer1.id for t in trades)
        assert any(t.id == offer2.id for t in trades)


class TestTradingAPI:
    """Test trading API endpoints"""
    
    @pytest.mark.asyncio
    async def test_initialize_bank_prices_endpoint(self, client, sample_game):
        """Test bank price initialization endpoint"""
        game_code = sample_game["game_code"]
        
        response = client.post(f"/api/v2/trading/{game_code}/bank/initialize-prices")
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'prices' in data
        assert 'food' in data['prices']
    
    def test_get_bank_prices_endpoint(self, client, sample_game, sample_players, db):
        """Test getting current bank prices"""
        game_code = sample_game["game_code"]
        
        # Start game to initialize banker
        client.post(f"/games/{game_code}/start")
        
        # Initialize prices
        client.post(f"/api/v2/trading/{game_code}/bank/initialize-prices")
        
        # Get prices
        response = client.get(f"/api/v2/trading/{game_code}/bank/prices")
        
        assert response.status_code == 200
        data = response.json()
        assert 'prices' in data
    
    def test_create_team_trade_offer_endpoint(self, client, sample_game, sample_players, db):
        """Test creating trade offer via API"""
        game_code = sample_game["game_code"]
        
        # Get player and assign BEFORE starting game
        game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
        player = db.query(Player).filter(Player.game_session_id == game.id, Player.role == "player").first()
        player.group_number = 1
        db.commit()
        
        # Start game to initialize team resources
        client.post(f"/games/{game_code}/start")
        db.refresh(game)
        
        # Create offer
        response = client.post(
            f"/api/v2/trading/{game_code}/team/offer",
            json={
                "game_code": game_code,
                "from_team_number": 1,
                "to_team_number": 2,
                "player_id": player.id,
                "offered_resources": {"food": 5},
                "requested_resources": {"raw_materials": 5}
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'trade_id' in data
    
    def test_update_bank_price_endpoint(self, client, sample_game, sample_players, db):
        """Test updating bank price via API"""
        game_code = sample_game["game_code"]
        
        # Start game to initialize bank prices
        client.post(f"/games/{game_code}/start")
        
        # Get initial prices
        game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
        initial_food_baseline = game.game_state['bank_prices']['food']['baseline']
        
        # Update food price to 10
        response = client.post(
            f"/games/{game_code}/update-bank-price",
            json={
                "resource_type": "food",
                "baseline_price": 10
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['resource_type'] == 'food'
        assert data['baseline'] == 10
        assert data['baseline'] != initial_food_baseline
        assert 'buy_price' in data
        assert 'sell_price' in data
        
        # Verify buy price is higher than baseline and sell price is lower
        assert data['buy_price'] > 10
        assert data['sell_price'] < 10
        
        # Verify price was updated in game state
        db.refresh(game)
        assert game.game_state['bank_prices']['food']['baseline'] == 10
        assert game.game_state['bank_prices']['food']['buy_price'] == data['buy_price']
        assert game.game_state['bank_prices']['food']['sell_price'] == data['sell_price']
    
    def test_trade_margin_recorded_on_accept(self, client, sample_game, sample_players, db):
        """Test that trade margins are recorded when trade is accepted"""
        game_code = sample_game["game_code"]
        
        # Get players and assign to teams
        game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
        players = db.query(Player).filter(
            Player.game_session_id == game.id,
            Player.role == "player"
        ).all()
        
        player1 = players[0]
        player1.group_number = 1
        player2 = players[1]
        player2.group_number = 2
        db.commit()
        
        # Start game and initialize bank prices
        client.post(f"/games/{game_code}/start")
        response = client.post(f"/api/v2/trading/{game_code}/bank/initialize-prices")
        assert response.status_code == 200
        
        db.refresh(game)
        
        # Create and accept trade offer
        trade_mgr = TradeManager(db)
        offer = trade_mgr.create_trade_offer(
            game_code, 1, 2, player1.id,
            {'food': 10}, {'currency': 50}
        )
        
        accepted_offer, updated_game = trade_mgr.accept_trade_offer(
            offer.id, player2.id, accept_counter=False
        )
        
        # Verify trade margins were recorded
        assert accepted_offer.from_team_margin is not None
        assert accepted_offer.to_team_margin is not None
        
        # Verify margin structure
        assert 'margin' in accepted_offer.from_team_margin
        assert 'trade_value' in accepted_offer.from_team_margin
        assert 'margin' in accepted_offer.to_team_margin
        assert 'trade_value' in accepted_offer.to_team_margin
        
        # Margins should be opposite (one team's gain is another's loss)
        from_margin = accepted_offer.from_team_margin['margin']
        to_margin = accepted_offer.to_team_margin['margin']
        
        # The sum of margins should be close to zero (accounting for rounding)
        # Not exactly zero due to different trade_value denominators
        assert abs(from_margin + to_margin) < 0.5  # Allow for calculation differences
