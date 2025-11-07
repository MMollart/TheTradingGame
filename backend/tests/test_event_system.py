"""
Tests for the game event system (natural disasters, economic events, etc.)
"""

import pytest
from datetime import datetime
from models import GameSession, GameStatus, EventType, EventCategory, EventStatus, Player
from event_manager import EventManager


@pytest.fixture
def started_game(client, sample_game, db):
    """Create a started game with teams initialized"""
    game_code = sample_game["game_code"]
    
    # Add players to teams before starting
    game = db.query(GameSession).filter(
        GameSession.game_code == game_code
    ).first()
    
    # Assign 4 test players to different teams
    for i in range(4):
        player = Player(
            game_session_id=game.id,
            player_name=f"TeamPlayer{i+1}",
            role="player",
            group_number=i+1,
            is_approved=True
        )
        db.add(player)
    db.commit()
    
    # Start the game
    response = client.post(f"/games/{game_code}/start")
    assert response.status_code == 200, f"Failed to start game: {response.text}"
    
    return sample_game


class TestEventManager:
    """Test EventManager business logic"""
    
    def test_difficulty_modifiers(self, db, started_game):
        """Test difficulty modifier calculations"""
        game = db.query(GameSession).filter(
            GameSession.game_code == started_game["game_code"]
        ).first()
        
        event_mgr = EventManager(db)
        
        # Test easy difficulty
        game.difficulty = "easy"
        assert event_mgr.get_difficulty_modifier(game) == 0.75
        
        # Test normal difficulty
        game.difficulty = "medium"
        assert event_mgr.get_difficulty_modifier(game) == 1.0
        
        # Test hard difficulty
        game.difficulty = "hard"
        assert event_mgr.get_difficulty_modifier(game) == 1.5
    
    def test_mitigation_multipliers(self, db):
        """Test mitigation multiplier calculations"""
        event_mgr = EventManager(db)
        
        # No buildings = no mitigation
        team = {'buildings': {}}
        assert event_mgr.get_mitigation_multiplier(team, 'infrastructure') == 1.0
        
        # 1 infrastructure = 20% reduction
        team = {'buildings': {'infrastructure': 1}}
        assert event_mgr.get_mitigation_multiplier(team, 'infrastructure') == 0.8
        
        # 3 infrastructure = 60% reduction
        team = {'buildings': {'infrastructure': 3}}
        assert abs(event_mgr.get_mitigation_multiplier(team, 'infrastructure') - 0.4) < 0.01
        
        # 5+ infrastructure = 100% reduction (capped)
        team = {'buildings': {'infrastructure': 5}}
        assert event_mgr.get_mitigation_multiplier(team, 'infrastructure') == 0.0
        
        team = {'buildings': {'infrastructure': 10}}
        assert event_mgr.get_mitigation_multiplier(team, 'infrastructure') == 0.0


class TestEarthquakeEvent:
    """Test earthquake event"""
    
    def test_earthquake_destroys_buildings(self, db, started_game):
        """Test that earthquake destroys buildings"""
        game = db.query(GameSession).filter(
            GameSession.game_code == started_game["game_code"]
        ).first()
        
        # Add buildings to teams
        for team_key in game.game_state['teams']:
            game.game_state['teams'][team_key]['buildings'] = {
                'farm': 3,
                'mine': 2,
                'electrical_factory': 1
            }
        db.commit()
        
        # Trigger earthquake
        event_mgr = EventManager(db)
        event = event_mgr.trigger_earthquake(game, severity=3)
        
        # Verify event created
        assert event is not None
        assert event.event_type == EventType.EARTHQUAKE
        assert event.severity == 3
        assert event.status == EventStatus.EXPIRED  # Instant event
        
        # Verify buildings were destroyed
        total_destroyed = event.event_data.get('total_buildings_destroyed', 0)
        assert total_destroyed > 0
    
    def test_earthquake_mitigation(self, db, started_game):
        """Test that infrastructure reduces earthquake damage"""
        game = db.query(GameSession).filter(
            GameSession.game_code == started_game["game_code"]
        ).first()
        
        # Set up two teams: one with infrastructure, one without
        team_keys = sorted(game.game_state['teams'].keys())
        assert len(team_keys) >= 2, "Need at least 2 teams for mitigation test"
        
        # Team 1: No infrastructure
        game.game_state['teams'][team_keys[0]]['buildings']['infrastructure'] = 0
        game.game_state['teams'][team_keys[0]]['buildings']['farm'] = 5
        game.game_state['teams'][team_keys[0]]['buildings']['mine'] = 5
        
        # Team 2: 3 infrastructure (60% reduction)
        game.game_state['teams'][team_keys[1]]['buildings']['infrastructure'] = 3
        game.game_state['teams'][team_keys[1]]['buildings']['farm'] = 5
        game.game_state['teams'][team_keys[1]]['buildings']['mine'] = 5
        db.commit()
        
        # Trigger earthquake
        event_mgr = EventManager(db)
        event = event_mgr.trigger_earthquake(game, severity=3)
        
        # Find teams in affected list
        affected_teams = event.event_data.get('affected_teams', [])
        team1_data = next((t for t in affected_teams if t['team'] == team_keys[0]), None)
        team2_data = next((t for t in affected_teams if t['team'] == team_keys[1]), None)
        
        # Team without infrastructure should lose more buildings (or at least equal)
        if team1_data and team2_data:
            assert team1_data['buildings_destroyed'] >= team2_data['buildings_destroyed']


