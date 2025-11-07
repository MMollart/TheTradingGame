"""
Event Manager - Business logic for game events (disasters, economic events, etc.)

This module handles:
- Event triggering and lifecycle management
- Difficulty scaling and severity calculations
- Mitigation mechanics (infrastructure, hospitals, restaurants)
- Duration tracking via food tax cycles
- Resource and building modifications
"""

import logging
import random
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from models import GameSession, GameEventInstance, EventType, EventCategory, EventStatus
from game_constants import GameDifficulty, DIFFICULTY_MODIFIERS

logger = logging.getLogger(__name__)


class EventManager:
    """Manages game events and their effects"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_difficulty_modifier(self, game: GameSession) -> float:
        """Get difficulty modifier for a game"""
        difficulty = game.difficulty or "medium"
        if difficulty == "easy":
            return 0.75
        elif difficulty == "hard":
            return 1.5
        return 1.0
    
    def get_mitigation_multiplier(self, team: Dict, building_type: str) -> float:
        """
        Calculate mitigation multiplier based on buildings.
        
        Args:
            team: Team dictionary with buildings
            building_type: Type of mitigation building (infrastructure, hospital, restaurant)
        
        Returns:
            Multiplier between 0.0 and 1.0 (1.0 = no mitigation, 0.0 = full mitigation)
        """
        buildings = team.get('buildings', {})
        count = buildings.get(building_type, 0)
        
        # Each building reduces impact by 20%, max 5 buildings = 100% reduction
        reduction = min(count * 0.2, 1.0)
        return 1.0 - reduction
    
    def calculate_final_effect(self, base_effect: float, severity: int, 
                              difficulty_modifier: float,
                              mitigation_multiplier: float = 1.0) -> float:
        """
        Calculate final event effect.
        
        Formula: Final Effect = Base Effect × Severity × Difficulty Modifier × Mitigation
        """
        return base_effect * severity * difficulty_modifier * mitigation_multiplier
    
    # ==================== Natural Disasters ====================
    
    def trigger_earthquake(self, game: GameSession, severity: int = 3) -> GameEventInstance:
        """
        Trigger earthquake event - destroys random buildings.
        
        Impact: Destroys buildings = (Severity × Difficulty Modifier), max 5 per team
        Mitigation: Infrastructure buildings reduce destruction by 20% each
        """
        difficulty_mod = self.get_difficulty_modifier(game)
        
        # Calculate base buildings destroyed per team
        base_destroyed = severity * difficulty_mod
        max_destroyed = 5  # Hard cap
        
        affected_teams = []
        total_destroyed = 0
        
        if 'teams' in game.game_state:
            for team_key, team in game.game_state['teams'].items():
                # Calculate mitigation
                mitigation = self.get_mitigation_multiplier(team, 'infrastructure')
                buildings_to_destroy = int(base_destroyed * mitigation)
                buildings_to_destroy = min(buildings_to_destroy, max_destroyed)
                
                if buildings_to_destroy > 0:
                    destroyed = self._destroy_random_buildings(team, buildings_to_destroy)
                    if destroyed > 0:
                        affected_teams.append({
                            'team': team_key,
                            'team_name': team.get('name', f"Team {team_key}"),
                            'buildings_destroyed': destroyed
                        })
                        total_destroyed += destroyed
            
            flag_modified(game, 'game_state')
            self.db.commit()
        
        # Create event instance
        event = GameEventInstance(
            game_session_id=game.id,
            event_type=EventType.EARTHQUAKE,
            event_category=EventCategory.NATURAL_DISASTER,
            severity=severity,
            status=EventStatus.EXPIRED,  # Instant event
            duration_cycles=0,
            event_data={
                'affected_teams': affected_teams,
                'total_buildings_destroyed': total_destroyed,
                'difficulty_modifier': difficulty_mod
            }
        )
        self.db.add(event)
        self.db.commit()
        
        logger.info(f"Earthquake triggered in {game.game_code}: {total_destroyed} buildings destroyed")
        return event
    
    def trigger_fire(self, game: GameSession, severity: int = 3) -> GameEventInstance:
        """
        Trigger fire event - destroys electrical factories.
        
        Impact: Destroys 20% × Severity × Difficulty of electrical factories per team
        Mitigation: Hospital buildings reduce destruction by 20% each
        """
        difficulty_mod = self.get_difficulty_modifier(game)
        base_destruction_rate = 0.20  # 20%
        
        affected_teams = []
        total_destroyed = 0
        
        if 'teams' in game.game_state:
            for team_key, team in game.game_state['teams'].items():
                buildings = team.get('buildings', {})
                electrical_factories = buildings.get('electrical_factory', 0)
                
                if electrical_factories > 0:
                    # Calculate destruction with mitigation
                    mitigation = self.get_mitigation_multiplier(team, 'hospital')
                    destruction_rate = base_destruction_rate * severity * difficulty_mod * mitigation
                    destruction_rate = min(destruction_rate, 1.0)  # Cap at 100%
                    
                    factories_destroyed = int(electrical_factories * destruction_rate)
                    
                    if factories_destroyed > 0:
                        buildings['electrical_factory'] = electrical_factories - factories_destroyed
                        affected_teams.append({
                            'team': team_key,
                            'team_name': team.get('name', f"Team {team_key}"),
                            'factories_destroyed': factories_destroyed,
                            'factories_remaining': buildings['electrical_factory']
                        })
                        total_destroyed += factories_destroyed
            
            if total_destroyed > 0:
                flag_modified(game, 'game_state')
                self.db.commit()
        
        # Create event instance
        event = GameEventInstance(
            game_session_id=game.id,
            event_type=EventType.FIRE,
            event_category=EventCategory.NATURAL_DISASTER,
            severity=severity,
            status=EventStatus.EXPIRED,
            duration_cycles=0,
            event_data={
                'affected_teams': affected_teams,
                'total_factories_destroyed': total_destroyed,
                'difficulty_modifier': difficulty_mod
            }
        )
        self.db.add(event)
        self.db.commit()
        
        logger.info(f"Fire triggered in {game.game_code}: {total_destroyed} electrical factories destroyed")
        return event
    
    def trigger_drought(self, game: GameSession, severity: int = 3) -> GameEventInstance:
        """
        Trigger drought event - reduces farm and mine production.
        
        Impact: 50% production reduction, adjusted by severity (±10% per severity level from 3)
        Duration: 2 food tax cycles
        Mitigation: Infrastructure buildings reduce impact by 20% each
        """
        difficulty_mod = self.get_difficulty_modifier(game)
        
        # Production modifier calculation
        # Severity 1-2: Less severe (60% production)
        # Severity 3: Standard (50% production)
        # Severity 4-5: More severe (40-30% production)
        base_modifier = 0.5 + (3 - severity) * 0.1
        
        # Store drought modifiers in game state
        if 'active_events' not in game.game_state:
            game.game_state['active_events'] = {}
        
        game.game_state['active_events']['drought'] = {
            'production_modifier': base_modifier,
            'severity': severity,
            'cycles_remaining': 2,
            'difficulty_modifier': difficulty_mod
        }
        
        flag_modified(game, 'game_state')
        self.db.commit()
        
        # Create event instance
        event = GameEventInstance(
            game_session_id=game.id,
            event_type=EventType.DROUGHT,
            event_category=EventCategory.NATURAL_DISASTER,
            severity=severity,
            status=EventStatus.ACTIVE,
            duration_cycles=2,
            cycles_remaining=2,
            event_data={
                'production_modifier': base_modifier,
                'affects_buildings': ['farm', 'mine'],
                'difficulty_modifier': difficulty_mod
            }
        )
        self.db.add(event)
        self.db.commit()
        
        logger.info(f"Drought triggered in {game.game_code}: {base_modifier*100}% production for 2 cycles")
        return event
    
    def trigger_plague(self, game: GameSession, severity: int = 3) -> GameEventInstance:
        """
        Trigger plague event - contagious, reduces all production.
        
        Impact: 30% × Severity × Difficulty production penalty
        Duration: Until cured (teams pay medicine to bank)
        Mitigation: Hospital buildings reduce penalty by 20% each
        Contagion: Spreads during trades, infected teams can't trade with non-infected
        """
        difficulty_mod = self.get_difficulty_modifier(game)
        base_penalty = 0.30
        
        # Calculate cure cost
        cure_cost = int(5 * difficulty_mod)
        
        # Randomly infect 1-2 teams based on severity
        initial_infected = 1 if severity <= 3 else 2
        
        if 'teams' not in game.game_state:
            game.game_state['teams'] = {}
        
        team_keys = list(game.game_state['teams'].keys())
        if len(team_keys) > 0:
            infected_teams = random.sample(team_keys, min(initial_infected, len(team_keys)))
            
            # Store plague state
            if 'active_events' not in game.game_state:
                game.game_state['active_events'] = {}
            
            game.game_state['active_events']['plague'] = {
                'infected_teams': infected_teams,
                'base_penalty': base_penalty,
                'severity': severity,
                'cure_cost': cure_cost,
                'difficulty_modifier': difficulty_mod
            }
            
            flag_modified(game, 'game_state')
            self.db.commit()
            
            # Create event instance
            event = GameEventInstance(
                game_session_id=game.id,
                event_type=EventType.PLAGUE,
                event_category=EventCategory.NATURAL_DISASTER,
                severity=severity,
                status=EventStatus.ACTIVE,
                duration_cycles=None,  # Until cured
                event_data={
                    'infected_teams': infected_teams,
                    'base_penalty': base_penalty,
                    'cure_cost': cure_cost,
                    'difficulty_modifier': difficulty_mod
                }
            )
            self.db.add(event)
            self.db.commit()
            
            logger.info(f"Plague triggered in {game.game_code}: {len(infected_teams)} teams infected")
            return event
        
        return None
    
    def cure_plague(self, game: GameSession, team_number: str) -> bool:
        """
        Cure plague for a specific team by paying medicine to bank.
        
        Returns True if successfully cured, False otherwise.
        """
        if 'active_events' not in game.game_state or 'plague' not in game.game_state['active_events']:
            return False
        
        plague_data = game.game_state['active_events']['plague']
        infected_teams = plague_data.get('infected_teams', [])
        
        if team_number in infected_teams:
            infected_teams.remove(team_number)
            
            # If no more infected teams, end plague event
            if len(infected_teams) == 0:
                del game.game_state['active_events']['plague']
                
                # Update event instance status
                event = self.db.query(GameEventInstance).filter(
                    GameEventInstance.game_session_id == game.id,
                    GameEventInstance.event_type == EventType.PLAGUE,
                    GameEventInstance.status == EventStatus.ACTIVE
                ).first()
                
                if event:
                    event.status = EventStatus.CURED
            
            flag_modified(game, 'game_state')
            self.db.commit()
            
            logger.info(f"Plague cured for team {team_number} in {game.game_code}")
            return True
        
        return False
    
    def trigger_blizzard(self, game: GameSession, severity: int = 3) -> GameEventInstance:
        """
        Trigger blizzard event - increases food tax and decreases production.
        
        Impact:
        - Food tax multiplied by (2 × Severity × Difficulty)
        - Production decreased by 10% (easy), 20% (normal), 30% (hard)
        Duration: 2 food tax cycles
        Mitigation: Restaurants provide currency rebate, Infrastructure reduces production penalty
        """
        difficulty_mod = self.get_difficulty_modifier(game)
        
        # Food tax multiplier
        food_tax_multiplier = 2.0 * severity * difficulty_mod
        
        # Production penalty by difficulty
        production_penalties = {
            "easy": 0.10,
            "normal": 0.20,
            "hard": 0.30
        }
        difficulty_key = game.difficulty or "normal"
        production_penalty = production_penalties.get(difficulty_key, 0.20)
        
        # Store blizzard state
        if 'active_events' not in game.game_state:
            game.game_state['active_events'] = {}
        
        game.game_state['active_events']['blizzard'] = {
            'food_tax_multiplier': food_tax_multiplier,
            'production_penalty': production_penalty,
            'severity': severity,
            'cycles_remaining': 2,
            'difficulty_modifier': difficulty_mod
        }
        
        flag_modified(game, 'game_state')
        self.db.commit()
        
        # Create event instance
        event = GameEventInstance(
            game_session_id=game.id,
            event_type=EventType.BLIZZARD,
            event_category=EventCategory.NATURAL_DISASTER,
            severity=severity,
            status=EventStatus.ACTIVE,
            duration_cycles=2,
            cycles_remaining=2,
            event_data={
                'food_tax_multiplier': food_tax_multiplier,
                'production_penalty': production_penalty,
                'difficulty_modifier': difficulty_mod
            }
        )
        self.db.add(event)
        self.db.commit()
        
        logger.info(f"Blizzard triggered in {game.game_code}: {food_tax_multiplier}x food tax, {production_penalty*100}% production penalty")
        return event
    
    def trigger_tornado(self, game: GameSession, severity: int = 3) -> GameEventInstance:
        """
        Trigger tornado event - destroys percentage of all resources.
        
        Impact: Removes 15% × Severity × Difficulty of ALL resources from each team
        Mitigation: Infrastructure buildings reduce loss by 20% each
        """
        difficulty_mod = self.get_difficulty_modifier(game)
        base_loss_rate = 0.15
        
        affected_teams = []
        
        if 'teams' in game.game_state:
            for team_key, team in game.game_state['teams'].items():
                resources = team.get('resources', {})
                
                # Calculate loss rate with mitigation
                mitigation = self.get_mitigation_multiplier(team, 'infrastructure')
                loss_rate = base_loss_rate * severity * difficulty_mod * mitigation
                loss_rate = min(loss_rate, 1.0)  # Cap at 100%
                
                losses = {}
                for resource_type in ['food', 'currency', 'raw_materials', 'electrical_goods', 'medical_goods']:
                    if resource_type in resources:
                        original = resources[resource_type]
                        loss = int(original * loss_rate)
                        resources[resource_type] = max(0, original - loss)
                        losses[resource_type] = loss
                
                total_loss = sum(losses.values())
                if total_loss > 0:
                    affected_teams.append({
                        'team': team_key,
                        'team_name': team.get('name', f"Team {team_key}"),
                        'losses': losses
                    })
            
            if len(affected_teams) > 0:
                flag_modified(game, 'game_state')
                self.db.commit()
        
        # Create event instance
        event = GameEventInstance(
            game_session_id=game.id,
            event_type=EventType.TORNADO,
            event_category=EventCategory.NATURAL_DISASTER,
            severity=severity,
            status=EventStatus.EXPIRED,
            duration_cycles=0,
            event_data={
                'affected_teams': affected_teams,
                'loss_rate': loss_rate,
                'difficulty_modifier': difficulty_mod
            }
        )
        self.db.add(event)
        self.db.commit()
        
        logger.info(f"Tornado triggered in {game.game_code}: {loss_rate*100}% resource loss for {len(affected_teams)} teams")
        return event
    
    # ==================== Economic Events ====================
    
    def trigger_economic_recession(self, game: GameSession, severity: int = 3) -> GameEventInstance:
        """
        Trigger economic recession - increases bank prices and building costs.
        
        Impact:
        - Bank prices increase by 50% × Severity × Difficulty
        - Building costs increase by 25% × Severity × Difficulty
        Duration: 2 + (Severity - 3) food tax cycles
        Mitigation: Infrastructure reduces price increases, Restaurants provide bonus currency
        """
        difficulty_mod = self.get_difficulty_modifier(game)
        
        # Calculate multipliers
        bank_price_increase = 0.50 * severity * difficulty_mod
        building_cost_increase = 0.25 * severity * difficulty_mod
        
        # Duration calculation
        duration_cycles = max(0, 2 + (severity - 3))
        if duration_cycles == 0:
            duration_cycles = 1  # Minimum 1 cycle
        
        # Store recession state
        if 'active_events' not in game.game_state:
            game.game_state['active_events'] = {}
        
        game.game_state['active_events']['recession'] = {
            'bank_price_multiplier': 1.0 + bank_price_increase,
            'building_cost_multiplier': 1.0 + building_cost_increase,
            'severity': severity,
            'cycles_remaining': duration_cycles,
            'difficulty_modifier': difficulty_mod,
            'restaurant_bonus_per_cycle': int(50 * severity * difficulty_mod)
        }
        
        flag_modified(game, 'game_state')
        self.db.commit()
        
        # Create event instance
        event = GameEventInstance(
            game_session_id=game.id,
            event_type=EventType.ECONOMIC_RECESSION,
            event_category=EventCategory.ECONOMIC_EVENT,
            severity=severity,
            status=EventStatus.ACTIVE,
            duration_cycles=duration_cycles,
            cycles_remaining=duration_cycles,
            event_data={
                'bank_price_multiplier': 1.0 + bank_price_increase,
                'building_cost_multiplier': 1.0 + building_cost_increase,
                'duration_cycles': duration_cycles,
                'difficulty_modifier': difficulty_mod
            }
        )
        self.db.add(event)
        self.db.commit()
        
        logger.info(f"Economic recession triggered in {game.game_code}: {(1.0+bank_price_increase)*100}% bank prices for {duration_cycles} cycles")
        return event
    
    # ==================== Positive Events ====================
    
    def trigger_automation_breakthrough(self, game: GameSession, severity: int = 3, 
                                       target_team: Optional[str] = None) -> GameEventInstance:
        """
        Trigger automation breakthrough - increases factory production.
        
        Impact: All factories produce +50% × Severity × Difficulty for 2 cycles
        Requirement: Must pay 30 × Difficulty electrical goods to bank
        Selection: Random team or team with most factories
        """
        difficulty_mod = self.get_difficulty_modifier(game)
        
        # Calculate requirements and bonuses
        electrical_goods_required = int(30 * difficulty_mod)
        production_bonus = 0.50 * severity * difficulty_mod
        
        # Select target team if not specified
        if not target_team and 'teams' in game.game_state:
            # Option: Team with most factories
            max_factories = 0
            selected_team = None
            
            for team_key, team in game.game_state['teams'].items():
                buildings = team.get('buildings', {})
                factory_count = buildings.get('electrical_factory', 0) + buildings.get('medical_factory', 0)
                if factory_count > max_factories:
                    max_factories = factory_count
                    selected_team = team_key
            
            target_team = selected_team or random.choice(list(game.game_state['teams'].keys()))
        
        # Store automation breakthrough state (pending payment)
        if 'active_events' not in game.game_state:
            game.game_state['active_events'] = {}
        
        game.game_state['active_events']['automation_breakthrough'] = {
            'target_team': target_team,
            'production_bonus': production_bonus,
            'electrical_goods_required': electrical_goods_required,
            'severity': severity,
            'difficulty_modifier': difficulty_mod,
            'payment_pending': True,
            'cycles_remaining_for_payment': 1  # Must pay within 1 tax cycle
        }
        
        flag_modified(game, 'game_state')
        self.db.commit()
        
        # Create event instance
        event = GameEventInstance(
            game_session_id=game.id,
            event_type=EventType.AUTOMATION_BREAKTHROUGH,
            event_category=EventCategory.POSITIVE_EVENT,
            severity=severity,
            status=EventStatus.ACTIVE,
            duration_cycles=2,
            cycles_remaining=2,
            event_data={
                'target_team': target_team,
                'production_bonus': production_bonus,
                'electrical_goods_required': electrical_goods_required,
                'payment_pending': True,
                'difficulty_modifier': difficulty_mod
            }
        )
        self.db.add(event)
        self.db.commit()
        
        logger.info(f"Automation breakthrough offered to team {target_team} in {game.game_code}")
        return event
    
    def complete_automation_breakthrough(self, game: GameSession, team_number: str) -> bool:
        """
        Complete automation breakthrough payment and activate bonus.
        
        Returns True if payment accepted and bonus activated.
        """
        if 'active_events' not in game.game_state or 'automation_breakthrough' not in game.game_state['active_events']:
            return False
        
        breakthrough_data = game.game_state['active_events']['automation_breakthrough']
        
        if breakthrough_data.get('target_team') != team_number:
            return False
        
        if not breakthrough_data.get('payment_pending'):
            return False
        
        # Activate the bonus
        breakthrough_data['payment_pending'] = False
        breakthrough_data['cycles_remaining'] = 2  # Bonus lasts 2 cycles
        breakthrough_data['active'] = True
        
        flag_modified(game, 'game_state')
        self.db.commit()
        
        logger.info(f"Automation breakthrough activated for team {team_number} in {game.game_code}")
        return True
    
    # ==================== Event Lifecycle ====================
    
    def process_food_tax_cycle(self, game: GameSession):
        """
        Process event updates when food tax cycle occurs.
        
        Decrements cycle counters and expires events as needed.
        """
        if 'active_events' not in game.game_state:
            return
        
        active_events = game.game_state['active_events']
        events_to_remove = []
        modified = False
        
        for event_name, event_data in active_events.items():
            if 'cycles_remaining' in event_data:
                event_data['cycles_remaining'] -= 1
                modified = True
                
                if event_data['cycles_remaining'] <= 0:
                    events_to_remove.append(event_name)
                    
                    # Update database event instance
                    event_type_map = {
                        'drought': EventType.DROUGHT,
                        'blizzard': EventType.BLIZZARD,
                        'recession': EventType.ECONOMIC_RECESSION,
                        'automation_breakthrough': EventType.AUTOMATION_BREAKTHROUGH
                    }
                    
                    if event_name in event_type_map:
                        event_instance = self.db.query(GameEventInstance).filter(
                            GameEventInstance.game_session_id == game.id,
                            GameEventInstance.event_type == event_type_map[event_name],
                            GameEventInstance.status == EventStatus.ACTIVE
                        ).first()
                        
                        if event_instance:
                            event_instance.status = EventStatus.EXPIRED
                            event_instance.cycles_remaining = 0
        
        # Remove expired events
        for event_name in events_to_remove:
            del active_events[event_name]
            logger.info(f"Event {event_name} expired in {game.game_code}")
        
        # Commit changes if anything was modified
        if modified or events_to_remove:
            flag_modified(game, 'game_state')
            self.db.commit()
    
    def get_active_events(self, game: GameSession) -> List[Dict[str, Any]]:
        """Get list of all active events for a game"""
        events = self.db.query(GameEventInstance).filter(
            GameEventInstance.game_session_id == game.id,
            GameEventInstance.status == EventStatus.ACTIVE
        ).all()
        
        return [
            {
                'id': event.id,
                'type': event.event_type.value,
                'category': event.event_category.value,
                'severity': event.severity,
                'triggered_at': event.triggered_at.isoformat(),
                'cycles_remaining': event.cycles_remaining,
                'event_data': event.event_data
            }
            for event in events
        ]
    
    # ==================== Helper Methods ====================
    
    def _destroy_random_buildings(self, team: Dict, count: int) -> int:
        """
        Destroy random buildings from a team.
        
        Returns: Number of buildings actually destroyed
        """
        buildings = team.get('buildings', {})
        
        # Get list of all available buildings
        available_buildings = []
        for building_type, building_count in buildings.items():
            for _ in range(building_count):
                available_buildings.append(building_type)
        
        # Randomly select buildings to destroy
        destroyed_count = min(count, len(available_buildings))
        if destroyed_count > 0:
            destroyed_buildings = random.sample(available_buildings, destroyed_count)
            
            for building_type in destroyed_buildings:
                buildings[building_type] = max(0, buildings[building_type] - 1)
        
        return destroyed_count
