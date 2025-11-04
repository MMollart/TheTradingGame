"""
Integration tests for Trading API endpoints
"""
import pytest
from sqlalchemy.orm.attributes import flag_modified
from models import GameSession, GameStatus


def test_get_bank_prices(client, sample_game):
    """Test getting bank prices"""
    game_code = sample_game["game_code"]
    
    response = client.get(f"/api/v2/trading/games/{game_code}/bank/prices")
    
    assert response.status_code == 200
    data = response.json()
    assert "prices" in data
    assert "food" in data["prices"]
    assert "buy" in data["prices"]["food"]
    assert "sell" in data["prices"]["food"]
    assert "baseline" in data["prices"]["food"]
    
    # Verify sell price is higher than buy price
    assert data["prices"]["food"]["sell"] > data["prices"]["food"]["buy"]


def test_get_price_history(client, sample_game):
    """Test getting price history"""
    game_code = sample_game["game_code"]
    
    response = client.get(f"/api/v2/trading/games/{game_code}/bank/price-history?resource=food&limit=10")
    
    assert response.status_code == 200
    data = response.json()
    assert "history" in data
    assert len(data["history"]) > 0
    assert "buy_price" in data["history"][0]
    assert "sell_price" in data["history"][0]


def test_bank_trade_execution(client, sample_game, db):
    """Test executing a bank trade"""
    game_code = sample_game["game_code"]
    
    # Start the game and manually initialize team 1
    game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
    game.status = GameStatus.IN_PROGRESS
    
    if not game.game_state:
        game.game_state = {}
    
    game.game_state['teams'] = {
        '1': {
            'resources': {
                'food': 30,
                'raw_materials': 0,
                'electrical_goods': 0,
                'medical_goods': 0,
                'currency': 100
            },
            'buildings': {'farm': 3},
            'nation_type': 'nation_1',
            'name': 'Test Nation'
        }
    }
    flag_modified(game, 'game_state')
    db.commit()
    
    # Execute a buy trade
    response = client.post(
        f"/api/v2/trading/games/{game_code}/bank/trade",
        json={
            "team_number": 1,
            "resource": "food",
            "amount": 5,
            "trade_type": "buy"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert "total_cost" in data
    assert "new_resources" in data
    assert data["new_resources"]["food"] == 35  # 30 + 5
    assert data["new_resources"]["currency"] < 100  # Spent some currency


def test_bank_trade_insufficient_currency(client, sample_game, db):
    """Test that bank trade fails with insufficient currency"""
    game_code = sample_game["game_code"]
    
    # Setup game with low currency
    game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
    game.status = GameStatus.IN_PROGRESS
    
    if not game.game_state:
        game.game_state = {}
    
    game.game_state['teams'] = {
        '1': {
            'resources': {
                'food': 10,
                'currency': 5  # Very low
            },
            'buildings': {},
            'nation_type': 'nation_1'
        }
    }
    flag_modified(game, 'game_state')
    db.commit()
    
    # Try to buy expensive items
    response = client.post(
        f"/api/v2/trading/games/{game_code}/bank/trade",
        json={
            "team_number": 1,
            "resource": "electrical_goods",
            "amount": 10,
            "trade_type": "buy"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == False
    assert "Insufficient currency" in data["message"]


def test_create_team_trade_offer(client, sample_game, db):
    """Test creating a trade offer between teams"""
    game_code = sample_game["game_code"]
    
    # Setup game with two teams
    game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
    game.status = GameStatus.IN_PROGRESS
    
    if not game.game_state:
        game.game_state = {}
    
    game.game_state['teams'] = {
        '1': {
            'resources': {'food': 50, 'raw_materials': 10, 'currency': 100},
            'buildings': {},
            'nation_type': 'nation_1'
        },
        '2': {
            'resources': {'food': 10, 'raw_materials': 50, 'currency': 100},
            'buildings': {},
            'nation_type': 'nation_2'
        }
    }
    flag_modified(game, 'game_state')
    db.commit()
    
    # Create trade offer
    response = client.post(
        f"/api/v2/trading/games/{game_code}/team-trade/offer",
        json={
            "from_team": 1,
            "to_team": 2,
            "offering": {"food": 10},
            "requesting": {"raw_materials": 5},
            "message": "Good deal!"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert "offer" in data
    assert data["offer"]["from_team"] == 1
    assert data["offer"]["to_team"] == 2
    assert data["offer"]["status"] == "pending"


def test_get_team_trade_offers(client, sample_game, db):
    """Test getting trade offers for a team"""
    game_code = sample_game["game_code"]
    
    # Setup game
    game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
    game.status = GameStatus.IN_PROGRESS
    
    if not game.game_state:
        game.game_state = {}
    
    game.game_state['teams'] = {
        '1': {'resources': {'food': 50, 'currency': 100}, 'buildings': {}, 'nation_type': 'nation_1'},
        '2': {'resources': {'raw_materials': 50, 'currency': 100}, 'buildings': {}, 'nation_type': 'nation_2'}
    }
    flag_modified(game, 'game_state')
    db.commit()
    
    # Create an offer
    client.post(
        f"/api/v2/trading/games/{game_code}/team-trade/offer",
        json={
            "from_team": 1,
            "to_team": 2,
            "offering": {"food": 10},
            "requesting": {"raw_materials": 5}
        }
    )
    
    # Get offers for team 1
    response = client.get(f"/api/v2/trading/games/{game_code}/team-trade/offers?team_number=1")
    
    assert response.status_code == 200
    data = response.json()
    assert "offers" in data
    assert len(data["offers"]) == 1


def test_accept_team_trade_offer(client, sample_game, db):
    """Test accepting a trade offer"""
    game_code = sample_game["game_code"]
    
    # Setup game
    game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
    game.status = GameStatus.IN_PROGRESS
    
    if not game.game_state:
        game.game_state = {}
    
    game.game_state['teams'] = {
        '1': {'resources': {'food': 50, 'raw_materials': 0, 'currency': 100}, 'buildings': {}, 'nation_type': 'nation_1'},
        '2': {'resources': {'food': 0, 'raw_materials': 50, 'currency': 100}, 'buildings': {}, 'nation_type': 'nation_2'}
    }
    flag_modified(game, 'game_state')
    db.commit()
    
    # Create an offer
    create_response = client.post(
        f"/api/v2/trading/games/{game_code}/team-trade/offer",
        json={
            "from_team": 1,
            "to_team": 2,
            "offering": {"food": 10},
            "requesting": {"raw_materials": 5}
        }
    )
    offer_id = create_response.json()["offer"]["offer_id"]
    
    # Accept the offer
    response = client.post(f"/api/v2/trading/games/{game_code}/team-trade/{offer_id}/accept")
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert data["offer"]["status"] == "accepted"
    
    # Verify resources were exchanged
    game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
    team1_resources = game.game_state['teams']['1']['resources']
    team2_resources = game.game_state['teams']['2']['resources']
    
    assert team1_resources['food'] == 40  # 50 - 10
    assert team1_resources['raw_materials'] == 5  # 0 + 5
    assert team2_resources['food'] == 10  # 0 + 10
    assert team2_resources['raw_materials'] == 45  # 50 - 5


def test_reject_team_trade_offer(client, sample_game, db):
    """Test rejecting a trade offer"""
    game_code = sample_game["game_code"]
    
    # Setup game
    game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
    game.status = GameStatus.IN_PROGRESS
    
    if not game.game_state:
        game.game_state = {}
    
    game.game_state['teams'] = {
        '1': {'resources': {'food': 50, 'currency': 100}, 'buildings': {}, 'nation_type': 'nation_1'},
        '2': {'resources': {'raw_materials': 50, 'currency': 100}, 'buildings': {}, 'nation_type': 'nation_2'}
    }
    flag_modified(game, 'game_state')
    db.commit()
    
    # Create an offer
    create_response = client.post(
        f"/api/v2/trading/games/{game_code}/team-trade/offer",
        json={
            "from_team": 1,
            "to_team": 2,
            "offering": {"food": 10},
            "requesting": {"raw_materials": 5}
        }
    )
    offer_id = create_response.json()["offer"]["offer_id"]
    
    # Reject the offer
    response = client.post(f"/api/v2/trading/games/{game_code}/team-trade/{offer_id}/reject")
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert data["offer"]["status"] == "rejected"


def test_counter_team_trade_offer(client, sample_game, db):
    """Test countering a trade offer"""
    game_code = sample_game["game_code"]
    
    # Setup game
    game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
    game.status = GameStatus.IN_PROGRESS
    
    if not game.game_state:
        game.game_state = {}
    
    game.game_state['teams'] = {
        '1': {'resources': {'food': 50, 'currency': 100}, 'buildings': {}, 'nation_type': 'nation_1'},
        '2': {'resources': {'raw_materials': 50, 'currency': 100}, 'buildings': {}, 'nation_type': 'nation_2'}
    }
    flag_modified(game, 'game_state')
    db.commit()
    
    # Create an offer
    create_response = client.post(
        f"/api/v2/trading/games/{game_code}/team-trade/offer",
        json={
            "from_team": 1,
            "to_team": 2,
            "offering": {"food": 10},
            "requesting": {"raw_materials": 5}
        }
    )
    offer_id = create_response.json()["offer"]["offer_id"]
    
    # Counter the offer
    response = client.post(
        f"/api/v2/trading/games/{game_code}/team-trade/{offer_id}/counter",
        json={
            "offering": {"food": 10},
            "requesting": {"raw_materials": 3},  # Counter with less requested
            "message": "How about 3 instead?"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert data["offer"]["status"] == "countered"
    assert data["offer"]["counter_offer"]["requesting"]["raw_materials"] == 3


def test_price_changes_after_trades(client, sample_game, db):
    """Test that prices change after multiple trades"""
    game_code = sample_game["game_code"]
    
    # Setup game
    game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
    game.status = GameStatus.IN_PROGRESS
    
    if not game.game_state:
        game.game_state = {}
    
    game.game_state['teams'] = {
        '1': {'resources': {'food': 10, 'currency': 1000}, 'buildings': {}, 'nation_type': 'nation_1'}
    }
    flag_modified(game, 'game_state')
    db.commit()
    
    # Get initial price
    initial_prices = client.get(f"/api/v2/trading/games/{game_code}/bank/prices").json()
    initial_sell_price = initial_prices["prices"]["food"]["sell"]
    
    # Execute multiple buy trades (high demand)
    for _ in range(5):
        client.post(
            f"/api/v2/trading/games/{game_code}/bank/trade",
            json={
                "team_number": 1,
                "resource": "food",
                "amount": 10,
                "trade_type": "buy"
            }
        )
    
    # Check new price
    new_prices = client.get(f"/api/v2/trading/games/{game_code}/bank/prices").json()
    new_sell_price = new_prices["prices"]["food"]["sell"]
    
    # Price should have increased due to high demand
    assert new_sell_price > initial_sell_price, f"Price should increase: {initial_sell_price} -> {new_sell_price}"
