"""
Tests for the automated food tax system
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from food_tax_manager import FoodTaxManager, TAX_INTERVALS, WARNING_BEFORE_TAX_MINUTES
from game_logic import GameLogic
from game_constants import (
    FOOD_TAX_DEVELOPED, FOOD_TAX_DEVELOPING, 
    ResourceType, BuildingType, FAMINE_PENALTY_MULTIPLIER
)
from models import GameSession, GameStatus


class TestTaxIntervalCalculations:
    """Test tax interval calculations based on difficulty and duration"""
    
    def test_easy_difficulty_60_min_game(self):
        """Easy difficulty, 60-minute game should have 15-minute tax intervals"""
        manager = FoodTaxManager(Mock())
        interval = manager.get_tax_interval_minutes("easy", 60)
        assert interval == 15
    
    def test_easy_difficulty_90_min_game(self):
        """Easy difficulty, 90-minute game should have 20-minute tax intervals (default)"""
        manager = FoodTaxManager(Mock())
        interval = manager.get_tax_interval_minutes("easy", 90)
        assert interval == 20
    
    def test_medium_difficulty_60_min_game(self):
        """Medium difficulty, 60-minute game should have 11-minute tax intervals"""
        manager = FoodTaxManager(Mock())
        interval = manager.get_tax_interval_minutes("medium", 60)
        assert interval == 11
    
    def test_medium_difficulty_90_min_game(self):
        """Medium difficulty, 90-minute game should have 15-minute tax intervals (default)"""
        manager = FoodTaxManager(Mock())
        interval = manager.get_tax_interval_minutes("medium", 90)
        assert interval == 15
    
    def test_hard_difficulty_60_min_game(self):
        """Hard difficulty, 60-minute game should have 7-minute tax intervals"""
        manager = FoodTaxManager(Mock())
        interval = manager.get_tax_interval_minutes("hard", 60)
        assert interval == 7
    
    def test_hard_difficulty_90_min_game(self):
        """Hard difficulty, 90-minute game should have 10-minute tax intervals (default)"""
        manager = FoodTaxManager(Mock())
        interval = manager.get_tax_interval_minutes("hard", 90)
        assert interval == 10
    
    def test_all_difficulty_levels(self):
        """Test all combinations of difficulty and duration"""
        manager = FoodTaxManager(Mock())
        
        for difficulty, durations in TAX_INTERVALS.items():
            for duration, expected_interval in durations.items():
                interval = manager.get_tax_interval_minutes(difficulty, duration)
                assert interval == expected_interval, \
                    f"Failed for {difficulty} difficulty, {duration} min game"
    
    def test_invalid_difficulty_defaults_to_medium(self):
        """Invalid difficulty should default to medium"""
        manager = FoodTaxManager(Mock())
        interval = manager.get_tax_interval_minutes("invalid", 90)
        assert interval == 15  # medium, 90 min
    
    def test_invalid_duration_defaults_to_90_min(self):
        """Invalid duration should default to 90 minutes"""
        manager = FoodTaxManager(Mock())
        interval = manager.get_tax_interval_minutes("medium", 999)
        assert interval == 15  # medium, 90 min


class TestTaxAmountCalculations:
    """Test food tax amount calculations with School building effect"""
    
    def test_developed_nation_base_tax(self):
        """Developed nation should pay 15 food tax without School"""
        manager = FoodTaxManager(Mock())
        team_state = {
            "is_developed": True,
            "buildings": {}
        }
        tax_amount = manager.calculate_food_tax_amount(team_state)
        assert tax_amount == FOOD_TAX_DEVELOPED  # 15
    
    def test_developing_nation_base_tax(self):
        """Developing nation should pay 5 food tax without School"""
        manager = FoodTaxManager(Mock())
        team_state = {
            "is_developed": False,
            "buildings": {}
        }
        tax_amount = manager.calculate_food_tax_amount(team_state)
        assert tax_amount == FOOD_TAX_DEVELOPING  # 5
    
    def test_developed_nation_with_school(self):
        """School should increase tax by 50% for developed nations"""
        manager = FoodTaxManager(Mock())
        team_state = {
            "is_developed": True,
            "buildings": {
                BuildingType.SCHOOL.value: 1
            }
        }
        tax_amount = manager.calculate_food_tax_amount(team_state)
        expected = int(FOOD_TAX_DEVELOPED * 1.5)  # 15 * 1.5 = 22.5 -> 22
        assert tax_amount == expected
    
    def test_developing_nation_with_school(self):
        """School should increase tax by 50% for developing nations"""
        manager = FoodTaxManager(Mock())
        team_state = {
            "is_developed": False,
            "buildings": {
                BuildingType.SCHOOL.value: 1
            }
        }
        tax_amount = manager.calculate_food_tax_amount(team_state)
        expected = int(FOOD_TAX_DEVELOPING * 1.5)  # 5 * 1.5 = 7.5 -> 7
        assert tax_amount == expected
    
    def test_multiple_schools_same_effect(self):
        """Multiple schools should have same effect as one school"""
        manager = FoodTaxManager(Mock())
        team_state_one = {
            "is_developed": True,
            "buildings": {BuildingType.SCHOOL.value: 1}
        }
        team_state_three = {
            "is_developed": True,
            "buildings": {BuildingType.SCHOOL.value: 3}
        }
        tax_one = manager.calculate_food_tax_amount(team_state_one)
        tax_three = manager.calculate_food_tax_amount(team_state_three)
        assert tax_one == tax_three


class TestTaxApplicationWithRestaurant:
    """Test food tax application with restaurant bonuses"""
    
    def test_restaurant_generates_currency_on_tax_payment(self):
        """Restaurant should generate currency when tax is paid"""
        team_state = {
            "is_developed": True,
            "resources": {
                ResourceType.FOOD.value: 50,
                ResourceType.CURRENCY.value: 100
            },
            "buildings": {
                BuildingType.RESTAURANT.value: 2
            }
        }
        
        success, message, new_state = GameLogic.apply_food_tax(team_state)
        
        assert success
        assert new_state["resources"][ResourceType.FOOD.value] == 50 - 15  # 35
        # Restaurant bonus: 15 food * 5 currency per food * 2 restaurants = 150
        assert new_state["resources"][ResourceType.CURRENCY.value] == 100 + 150  # 250
        assert "Restaurants generated" in message
    
    def test_no_restaurant_bonus_during_famine(self):
        """Restaurants should not generate currency during famine"""
        team_state = {
            "is_developed": True,
            "resources": {
                ResourceType.FOOD.value: 5,  # Not enough for 15 food tax
                ResourceType.CURRENCY.value: 100
            },
            "buildings": {
                BuildingType.RESTAURANT.value: 2
            }
        }
        
        success, message, new_state = GameLogic.apply_food_tax(team_state)
        
        assert success
        assert "FAMINE" in message
        # Currency should be spent on famine penalty, not gained from restaurants
        assert new_state["resources"][ResourceType.CURRENCY.value] < 100


class TestFamineHandling:
    """Test famine penalty when teams can't pay food tax"""
    
    def test_famine_penalty_calculation(self):
        """Famine should cost 2x bank price in currency"""
        team_state = {
            "is_developed": True,  # 15 food tax
            "resources": {
                ResourceType.FOOD.value: 5,  # Only have 5 food
                ResourceType.CURRENCY.value: 200
            },
            "buildings": {}
        }
        
        success, message, new_state = GameLogic.apply_food_tax(team_state)
        
        assert success
        assert "FAMINE" in message
        assert new_state["resources"][ResourceType.FOOD.value] == 0
        
        # Shortage = 15 - 5 = 10 food
        # Bank price = 2 currency per food (from BANK_INITIAL_PRICES)
        # Penalty = 10 * 2 * 2 = 40 currency
        expected_currency = 200 - 40
        assert new_state["resources"][ResourceType.CURRENCY.value] == expected_currency
    
    def test_cannot_pay_famine_penalty(self):
        """Should fail if can't pay famine penalty"""
        team_state = {
            "is_developed": True,  # 15 food tax
            "resources": {
                ResourceType.FOOD.value: 0,
                ResourceType.CURRENCY.value: 10  # Not enough currency
            },
            "buildings": {}
        }
        
        success, message, new_state = GameLogic.apply_food_tax(team_state)
        
        assert not success
        assert "Cannot pay" in message or "Need" in message


