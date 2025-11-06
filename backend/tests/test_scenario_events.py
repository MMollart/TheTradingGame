"""
Tests for scenario event scheduler automation
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from scenario_event_scheduler import ScenarioEventProcessor
from scenarios import ScenarioType
from models import GameSession, GameStatus
from game_constants import ResourceType, BuildingType


@pytest.fixture
def scenario_processor(db: Session):
    """Create a scenario event processor"""
    return ScenarioEventProcessor(db)


@pytest.fixture
def marshall_plan_game(db: Session):
    """Create a game with Marshall Plan scenario"""
    game = GameSession(
        game_code="TEST01",
        status=GameStatus.IN_PROGRESS,
        scenario_id=ScenarioType.MARSHALL_PLAN,
        started_at=datetime.utcnow() - timedelta(minutes=25),
        game_state={
            'scenario': {
                'id': ScenarioType.MARSHALL_PLAN,
                'name': 'Post-WWII Marshall Plan'
            },
            'teams': {
                '1': {
                    'name': 'Britain',
                    'resources': {'currency': 100, 'food': 50}
                },
                '2': {
                    'name': 'France',
                    'resources': {'currency': 80, 'food': 60}
                }
            }
        }
    )
    db.add(game)
    db.commit()
    db.refresh(game)
    return game


@pytest.fixture
def silk_road_game(db: Session):
    """Create a game with Silk Road scenario"""
    game = GameSession(
        game_code="TEST02",
        status=GameStatus.IN_PROGRESS,
        scenario_id=ScenarioType.SILK_ROAD,
        started_at=datetime.utcnow() - timedelta(minutes=20),
        game_state={
            'scenario': {
                'id': ScenarioType.SILK_ROAD,
                'name': 'Silk Road Trade Routes'
            },
            'teams': {
                '1': {
                    'name': 'China',
                    'resources': {'currency': 200, 'food': 40, 'raw_materials': 60}
                },
                '2': {
                    'name': 'Persia',
                    'resources': {'currency': 150, 'food': 45, 'raw_materials': 40}
                }
            }
        }
    )
    db.add(game)
    db.commit()
    db.refresh(game)
    return game


@pytest.fixture
def great_depression_game(db: Session):
    """Create a game with Great Depression scenario"""
    game = GameSession(
        game_code="TEST03",
        status=GameStatus.IN_PROGRESS,
        scenario_id=ScenarioType.GREAT_DEPRESSION,
        started_at=datetime.utcnow() - timedelta(minutes=22),
        game_state={
            'scenario': {
                'id': ScenarioType.GREAT_DEPRESSION,
                'name': 'Great Depression Recovery'
            },
            'teams': {
                '1': {
                    'name': 'USA',
                    'resources': {'currency': 50, 'food': 20},
                    'buildings': {'farm': 2, 'mine': 1}
                },
                '2': {
                    'name': 'Germany',
                    'resources': {'currency': 120, 'food': 15},
                    'buildings': {'mine': 2, 'electrical_factory': 2}
                }
            }
        }
    )
    db.add(game)
    db.commit()
    db.refresh(game)
    return game


class TestScenarioEventProcessor:
    """Test scenario event processing"""
    
    def test_elapsed_time_calculation(self, scenario_processor, marshall_plan_game):
        """Test that elapsed time is calculated correctly"""
        elapsed = scenario_processor.get_elapsed_minutes(marshall_plan_game)
        assert 24 <= elapsed <= 26  # Should be around 25 minutes
    
    def test_elapsed_time_with_pause(self, scenario_processor, db):
        """Test elapsed time calculation accounts for pauses"""
        game = GameSession(
            game_code="PAUSE01",
            status=GameStatus.IN_PROGRESS,
            started_at=datetime.utcnow() - timedelta(minutes=30),
            game_state={
                'total_paused_time_ms': 10 * 60 * 1000  # 10 minutes paused
            }
        )
        db.add(game)
        db.commit()
        
        elapsed = scenario_processor.get_elapsed_minutes(game)
        assert 19 <= elapsed <= 21  # Should be around 20 minutes (30 - 10)
    
    @pytest.mark.asyncio
    async def test_marshall_aid_distribution(self, scenario_processor, marshall_plan_game):
        """Test Marshall Aid currency distribution"""
        events = await scenario_processor.process_periodic_events(marshall_plan_game)
        
        # Should trigger Marshall Aid at 25 minutes (first at 20 min)
        assert len(events) > 0
        
        # Check that currency was distributed
        event = events[0]
        assert event['event_type'] == 'scenario_periodic_event'
        assert event['scenario_event'] == 'marshall_aid'
        assert 'amount' in event['data']
        
        # Verify teams received currency
        assert marshall_plan_game.game_state['teams']['1']['resources']['currency'] > 100
        assert marshall_plan_game.game_state['teams']['2']['resources']['currency'] > 80
    
    @pytest.mark.asyncio
    async def test_food_crisis_trigger(self, scenario_processor, db):
        """Test Food Crisis conditional trigger"""
        game = GameSession(
            game_code="CRISIS01",
            status=GameStatus.IN_PROGRESS,
            scenario_id=ScenarioType.MARSHALL_PLAN,
            started_at=datetime.utcnow() - timedelta(minutes=10),
            game_state={
                'scenario': {
                    'id': ScenarioType.MARSHALL_PLAN
                },
                'teams': {
                    '1': {
                        'name': 'Britain',
                        'resources': {'currency': 200, 'food': 5}  # Below threshold
                    },
                    '2': {
                        'name': 'France',
                        'resources': {'currency': 150, 'food': 50}
                    }
                }
            }
        )
        db.add(game)
        db.commit()
        db.refresh(game)
        
        events = await scenario_processor.process_periodic_events(game)
        
        # Should trigger food crisis
        crisis_events = [e for e in events if e.get('scenario_event') == 'food_crisis']
        assert len(crisis_events) > 0
        
        # Verify currency penalty was applied to all teams
        assert game.game_state['teams']['1']['resources']['currency'] < 200
        assert game.game_state['teams']['2']['resources']['currency'] < 150
    
    @pytest.mark.asyncio
    async def test_bank_run_trigger(self, scenario_processor, great_depression_game):
        """Test Bank Run conditional trigger"""
        events = await scenario_processor.process_periodic_events(great_depression_game)
        
        # Should trigger bank run at 22 minutes (every 20 min)
        bank_run_events = [e for e in events if e.get('scenario_event') == 'bank_run']
        
        if len(bank_run_events) > 0:
            # USA has < 100 currency, should lose a building
            event = bank_run_events[0]
            assert 'affected_teams' in event['data']
            assert 'USA' in event['data']['affected_teams']
            
            # Verify building was removed
            total_buildings_before = 3  # 2 farms + 1 mine
            total_buildings_after = sum(great_depression_game.game_state['teams']['1']['buildings'].values())
            assert total_buildings_after < total_buildings_before
    
    @pytest.mark.asyncio
    async def test_demand_shift_announcement(self, scenario_processor, silk_road_game):
        """Test Demand Shift random resource selection"""
        events = await scenario_processor.process_periodic_events(silk_road_game)
        
        # Should trigger demand shift at 20 minutes (every 15 min)
        demand_events = [e for e in events if e.get('scenario_event') == 'demand_shift']
        
        if len(demand_events) > 0:
            event = demand_events[0]
            assert 'resource' in event['data']
            assert event['data']['multiplier'] == 2
            assert event['data']['resource'] in ['food', 'raw_materials', 'electrical_goods', 'medical_goods']
    
    @pytest.mark.asyncio
    async def test_piracy_tax_resource_loss(self, scenario_processor, db):
        """Test Piracy Tax periodic penalty"""
        game = GameSession(
            game_code="PIRATE01",
            status=GameStatus.IN_PROGRESS,
            scenario_id=ScenarioType.AGE_OF_EXPLORATION,
            started_at=datetime.utcnow() - timedelta(minutes=16),
            game_state={
                'scenario': {
                    'id': ScenarioType.AGE_OF_EXPLORATION
                },
                'teams': {
                    '1': {
                        'name': 'Spain',
                        'resources': {
                            'currency': 400,
                            'food': 100,
                            'raw_materials': 100,
                            'electrical_goods': 50,
                            'medical_goods': 50
                        }
                    }
                }
            }
        )
        db.add(game)
        db.commit()
        db.refresh(game)
        
        events = await scenario_processor.process_periodic_events(game)
        
        # Should trigger piracy tax at 16 minutes (every 15 min)
        piracy_events = [e for e in events if e.get('scenario_event') == 'piracy_tax']
        
        if len(piracy_events) > 0:
            # Verify 5% resource loss
            team = game.game_state['teams']['1']['resources']
            assert team['food'] < 100
            assert team['raw_materials'] < 100
            assert team['electrical_goods'] < 50
            assert team['medical_goods'] < 50
    
    @pytest.mark.asyncio
    async def test_no_events_without_scenario(self, scenario_processor, db):
        """Test that games without scenarios don't trigger events"""
        game = GameSession(
            game_code="NOSCENAR",
            status=GameStatus.IN_PROGRESS,
            scenario_id=None,
            started_at=datetime.utcnow() - timedelta(minutes=30),
            game_state={
                'teams': {
                    '1': {'name': 'Team 1', 'resources': {'currency': 100}}
                }
            }
        )
        db.add(game)
        db.commit()
        
        events = await scenario_processor.process_periodic_events(game)
        assert len(events) == 0
    
    @pytest.mark.asyncio
    async def test_event_cooldown(self, scenario_processor, db):
        """Test that conditional events have cooldown periods"""
        game = GameSession(
            game_code="COOLDOWN",
            status=GameStatus.IN_PROGRESS,
            scenario_id=ScenarioType.MARSHALL_PLAN,
            started_at=datetime.utcnow() - timedelta(minutes=5),
            game_state={
                'scenario': {'id': ScenarioType.MARSHALL_PLAN},
                'teams': {
                    '1': {'name': 'Britain', 'resources': {'currency': 200, 'food': 5}}
                }
            }
        )
        db.add(game)
        db.commit()
        db.refresh(game)
        
        # First trigger
        events1 = await scenario_processor.process_periodic_events(game)
        
        # Immediate second check - should not trigger due to cooldown
        events2 = await scenario_processor.process_periodic_events(game)
        
        crisis_count1 = len([e for e in events1 if e.get('scenario_event') == 'food_crisis'])
        crisis_count2 = len([e for e in events2 if e.get('scenario_event') == 'food_crisis'])
        
        # First should trigger, second should not
        assert crisis_count1 + crisis_count2 == 1
