"""
Food Tax Manager - Handles automated food tax collection

This module manages the automatic food tax system with:
- Difficulty-based tax intervals
- Game duration scaling
- Pause-aware timing
- 3-minute warnings
- Restaurant bonuses
- Famine penalties
"""

from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from models import GameSession, GameStatus
from game_constants import (
    FOOD_TAX_DEVELOPED, FOOD_TAX_DEVELOPING, FAMINE_PENALTY_MULTIPLIER,
    ResourceType, BuildingType, BANK_INITIAL_PRICES, BUILDING_BENEFITS
)
from game_logic import GameLogic


# Tax interval configurations
# Format: {difficulty: {game_duration_minutes: tax_interval_minutes}}
TAX_INTERVALS = {
    "easy": {
        60: 15,   # 60-minute game: tax every 15 minutes
        90: 20,   # 90-minute game: tax every 20 minutes (default)
        120: 25,  # 120-minute game: tax every 25 minutes
        150: 30,  # 150-minute game: tax every 30 minutes
        180: 35,  # 180-minute game: tax every 35 minutes
        210: 40,  # 210-minute game: tax every 40 minutes
        240: 45,  # 240-minute game: tax every 45 minutes
    },
    "medium": {
        60: 11,   # 60-minute game: tax every 11 minutes
        90: 15,   # 90-minute game: tax every 15 minutes (default)
        120: 18,  # 120-minute game: tax every 18 minutes
        150: 22,  # 150-minute game: tax every 22 minutes
        180: 26,  # 180-minute game: tax every 26 minutes
        210: 30,  # 210-minute game: tax every 30 minutes
        240: 34,  # 240-minute game: tax every 34 minutes
    },
    "hard": {
        60: 7,    # 60-minute game: tax every 7 minutes
        90: 10,   # 90-minute game: tax every 10 minutes (default)
        120: 12,  # 120-minute game: tax every 12 minutes
        150: 15,  # 150-minute game: tax every 15 minutes
        180: 17,  # 180-minute game: tax every 17 minutes
        210: 20,  # 210-minute game: tax every 20 minutes
        240: 22,  # 240-minute game: tax every 22 minutes
    }
}

WARNING_BEFORE_TAX_MINUTES = 3  # Warn teams 3 minutes before tax is due
SCHEDULER_CHECK_INTERVAL_SECONDS = 30  # How often to check for tax processing