class TestPauseAwareTimings:
    """Test pause-aware timing adjustments"""
    
    def test_adjust_for_pause_adds_duration(self, db_session):
        """Pause adjustment should add duration to next_tax_due"""
        # Create a mock game with food tax tracking
        game = GameSession(
            game_code="TEST01",
            status=GameStatus.IN_PROGRESS,
            difficulty="medium",
            game_duration_minutes=90,
            game_state={
                'teams': {
                    '1': {'is_developed': True}
                },
                'food_tax': {
                    '1': {
                        'next_tax_due': datetime.utcnow().isoformat(),
                        'warning_sent': False,
                        'tax_interval_minutes': 15
                    }
                }
            }
        )
        db_session.add(game)
        db_session.commit()
        
        original_due = datetime.fromisoformat(game.game_state['food_tax']['1']['next_tax_due'])
        
        manager = FoodTaxManager(db_session)
        pause_duration_ms = 120000  # 2 minutes
        result = manager.adjust_for_pause("TEST01", pause_duration_ms)
        
        assert result['success']
        assert '1' in result['adjusted_teams']
        
        # Refresh game
        db_session.refresh(game)
        new_due = datetime.fromisoformat(game.game_state['food_tax']['1']['next_tax_due'])
        
        # New due time should be 2 minutes later
        time_diff = (new_due - original_due).total_seconds()
        assert abs(time_diff - 120) < 1  # Allow 1 second tolerance
    
    def test_adjust_resets_warning_flag(self, db_session):
        """Pause adjustment should reset warning_sent flag"""
        game = GameSession(
            game_code="TEST02",
            status=GameStatus.IN_PROGRESS,
            game_state={
                'teams': {'1': {}},
                'food_tax': {
                    '1': {
                        'next_tax_due': datetime.utcnow().isoformat(),
                        'warning_sent': True,  # Warning was sent
                        'tax_interval_minutes': 15
                    }
                }
            }
        )
        db_session.add(game)
        db_session.commit()
        
        manager = FoodTaxManager(db_session)
        manager.adjust_for_pause("TEST02", 60000)
        
        db_session.refresh(game)
        assert not game.game_state['food_tax']['1']['warning_sent']