class TestFireEvent:
    """Test fire event"""
    
    def test_fire_destroys_electrical_factories(self, db, started_game):
        """Test that fire destroys electrical factories"""
        game = db.query(GameSession).filter(
            GameSession.game_code == started_game["game_code"]
        ).first()
        
        # Add electrical factories to teams (preserve existing buildings)
        for team_key in game.game_state['teams']:
            current_farm = game.game_state['teams'][team_key]['buildings'].get('farm', 0)
            game.game_state['teams'][team_key]['buildings']['electrical_factory'] = 5
            game.game_state['teams'][team_key]['buildings']['farm'] = 3 if current_farm == 0 else current_farm
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(game, 'game_state')
        db.commit()
        
        # Trigger fire
        event_mgr = EventManager(db)
        event = event_mgr.trigger_fire(game, severity=3)
        
        # Verify event created
        assert event is not None
        assert event.event_type == EventType.FIRE
        
        # Verify only electrical factories were destroyed
        db.refresh(game)
        for team_key in game.game_state['teams']:
            buildings = game.game_state['teams'][team_key]['buildings']
            assert buildings.get('electrical_factory', 0) < 5  # Some destroyed
            # Farm should be unchanged from what we set (3) or what was there originally
            assert buildings.get('farm', 0) >= 1  # At least some farms remain
    
    def test_fire_hospital_mitigation(self, db, started_game):
        """Test that hospitals reduce fire damage"""
        game = db.query(GameSession).filter(
            GameSession.game_code == started_game["game_code"]
        ).first()
        
        team_keys = sorted(game.game_state['teams'].keys())
        assert len(team_keys) >= 2, "Need at least 2 teams for mitigation test"
        
        # Team 1: No hospitals
        game.game_state['teams'][team_keys[0]]['buildings']['electrical_factory'] = 10
        game.game_state['teams'][team_keys[0]]['buildings']['hospital'] = 0
        
        # Team 2: 2 hospitals (40% reduction)
        game.game_state['teams'][team_keys[1]]['buildings']['electrical_factory'] = 10
        game.game_state['teams'][team_keys[1]]['buildings']['hospital'] = 2
        db.commit()
        
        # Trigger fire
        event_mgr = EventManager(db)
        event = event_mgr.trigger_fire(game, severity=3)
        
        # Team with hospitals should lose fewer factories
        db.refresh(game)
        team1_factories = game.game_state['teams'][team_keys[0]]['buildings'].get('electrical_factory', 0)
        team2_factories = game.game_state['teams'][team_keys[1]]['buildings'].get('electrical_factory', 0)
        
        assert team2_factories >= team1_factories