class FoodTaxManager:
    """Manages automated food tax collection"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_tax_interval_minutes(self, difficulty: str, game_duration_minutes: int) -> int:
        """
        Calculate the tax interval based on difficulty and game duration.
        
        Args:
            difficulty: Game difficulty (easy, medium, hard)
            game_duration_minutes: Total game duration in minutes
            
        Returns:
            Tax interval in minutes
        """
        # Default to medium if invalid difficulty
        if difficulty not in TAX_INTERVALS:
            difficulty = "medium"
        
        # Default to 90 minutes if invalid duration
        if game_duration_minutes not in TAX_INTERVALS[difficulty]:
            game_duration_minutes = 90
        
        return TAX_INTERVALS[difficulty][game_duration_minutes]
    
    def calculate_food_tax_amount(self, team_state: Dict[str, Any]) -> int:
        """
        Calculate the food tax amount for a team.
        
        School building effect: Increases food tax (as per game rules).
        The tax amount is increased by 50% if the team has a school.
        
        Args:
            team_state: Team's current state
            
        Returns:
            Food tax amount
        """
        is_developed = team_state.get("is_developed", False)
        base_tax = FOOD_TAX_DEVELOPED if is_developed else FOOD_TAX_DEVELOPING
        
        # Check if team has a school building
        school_count = team_state.get("buildings", {}).get(BuildingType.SCHOOL.value, 0)
        
        if school_count > 0:
            # School increases food tax by 50%
            SCHOOL_TAX_MULTIPLIER = 1.5
            tax_amount = int(base_tax * SCHOOL_TAX_MULTIPLIER)
        else:
            tax_amount = base_tax
        
        return tax_amount
    
    def initialize_food_tax_tracking(self, game: GameSession) -> None:
        """
        Initialize food tax tracking for a game session.
        Called when the game starts.
        
        Args:
            game: GameSession instance
        """
        if not game.game_state:
            game.game_state = {}
        
        if 'food_tax' not in game.game_state:
            game.game_state['food_tax'] = {}
        
        # Get tax interval
        difficulty = game.difficulty or "medium"
        duration = game.game_duration_minutes or 90
        tax_interval = self.get_tax_interval_minutes(difficulty, duration)
        
        # Initialize tracking for each team
        current_time = datetime.utcnow()
        
        for team_number in game.game_state.get('teams', {}).keys():
            game.game_state['food_tax'][team_number] = {
                'last_tax_time': None,  # No tax applied yet
                'next_tax_due': (current_time + timedelta(minutes=tax_interval)).isoformat(),
                'warning_sent': False,
                'tax_interval_minutes': tax_interval,
                'total_taxes_paid': 0,
                'total_famines': 0
            }
        
        flag_modified(game, 'game_state')
        self.db.commit()
    
    def adjust_for_pause(self, game_code: str, pause_duration_ms: int) -> Dict[str, Any]:
        """
        Adjust food tax timings when game is resumed after a pause.
        
        Args:
            game_code: Game code
            pause_duration_ms: Duration of the pause in milliseconds
            
        Returns:
            Result dictionary with adjustment details
        """
        game = self.db.query(GameSession).filter(
            GameSession.game_code == game_code.upper()
        ).first()
        
        if not game:
            return {"success": False, "error": "Game not found"}
        
        if 'food_tax' not in game.game_state:
            return {"success": False, "error": "Food tax not initialized"}
        
        pause_duration_seconds = pause_duration_ms / 1000
        pause_delta = timedelta(seconds=pause_duration_seconds)
        
        adjusted_teams = []
        
        for team_number, tax_data in game.game_state['food_tax'].items():
            if tax_data.get('next_tax_due'):
                # Adjust next tax due time by adding pause duration
                old_due = datetime.fromisoformat(tax_data['next_tax_due'])
                new_due = old_due + pause_delta
                tax_data['next_tax_due'] = new_due.isoformat()
                
                # Reset warning flag if it was sent (will resend if still needed)
                tax_data['warning_sent'] = False
                
                adjusted_teams.append(team_number)
        
        flag_modified(game, 'game_state')
        self.db.commit()
        
        return {
            "success": True,
            "adjusted_teams": adjusted_teams,
            "pause_duration_seconds": pause_duration_seconds
        }
    
    def check_and_process_taxes(self, game_code: str) -> List[Dict[str, Any]]:
        """
        Check if any teams need to be warned or have tax applied.
        
        This should be called periodically (e.g., every 30 seconds) by a background task.
        
        Args:
            game_code: Game code
            
        Returns:
            List of events to broadcast via WebSocket
        """
        game = self.db.query(GameSession).filter(
            GameSession.game_code == game_code.upper()
        ).first()
        
        if not game:
            return []
        
        # Refresh the game object to ensure we have the latest status from the database
        # This is critical to avoid processing games that have ended or been paused
        self.db.refresh(game)
        
        # Only process games that are IN_PROGRESS (not WAITING, PAUSED, or COMPLETED)
        if game.status != GameStatus.IN_PROGRESS:
            return []
        
        if 'food_tax' not in game.game_state:
            return []
        
        current_time = datetime.utcnow()
        events = []
        tax_applied = False  # Track if any tax was applied this cycle
        
        for team_number, tax_data in game.game_state['food_tax'].items():
            next_due_str = tax_data.get('next_tax_due')
            if not next_due_str:
                continue
            
            next_due = datetime.fromisoformat(next_due_str)
            time_until_due = (next_due - current_time).total_seconds() / 60  # in minutes
            
            # Check if warning should be sent (3 minutes before)
            if (time_until_due <= WARNING_BEFORE_TAX_MINUTES and 
                time_until_due > 0 and 
                not tax_data.get('warning_sent', False)):
                
                events.append({
                    "type": "event",
                    "event_type": "food_tax_warning",
                    "data": {
                        "team_number": team_number,
                        "minutes_remaining": round(time_until_due, 1),
                        "next_tax_due": next_due_str
                    }
                })
                
                # Mark warning as sent
                tax_data['warning_sent'] = True
                flag_modified(game, 'game_state')
            
            # Check if tax is due
            elif time_until_due <= 0:
                # Apply tax
                result = self._apply_tax_to_team(game, team_number, tax_data)
                events.append(result)
                tax_applied = True
        
        # Process event cycle updates (for duration-based events like Drought, Blizzard)
        # Only process once per food tax cycle when at least one tax was applied
        if tax_applied:
            try:
                from event_manager import EventManager
                event_mgr = EventManager(self.db)
                event_mgr.process_food_tax_cycle(game)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error processing event cycle for game {game_code}: {str(e)}")
        
        self.db.commit()
        return events
    
    def _apply_tax_to_team(
        self, 
        game: GameSession, 
        team_number: str, 
        tax_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply food tax to a specific team.
        
        Args:
            game: GameSession instance
            team_number: Team number (as string)
            tax_data: Tax tracking data for this team
            
        Returns:
            WebSocket event data
        """
        team_state = game.game_state['teams'][team_number]
        
        # Calculate tax amount (with School effect)
        tax_amount = self.calculate_food_tax_amount(team_state)
        
        # Apply tax using existing game logic
        success, message, new_state = GameLogic.apply_food_tax(team_state)
        
        # Update team state
        if success and new_state:
            game.game_state['teams'][team_number] = new_state
            flag_modified(game, 'game_state')
            
            # Track statistics
            if "FAMINE" in (message or ""):
                tax_data['total_famines'] += 1
            else:
                tax_data['total_taxes_paid'] += 1
            
            # Schedule next tax
            tax_interval = tax_data.get('tax_interval_minutes', 15)
            next_due = datetime.utcnow() + timedelta(minutes=tax_interval)
            tax_data['next_tax_due'] = next_due.isoformat()
            tax_data['last_tax_time'] = datetime.utcnow().isoformat()
            tax_data['warning_sent'] = False
            
            # Transfer food to bank if successful payment (not famine)
            if "FAMINE" not in (message or ""):
                bank_inventory = game.game_state.get('bank_inventory', {})
                bank_inventory['food'] = bank_inventory.get('food', 0) + tax_amount
                game.game_state['bank_inventory'] = bank_inventory
            
            flag_modified(game, 'game_state')
            
            # Determine event type
            is_famine = "FAMINE" in (message or "")
            event_type = "food_tax_famine" if is_famine else "food_tax_applied"
            
            return {
                "type": "event",
                "event_type": event_type,
                "data": {
                    "team_number": team_number,
                    "tax_amount": tax_amount,
                    "success": True,
                    "message": message,
                    "new_resources": new_state.get('resources', {}),
                    "next_tax_due": tax_data['next_tax_due'],
                    "is_famine": is_famine
                }
            }
        else:
            # Tax application failed (should be rare)
            return {
                "type": "event",
                "event_type": "food_tax_failed",
                "data": {
                    "team_number": team_number,
                    "success": False,
                    "message": message or "Failed to apply food tax"
                }
            }
    
    def get_tax_status(self, game_code: str) -> Dict[str, Any]:
        """
        Get current food tax status for all teams.
        
        Args:
            game_code: Game code
            
        Returns:
            Tax status for all teams
        """
        game = self.db.query(GameSession).filter(
            GameSession.game_code == game_code.upper()
        ).first()
        
        if not game:
            return {"success": False, "error": "Game not found"}
        
        if 'food_tax' not in game.game_state:
            return {"success": False, "error": "Food tax not initialized"}
        
        current_time = datetime.utcnow()
        team_statuses = {}
        
        for team_number, tax_data in game.game_state['food_tax'].items():
            next_due_str = tax_data.get('next_tax_due')
            
            if next_due_str:
                next_due = datetime.fromisoformat(next_due_str)
                time_until_due = (next_due - current_time).total_seconds() / 60
            else:
                time_until_due = None
            
            team_state = game.game_state['teams'].get(team_number, {})
            tax_amount = self.calculate_food_tax_amount(team_state)
            
            team_statuses[team_number] = {
                "next_tax_due": next_due_str,
                "minutes_until_due": round(time_until_due, 1) if time_until_due else None,
                "tax_amount": tax_amount,
                "tax_interval_minutes": tax_data.get('tax_interval_minutes'),
                "warning_sent": tax_data.get('warning_sent', False),
                "total_taxes_paid": tax_data.get('total_taxes_paid', 0),
                "total_famines": tax_data.get('total_famines', 0),
                "last_tax_time": tax_data.get('last_tax_time')
            }
        
        return {
            "success": True,
            "game_code": game_code.upper(),
            "game_status": game.status.value,
            "teams": team_statuses
        }
    
    def force_apply_tax(self, game_code: str, team_number: str) -> Dict[str, Any]:
        """
        Manually trigger food tax for a specific team (banker action).
        
        Args:
            game_code: Game code
            team_number: Team number (as string)
            
        Returns:
            Result of tax application
        """
        game = self.db.query(GameSession).filter(
            GameSession.game_code == game_code.upper()
        ).first()
        
        if not game:
            return {"success": False, "error": "Game not found"}
        
        if 'food_tax' not in game.game_state:
            return {"success": False, "error": "Food tax not initialized"}
        
        if team_number not in game.game_state['food_tax']:
            return {"success": False, "error": f"Team {team_number} not found"}
        
        tax_data = game.game_state['food_tax'][team_number]
        result = self._apply_tax_to_team(game, team_number, tax_data)
        
        self.db.commit()
        
        return {
            "success": True,
            "event": result
        }
    
    def force_apply_tax_all_teams(self, game_code: str) -> Dict[str, Any]:
        """
        Manually trigger food tax for ALL teams (host/banker action).
        
        This is used when the host or banker presses "Apply Food Tax (All Nations)" button.
        
        Args:
            game_code: Game code
            
        Returns:
            Dictionary with:
            - success (bool): Whether the operation succeeded
            - events (List[Dict]): List of tax application events for each team
            - teams_processed (int): Number of teams processed
            - error (str): Error message if success is False
        """
        game = self.db.query(GameSession).filter(
            GameSession.game_code == game_code.upper()
        ).first()
        
        if not game:
            return {"success": False, "error": "Game not found"}
        
        if 'food_tax' not in game.game_state:
            return {"success": False, "error": "Food tax not initialized"}
        
        events = []
        for team_number, tax_data in game.game_state['food_tax'].items():
            result = self._apply_tax_to_team(game, team_number, tax_data)
            events.append(result)
        
        self.db.commit()
        
        return {
            "success": True,
            "events": events,
            "teams_processed": len(events)
        }