class TestTaxInitialization:
    """Test food tax tracking initialization"""
    
    def test_initialize_creates_tracking(self, db_session):
        """Initialization should create food_tax tracking for all teams"""
        game = GameSession(
            game_code="TEST03",
            status=GameStatus.WAITING,
            difficulty="medium",
            game_duration_minutes=90,
            game_state={
                'teams': {
                    '1': {'is_developed': True},
                    '2': {'is_developed': False}
                }
            }
        )
        db_session.add(game)
        db_session.commit()
        
        manager = FoodTaxManager(db_session)
        manager.initialize_food_tax_tracking(game)
        
        db_session.refresh(game)
        
        assert 'food_tax' in game.game_state
        assert '1' in game.game_state['food_tax']
        assert '2' in game.game_state['food_tax']
        
        for team_num in ['1', '2']:
            tax_data = game.game_state['food_tax'][team_num]
            assert tax_data['last_tax_time'] is None
            assert tax_data['next_tax_due'] is not None
            assert tax_data['warning_sent'] is False
            assert tax_data['tax_interval_minutes'] == 15  # medium, 90 min
            assert tax_data['total_taxes_paid'] == 0
            assert tax_data['total_famines'] == 0
    
    def test_initialize_sets_correct_interval(self, db_session):
        """Initialization should use correct tax interval based on difficulty"""
        for difficulty, expected_interval in [("easy", 20), ("medium", 15), ("hard", 10)]:
            game = GameSession(
                game_code=f"TEST_{difficulty.upper()}",
                status=GameStatus.WAITING,
                difficulty=difficulty,
                game_duration_minutes=90,
                game_state={'teams': {'1': {}}}
            )
            db_session.add(game)
            db_session.commit()
            
            manager = FoodTaxManager(db_session)
            manager.initialize_food_tax_tracking(game)
            
            db_session.refresh(game)
            assert game.game_state['food_tax']['1']['tax_interval_minutes'] == expected_interval