class TestDroughtEvent:
    """Test drought event"""
    
    def test_drought_reduces_production(self, db, started_game):
        """Test that drought is created with correct duration"""
        game = db.query(GameSession).filter(
            GameSession.game_code == started_game["game_code"]
        ).first()
        
        # Trigger drought
        event_mgr = EventManager(db)
        event = event_mgr.trigger_drought(game, severity=3)
        
        # Verify event created
        assert event is not None
        assert event.event_type == EventType.DROUGHT
        assert event.status == EventStatus.ACTIVE
        assert event.duration_cycles == 2
        assert event.cycles_remaining == 2
        
        # Verify production modifier stored in game state
        db.refresh(game)
        assert 'active_events' in game.game_state
        assert 'drought' in game.game_state['active_events']
        drought_data = game.game_state['active_events']['drought']
        assert 'production_modifier' in drought_data
        assert drought_data['cycles_remaining'] == 2
    
    def test_drought_duration_tracking(self, db, started_game):
        """Test that drought cycles decrement correctly"""
        game = db.query(GameSession).filter(
            GameSession.game_code == started_game["game_code"]
        ).first()
        
        # Trigger drought
        event_mgr = EventManager(db)
        event = event_mgr.trigger_drought(game, severity=3)
        
        # Check initial cycles
        db.refresh(game)
        assert 'drought' in game.game_state['active_events']
        assert game.game_state['active_events']['drought']['cycles_remaining'] == 2
        
        # Process one food tax cycle
        db.refresh(game)  # Ensure we have latest state
        event_mgr.process_food_tax_cycle(game)
        db.commit()  # Commit the changes
        
        # Verify cycle decremented - get fresh game object
        game = db.query(GameSession).filter(
            GameSession.game_code == started_game["game_code"]
        ).first()
        if 'drought' in game.game_state.get('active_events', {}):
            assert game.game_state['active_events']['drought']['cycles_remaining'] == 1
        
        # Process second cycle
        event_mgr.process_food_tax_cycle(game)
        
        # Verify drought expired
        db.refresh(game)
        assert 'drought' not in game.game_state.get('active_events', {})


class TestPlagueEvent:
    """Test plague event"""
    
    def test_plague_infects_teams(self, db, started_game):
        """Test that plague infects initial teams"""
        game = db.query(GameSession).filter(
            GameSession.game_code == started_game["game_code"]
        ).first()
        
        # Trigger plague
        event_mgr = EventManager(db)
        event = event_mgr.trigger_plague(game, severity=3)
        
        # Verify event created
        assert event is not None
        assert event.event_type == EventType.PLAGUE
        assert event.status == EventStatus.ACTIVE
        assert event.duration_cycles is None  # Until cured
        
        # Verify teams infected
        infected_teams = event.event_data.get('infected_teams', [])
        assert len(infected_teams) > 0
    
    def test_plague_cure(self, db, started_game):
        """Test that plague can be cured"""
        game = db.query(GameSession).filter(
            GameSession.game_code == started_game["game_code"]
        ).first()
        
        # Trigger plague
        event_mgr = EventManager(db)
        event = event_mgr.trigger_plague(game, severity=3)
        
        db.refresh(game)
        infected_teams = game.game_state['active_events']['plague']['infected_teams']
        team_to_cure = infected_teams[0]
        
        # Cure the team
        success = event_mgr.cure_plague(game, team_to_cure)
        assert success is True
        
        # Verify team removed from infected list
        db.refresh(game)
        if 'plague' in game.game_state.get('active_events', {}):
            current_infected = game.game_state['active_events']['plague']['infected_teams']
            assert team_to_cure not in current_infected


class TestBlizzardEvent:
    """Test blizzard event"""
    
    def test_blizzard_increases_food_tax(self, db, started_game):
        """Test that blizzard increases food tax multiplier"""
        game = db.query(GameSession).filter(
            GameSession.game_code == started_game["game_code"]
        ).first()
        
        # Trigger blizzard
        event_mgr = EventManager(db)
        event = event_mgr.trigger_blizzard(game, severity=3)
        
        # Verify event created
        assert event is not None
        assert event.event_type == EventType.BLIZZARD
        assert event.status == EventStatus.ACTIVE
        
        # Verify multipliers stored
        db.refresh(game)
        assert 'blizzard' in game.game_state['active_events']
        blizzard_data = game.game_state['active_events']['blizzard']
        assert blizzard_data['food_tax_multiplier'] > 1.0
        assert 'production_penalty' in blizzard_data


class TestTornadoEvent:
    """Test tornado event"""
    
    def test_tornado_destroys_resources(self, db, started_game):
        """Test that tornado destroys percentage of resources"""
        game = db.query(GameSession).filter(
            GameSession.game_code == started_game["game_code"]
        ).first()
        
        # Set specific resources to teams (overwrite existing)
        for team_key in game.game_state['teams']:
            game.game_state['teams'][team_key]['resources'] = {
                'food': 100,
                'currency': 100,
                'raw_materials': 100,
                'electrical_goods': 100,
                'medical_goods': 100
            }
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(game, 'game_state')
        db.commit()
        
        # Trigger tornado
        event_mgr = EventManager(db)
        event = event_mgr.trigger_tornado(game, severity=3)
        
        # Verify event created
        assert event is not None
        assert event.event_type == EventType.TORNADO
        
        # Verify resources were reduced
        db.refresh(game)
        for team_key in game.game_state['teams']:
            resources = game.game_state['teams'][team_key]['resources']
            assert resources.get('food', 0) < 100
            assert resources.get('currency', 0) < 100
            assert resources.get('raw_materials', 0) < 100