class TestWarningSystem:
    """Test 3-minute warning system"""
    
    def test_warning_sent_before_tax_due(self, db_session):
        """Warning should be sent 3 minutes before tax is due"""
        # Set next tax due in 2 minutes (within warning window)
        next_due = datetime.utcnow() + timedelta(minutes=2)
        
        game = GameSession(
            game_code="TEST04",
            status=GameStatus.IN_PROGRESS,
            game_state={
                'teams': {'1': {}},
                'food_tax': {
                    '1': {
                        'next_tax_due': next_due.isoformat(),
                        'warning_sent': False,
                        'tax_interval_minutes': 15
                    }
                }
            }
        )
        db_session.add(game)
        db_session.commit()
        
        manager = FoodTaxManager(db_session)
        events = manager.check_and_process_taxes("TEST04")
        
        # Should get a warning event
        assert len(events) == 1
        assert events[0]['event_type'] == 'food_tax_warning'
        assert events[0]['data']['team_number'] == '1'
        
        # Warning flag should be set
        db_session.refresh(game)
        assert game.game_state['food_tax']['1']['warning_sent']
    
    def test_no_duplicate_warnings(self, db_session):
        """Warning should not be sent twice"""
        next_due = datetime.utcnow() + timedelta(minutes=2)
        
        game = GameSession(
            game_code="TEST05",
            status=GameStatus.IN_PROGRESS,
            game_state={
                'teams': {'1': {}},
                'food_tax': {
                    '1': {
                        'next_tax_due': next_due.isoformat(),
                        'warning_sent': True,  # Already sent
                        'tax_interval_minutes': 15
                    }
                }
            }
        )
        db_session.add(game)
        db_session.commit()
        
        manager = FoodTaxManager(db_session)
        events = manager.check_and_process_taxes("TEST05")
        
        # Should not get any events
        assert len(events) == 0


class TestAutomatedTaxApplication:
    """Test automated tax application"""
    
    def test_tax_applied_when_due(self, db_session):
        """Tax should be automatically applied when due time is reached"""
        # Set tax due in the past
        next_due = datetime.utcnow() - timedelta(minutes=1)
        
        game = GameSession(
            game_code="TEST06",
            status=GameStatus.IN_PROGRESS,
            game_state={
                'teams': {
                    '1': {
                        'is_developed': True,
                        'resources': {
                            ResourceType.FOOD.value: 50,
                            ResourceType.CURRENCY.value: 100
                        },
                        'buildings': {}
                    }
                },
                'food_tax': {
                    '1': {
                        'next_tax_due': next_due.isoformat(),
                        'warning_sent': True,
                        'tax_interval_minutes': 15,
                        'total_taxes_paid': 0,
                        'total_famines': 0
                    }
                },
                'bank_inventory': {
                    ResourceType.FOOD.value: 0
                }
            }
        )
        db_session.add(game)
        db_session.commit()
        
        manager = FoodTaxManager(db_session)
        events = manager.check_and_process_taxes("TEST06")
        
        # Should get tax applied event
        assert len(events) == 1
        assert events[0]['event_type'] == 'food_tax_applied'
        assert events[0]['data']['team_number'] == '1'
        assert events[0]['data']['success']
        
        # Check team resources updated
        db_session.refresh(game)
        team_state = game.game_state['teams']['1']
        assert team_state['resources'][ResourceType.FOOD.value] == 50 - 15  # 35
        
        # Check bank received food
        assert game.game_state['bank_inventory'][ResourceType.FOOD.value] == 15
        
        # Check statistics updated
        assert game.game_state['food_tax']['1']['total_taxes_paid'] == 1
        assert game.game_state['food_tax']['1']['total_famines'] == 0
        
        # Check next tax scheduled
        assert game.game_state['food_tax']['1']['last_tax_time'] is not None
        assert game.game_state['food_tax']['1']['warning_sent'] is False
    
    def test_famine_event_when_insufficient_food(self, db_session):
        """Famine event should be sent when team can't pay food tax"""
        next_due = datetime.utcnow() - timedelta(minutes=1)
        
        game = GameSession(
            game_code="TEST07",
            status=GameStatus.IN_PROGRESS,
            game_state={
                'teams': {
                    '1': {
                        'is_developed': True,
                        'resources': {
                            ResourceType.FOOD.value: 5,  # Not enough
                            ResourceType.CURRENCY.value: 100
                        },
                        'buildings': {}
                    }
                },
                'food_tax': {
                    '1': {
                        'next_tax_due': next_due.isoformat(),
                        'warning_sent': True,
                        'tax_interval_minutes': 15,
                        'total_taxes_paid': 0,
                        'total_famines': 0
                    }
                },
                'bank_inventory': {ResourceType.FOOD.value: 0}
            }
        )
        db_session.add(game)
        db_session.commit()
        
        manager = FoodTaxManager(db_session)
        events = manager.check_and_process_taxes("TEST07")
        
        # Should get famine event
        assert len(events) == 1
        assert events[0]['event_type'] == 'food_tax_famine'
        assert events[0]['data']['is_famine']
        
        # Check statistics updated
        db_session.refresh(game)
        assert game.game_state['food_tax']['1']['total_famines'] == 1
        assert game.game_state['food_tax']['1']['total_taxes_paid'] == 0


class TestTaxStatusAPI:
    """Test tax status retrieval"""
    
    def test_get_status_returns_all_teams(self, db_session):
        """Status should return information for all teams"""
        next_due = datetime.utcnow() + timedelta(minutes=10)
        
        game = GameSession(
            game_code="TEST08",
            status=GameStatus.IN_PROGRESS,
            difficulty="medium",
            game_duration_minutes=90,
            game_state={
                'teams': {
                    '1': {'is_developed': True, 'buildings': {}},
                    '2': {'is_developed': False, 'buildings': {}}
                },
                'food_tax': {
                    '1': {
                        'next_tax_due': next_due.isoformat(),
                        'warning_sent': False,
                        'tax_interval_minutes': 15,
                        'total_taxes_paid': 2,
                        'total_famines': 0,
                        'last_tax_time': None
                    },
                    '2': {
                        'next_tax_due': next_due.isoformat(),
                        'warning_sent': False,
                        'tax_interval_minutes': 15,
                        'total_taxes_paid': 1,
                        'total_famines': 1,
                        'last_tax_time': None
                    }
                }
            }
        )
        db_session.add(game)
        db_session.commit()
        
        manager = FoodTaxManager(db_session)
        status = manager.get_tax_status("TEST08")
        
        assert status['success']
        assert len(status['teams']) == 2
        
        # Check team 1
        team1 = status['teams']['1']
        assert team1['tax_amount'] == 15  # Developed nation
        assert team1['tax_interval_minutes'] == 15
        assert abs(team1['minutes_until_due'] - 10) < 0.2  # ~10 minutes
        assert team1['total_taxes_paid'] == 2
        assert team1['total_famines'] == 0
        
        # Check team 2
        team2 = status['teams']['2']
        assert team2['tax_amount'] == 5  # Developing nation
        assert team2['total_taxes_paid'] == 1
        assert team2['total_famines'] == 1