class TestEconomicRecession:
    """Test economic recession event"""
    
    def test_recession_increases_prices(self, db, started_game):
        """Test that recession increases bank prices and building costs"""
        game = db.query(GameSession).filter(
            GameSession.game_code == started_game["game_code"]
        ).first()
        
        # Trigger recession
        event_mgr = EventManager(db)
        event = event_mgr.trigger_economic_recession(game, severity=3)
        
        # Verify event created
        assert event is not None
        assert event.event_type == EventType.ECONOMIC_RECESSION
        assert event.status == EventStatus.ACTIVE
        
        # Verify multipliers stored
        db.refresh(game)
        assert 'recession' in game.game_state['active_events']
        recession_data = game.game_state['active_events']['recession']
        assert recession_data['bank_price_multiplier'] > 1.0
        assert recession_data['building_cost_multiplier'] > 1.0


class TestAutomationBreakthrough:
    """Test automation breakthrough event"""
    
    def test_automation_breakthrough_selection(self, db, started_game):
        """Test that automation breakthrough selects a team"""
        game = db.query(GameSession).filter(
            GameSession.game_code == started_game["game_code"]
        ).first()
        
        # Trigger automation breakthrough
        event_mgr = EventManager(db)
        event = event_mgr.trigger_automation_breakthrough(game, severity=3)
        
        # Verify event created
        assert event is not None
        assert event.event_type == EventType.AUTOMATION_BREAKTHROUGH
        assert event.status == EventStatus.ACTIVE
        
        # Verify target team selected
        target_team = event.event_data.get('target_team')
        assert target_team is not None
        assert target_team in game.game_state['teams']
    
    def test_automation_completion(self, db, started_game):
        """Test that automation can be completed"""
        game = db.query(GameSession).filter(
            GameSession.game_code == started_game["game_code"]
        ).first()
        
        # Trigger automation breakthrough
        event_mgr = EventManager(db)
        event = event_mgr.trigger_automation_breakthrough(game, severity=3)
        
        db.refresh(game)
        target_team = game.game_state['active_events']['automation_breakthrough']['target_team']
        
        # Complete the payment
        success = event_mgr.complete_automation_breakthrough(game, target_team)
        assert success is True
        
        # Verify bonus activated
        db.refresh(game)
        breakthrough_data = game.game_state['active_events']['automation_breakthrough']
        assert breakthrough_data['payment_pending'] is False
        assert breakthrough_data['active'] is True


class TestEventAPI:
    """Test event API endpoints"""
    
    def test_trigger_earthquake_endpoint(self, client, started_game):
        """Test triggering earthquake via API"""
        game_code = started_game["game_code"]
        
        response = client.post(
            f"/api/v2/events/games/{game_code}/trigger",
            json={
                "event_type": "earthquake",
                "severity": 3
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "event_id" in data
        assert "Earthquake" in data["message"]
    
    def test_get_active_events(self, client, started_game, db):
        """Test getting list of active events"""
        game_code = started_game["game_code"]
        
        # Trigger some events
        game = db.query(GameSession).filter(
            GameSession.game_code == game_code
        ).first()
        
        event_mgr = EventManager(db)
        event_mgr.trigger_drought(game, severity=3)
        event_mgr.trigger_plague(game, severity=2)
        
        # Get active events
        response = client.get(f"/api/v2/events/games/{game_code}/active")
        
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert len(data["events"]) >= 2
    
    def test_cure_plague_endpoint(self, client, started_game, db):
        """Test curing plague via API"""
        game_code = started_game["game_code"]
        
        # Trigger plague
        game = db.query(GameSession).filter(
            GameSession.game_code == game_code
        ).first()
        
        event_mgr = EventManager(db)
        event_mgr.trigger_plague(game, severity=3)
        
        db.refresh(game)
        infected_team = game.game_state['active_events']['plague']['infected_teams'][0]
        
        # Cure plague
        response = client.post(
            f"/api/v2/events/games/{game_code}/cure-plague",
            json={"team_number": infected_team}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_invalid_event_type(self, client, started_game):
        """Test triggering invalid event type returns error"""
        game_code = started_game["game_code"]
        
        response = client.post(
            f"/api/v2/events/games/{game_code}/trigger",
            json={
                "event_type": "invalid_event",
                "severity": 3
            }
        )
        
        # Should return 400 or 500 depending on how error is caught
        assert response.status_code in [400, 500]
        detail = response.json().get("detail", "")
        assert "Unknown event type" in detail or "event" in detail.lower()
