"""
Scenario Event Scheduler - Background task for automated scenario events

This module runs a background task that periodically checks all active games
with scenarios and processes automated events like Marshall Aid, Demand Shifts,
Piracy Tax, Bank Runs, and conditional triggers.
"""

import asyncio
import logging
import random
from typing import Dict, Set, List, Any
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from database import get_db
from models import GameSession, GameStatus
from scenarios import get_scenario, ScenarioType
from websocket_manager import manager as ws_manager

logger = logging.getLogger(__name__)

# Global state
scheduler_task = None
scheduler_running = False
SCHEDULER_CHECK_INTERVAL_SECONDS = 30  # Check every 30 seconds

# Track scenario event state per game
# game_code -> {event_name: {last_triggered: datetime, count: int}}
scenario_event_state: Dict[str, Dict[str, Any]] = {}


class ScenarioEventProcessor:
    """Processes automated scenario events for a game"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_elapsed_minutes(self, game: GameSession) -> float:
        """Calculate elapsed game time in minutes, accounting for pauses"""
        if not game.started_at:
            return 0.0
        
        elapsed = datetime.utcnow() - game.started_at
        elapsed_seconds = elapsed.total_seconds()
        
        # Subtract total paused time if tracked
        if game.game_state and 'total_paused_time_ms' in game.game_state:
            paused_ms = game.game_state['total_paused_time_ms']
            elapsed_seconds -= (paused_ms / 1000)
        
        return elapsed_seconds / 60.0
    
    def initialize_event_state(self, game_code: str):
        """Initialize event tracking for a game"""
        if game_code not in scenario_event_state:
            scenario_event_state[game_code] = {}
    
    async def process_periodic_events(self, game: GameSession) -> List[Dict[str, Any]]:
        """Process periodic events like Marshall Aid, Demand Shifts, Piracy Tax"""
        events = []
        
        if not game.scenario_id or not game.game_state or 'scenario' not in game.game_state:
            return events
        
        try:
            scenario = get_scenario(game.scenario_id)
        except ValueError:
            return events
        
        self.initialize_event_state(game.game_code)
        game_state = scenario_event_state[game.game_code]
        elapsed_minutes = self.get_elapsed_minutes(game)
        
        for rule in scenario.get('special_rules', []):
            implementation = rule.get('implementation')
            params = rule.get('parameters', {})
            
            # Phase 1.1: Automated Periodic Events
            if implementation == 'banker_event':
                event = await self._process_banker_event(
                    game, rule, params, game_state, elapsed_minutes
                )
                if event:
                    events.append(event)
            
            elif implementation == 'periodic_penalty':
                event = await self._process_periodic_penalty(
                    game, rule, params, game_state, elapsed_minutes
                )
                if event:
                    events.append(event)
            
            # Phase 2.1: Conditional Triggers
            elif implementation == 'penalty_trigger':
                event = await self._process_conditional_trigger(
                    game, rule, params, game_state
                )
                if event:
                    events.append(event)
            
            # Phase 1.3: Resource Events
            elif implementation == 'random_event':
                event = await self._process_random_event(
                    game, rule, params, game_state, elapsed_minutes
                )
                if event:
                    events.append(event)
        
        return events
    
    async def _process_banker_event(
        self, game: GameSession, rule: Dict, params: Dict,
        game_state: Dict, elapsed_minutes: float
    ) -> Dict[str, Any]:
        """Process banker events like Marshall Aid, Demand Shifts"""
        interval = params.get('interval_minutes', 20)
        event_name = rule['name']
        
        if event_name not in game_state:
            game_state[event_name] = {'last_triggered': 0, 'count': 0}
        
        event_state = game_state[event_name]
        time_since_last = elapsed_minutes - event_state['last_triggered']
        
        if time_since_last >= interval:
            event_state['last_triggered'] = elapsed_minutes
            event_state['count'] += 1
            
            # Marshall Aid - decreasing amounts
            if 'Marshall Aid' in event_name:
                amounts = params.get('amounts', [100, 75, 50, 25])
                count = event_state['count'] - 1
                
                if count < len(amounts):
                    amount = amounts[count]
                    
                    # Distribute to all teams
                    if 'teams' in game.game_state:
                        for team_key in game.game_state['teams']:
                            team = game.game_state['teams'][team_key]
                            if 'resources' in team and 'currency' in team['resources']:
                                team['resources']['currency'] += amount
                        
                        flag_modified(game, 'game_state')
                        self.db.commit()
                        
                        logger.info(f"Marshall Aid distributed: {amount} currency to all teams in {game.game_code}")
                        
                        return {
                            'type': 'event',
                            'event_type': 'scenario_periodic_event',
                            'scenario_event': 'marshall_aid',
                            'data': {
                                'message': f"🎁 Marshall Aid Round {count + 1}: All nations receive {amount} currency!",
                                'amount': amount,
                                'round': count + 1
                            }
                        }
            
            # Demand Shifts - announce doubled resource
            elif 'Demand Shift' in event_name:
                resources = ['food', 'raw_materials', 'electrical_goods', 'medical_goods']
                selected_resource = random.choice(resources)
                
                logger.info(f"Demand Shift in {game.game_code}: {selected_resource} value doubled")
                
                return {
                    'type': 'event',
                    'event_type': 'scenario_periodic_event',
                    'scenario_event': 'demand_shift',
                    'data': {
                        'message': f"📈 Demand Shift: {selected_resource.replace('_', ' ').title()} value is now 2× for trading!",
                        'resource': selected_resource,
                        'multiplier': 2
                    }
                }
        
        return None
    
    async def _process_periodic_penalty(
        self, game: GameSession, rule: Dict, params: Dict,
        game_state: Dict, elapsed_minutes: float
    ) -> Dict[str, Any]:
        """Process periodic penalties like Piracy Tax"""
        interval = params.get('interval_minutes', 15)
        event_name = rule['name']
        
        if event_name not in game_state:
            game_state[event_name] = {'last_triggered': 0, 'count': 0}
        
        event_state = game_state[event_name]
        time_since_last = elapsed_minutes - event_state['last_triggered']
        
        if time_since_last >= interval:
            event_state['last_triggered'] = elapsed_minutes
            event_state['count'] += 1
            
            # Piracy Tax - 5% resource loss
            if 'Piracy' in event_name:
                loss_percent = params.get('resource_loss_percent', 5)
                
                if 'teams' in game.game_state:
                    for team_key in game.game_state['teams']:
                        team = game.game_state['teams'][team_key]
                        if 'resources' in team:
                            for resource in ['food', 'raw_materials', 'electrical_goods', 'medical_goods']:
                                if resource in team['resources']:
                                    original = team['resources'][resource]
                                    loss = int(original * (loss_percent / 100))
                                    team['resources'][resource] = max(0, original - loss)
                    
                    flag_modified(game, 'game_state')
                    self.db.commit()
                    
                    logger.info(f"Piracy Tax applied: {loss_percent}% loss to all teams in {game.game_code}")
                    
                    return {
                        'type': 'event',
                        'event_type': 'scenario_periodic_event',
                        'scenario_event': 'piracy_tax',
                        'data': {
                            'message': f"🏴‍☠️ Piracy Attack: All nations lose {loss_percent}% of resources!",
                            'loss_percent': loss_percent
                        }
                    }
        
        return None
    
    async def _process_conditional_trigger(
        self, game: GameSession, rule: Dict, params: Dict,
        game_state: Dict
    ) -> Dict[str, Any]:
        """Process conditional triggers like Food Crisis, Worker Strikes"""
        event_name = rule['name']
        
        # Prevent spam - check if recently triggered
        if event_name in game_state:
            last_triggered = game_state[event_name].get('last_triggered', 0)
            elapsed = self.get_elapsed_minutes(game)
            if elapsed - last_triggered < 5:  # Cooldown of 5 minutes
                return None
        
        # Food Crisis - if any nation below threshold, all lose currency
        if 'Food Crisis' in event_name:
            threshold = params.get('food_threshold', 10)
            penalty_percent = params.get('currency_penalty_percent', 10)
            
            if 'teams' in game.game_state:
                trigger_crisis = False
                for team_key in game.game_state['teams']:
                    team = game.game_state['teams'][team_key]
                    if 'resources' in team and 'food' in team['resources']:
                        if team['resources']['food'] < threshold:
                            trigger_crisis = True
                            break
                
                if trigger_crisis:
                    # Apply penalty to all teams
                    for team_key in game.game_state['teams']:
                        team = game.game_state['teams'][team_key]
                        if 'resources' in team and 'currency' in team['resources']:
                            original = team['resources']['currency']
                            penalty = int(original * (penalty_percent / 100))
                            team['resources']['currency'] = max(0, original - penalty)
                    
                    flag_modified(game, 'game_state')
                    self.db.commit()
                    
                    if event_name not in game_state:
                        game_state[event_name] = {}
                    game_state[event_name]['last_triggered'] = self.get_elapsed_minutes(game)
                    
                    logger.info(f"Food Crisis triggered in {game.game_code}: {penalty_percent}% currency loss")
                    
                    return {
                        'type': 'event',
                        'event_type': 'scenario_conditional_event',
                        'scenario_event': 'food_crisis',
                        'data': {
                            'message': f"🚨 Food Crisis! A nation fell below {threshold} food. All nations lose {penalty_percent}% currency!",
                            'threshold': threshold,
                            'penalty_percent': penalty_percent
                        }
                    }
        
        # Worker Strikes - if medical goods below threshold
        elif 'Worker Strike' in event_name:
            threshold = params.get('medical_goods_threshold', 5)
            
            if 'teams' in game.game_state:
                for team_key in game.game_state['teams']:
                    team = game.game_state['teams'][team_key]
                    if 'resources' in team and 'medical_goods' in team['resources']:
                        if team['resources']['medical_goods'] < threshold:
                            # Track strike start time
                            if event_name not in game_state:
                                game_state[event_name] = {}
                            
                            if 'strike_teams' not in game_state[event_name]:
                                game_state[event_name]['strike_teams'] = {}
                            
                            team_name = team.get('name', f"Team {team_key}")
                            if team_key not in game_state[event_name]['strike_teams']:
                                game_state[event_name]['strike_teams'][team_key] = self.get_elapsed_minutes(game)
                                
                                logger.info(f"Worker Strike triggered for {team_name} in {game.game_code}")
                                
                                return {
                                    'type': 'event',
                                    'event_type': 'scenario_conditional_event',
                                    'scenario_event': 'worker_strike',
                                    'data': {
                                        'message': f"⚠️ Worker Strike in {team_name}! Medical goods below {threshold}. Factories halted for 5 minutes!",
                                        'team': team_key,
                                        'team_name': team_name,
                                        'threshold': threshold
                                    }
                                }
        
        # Bank Runs - check currency requirement
        elif 'Bank Run' in event_name:
            interval = params.get('interval_minutes', 20)
            requirement = params.get('currency_requirement', 100)
            
            if event_name not in game_state:
                game_state[event_name] = {'last_triggered': 0}
            
            elapsed = self.get_elapsed_minutes(game)
            time_since_last = elapsed - game_state[event_name]['last_triggered']
            
            if time_since_last >= interval:
                game_state[event_name]['last_triggered'] = elapsed
                
                if 'teams' in game.game_state:
                    affected_teams = []
                    for team_key in game.game_state['teams']:
                        team = game.game_state['teams'][team_key]
                        if 'resources' in team and 'currency' in team['resources']:
                            if team['resources']['currency'] < requirement:
                                # Remove a building (simplified - remove first available)
                                if 'buildings' in team:
                                    for building_type, count in team['buildings'].items():
                                        if count > 0:
                                            team['buildings'][building_type] -= 1
                                            team_name = team.get('name', f"Team {team_key}")
                                            affected_teams.append(team_name)
                                            break
                    
                    if affected_teams:
                        flag_modified(game, 'game_state')
                        self.db.commit()
                        
                        logger.info(f"Bank Run in {game.game_code}: {len(affected_teams)} teams lost buildings")
                        
                        return {
                            'type': 'event',
                            'event_type': 'scenario_conditional_event',
                            'scenario_event': 'bank_run',
                            'data': {
                                'message': f"🏦 Bank Run! Nations with less than {requirement} currency lose 1 building: {', '.join(affected_teams)}",
                                'requirement': requirement,
                                'affected_teams': affected_teams
                            }
                        }
        
        return None
    
    async def _process_random_event(
        self, game: GameSession, rule: Dict, params: Dict,
        game_state: Dict, elapsed_minutes: float
    ) -> Dict[str, Any]:
        """Process random events like Bandit Raids"""
        event_name = rule['name']
        
        if event_name not in game_state:
            game_state[event_name] = {'last_triggered': 0}
        
        # Random chance every check (about 5% chance per 30-second check = ~10% per minute)
        if random.random() < 0.05:
            time_since_last = elapsed_minutes - game_state[event_name]['last_triggered']
            
            # Minimum 10 minutes between bandit raids
            if time_since_last >= 10:
                game_state[event_name]['last_triggered'] = elapsed_minutes
                
                # Bandit Raids - random team loses resources
                if 'Bandit' in event_name:
                    loss_percent = params.get('resource_loss_percent', 10)
                    
                    if 'teams' in game.game_state:
                        # Pick random team
                        team_keys = list(game.game_state['teams'].keys())
                        if team_keys:
                            target_team = random.choice(team_keys)
                            team = game.game_state['teams'][target_team]
                            
                            if 'resources' in team:
                                losses = {}
                                for resource in ['food', 'raw_materials', 'electrical_goods', 'medical_goods']:
                                    if resource in team['resources']:
                                        original = team['resources'][resource]
                                        loss = int(original * (loss_percent / 100))
                                        team['resources'][resource] = max(0, original - loss)
                                        losses[resource] = loss
                                
                                flag_modified(game, 'game_state')
                                self.db.commit()
                                
                                team_name = team.get('name', f"Team {target_team}")
                                logger.info(f"Bandit Raid in {game.game_code}: {team_name} lost {loss_percent}%")
                                
                                return {
                                    'type': 'event',
                                    'event_type': 'scenario_random_event',
                                    'scenario_event': 'bandit_raid',
                                    'data': {
                                        'message': f"🗡️ Bandit Raid! {team_name} caravan attacked, lost {loss_percent}% of resources!",
                                        'team': target_team,
                                        'team_name': team_name,
                                        'loss_percent': loss_percent,
                                        'losses': losses
                                    }
                                }
        
        return None


async def check_all_games_for_scenario_events():
    """
    Check all active games for scenario events.
    
    This runs periodically and processes all games with scenarios
    that are currently in progress.
    """
    db = next(get_db())
    
    try:
        # Get all active games with scenarios
        games = db.query(GameSession).filter(
            GameSession.status == GameStatus.IN_PROGRESS,
            GameSession.scenario_id.isnot(None)
        ).all()
        
        for game in games:
            try:
                processor = ScenarioEventProcessor(db)
                events = await processor.process_periodic_events(game)
                
                # Broadcast events via WebSocket
                for event in events:
                    await ws_manager.broadcast_to_game(
                        game.game_code.upper(),
                        event
                    )
                    
                    logger.info(
                        f"Scenario event for game {game.game_code}: {event.get('scenario_event')}"
                    )
            
            except Exception as e:
                logger.error(
                    f"Error processing scenario events for game {game.game_code}: {str(e)}",
                    exc_info=True
                )
    
    except Exception as e:
        logger.error(f"Error in check_all_games_for_scenario_events: {str(e)}", exc_info=True)
    
    finally:
        db.close()


async def scenario_event_scheduler():
    """
    Background scheduler task that runs continuously.
    
    Checks all active games every 30 seconds for scenario event processing.
    """
    global scheduler_running
    scheduler_running = True
    
    logger.info("Scenario event scheduler started")
    
    try:
        while scheduler_running:
            await check_all_games_for_scenario_events()
            await asyncio.sleep(SCHEDULER_CHECK_INTERVAL_SECONDS)
    
    except asyncio.CancelledError:
        logger.info("Scenario event scheduler cancelled")
        raise
    
    except Exception as e:
        logger.error(f"Error in scenario_event_scheduler: {str(e)}", exc_info=True)
    
    finally:
        scheduler_running = False
        logger.info("Scenario event scheduler stopped")


def start_scenario_event_scheduler():
    """Start the scenario event scheduler background task"""
    global scheduler_task, scheduler_running
    
    if scheduler_task is None or scheduler_task.done():
        scheduler_task = asyncio.create_task(scenario_event_scheduler())
        logger.info("Scenario event scheduler task created")
    else:
        logger.warning("Scenario event scheduler already running")


def stop_scenario_event_scheduler():
    """Stop the scenario event scheduler background task"""
    global scheduler_task, scheduler_running
    
    scheduler_running = False
    
    if scheduler_task and not scheduler_task.done():
        scheduler_task.cancel()
        logger.info("Scenario event scheduler stop requested")


async def on_game_started(game_code: str):
    """Called when a game starts - initialize scenario event tracking"""
    db = next(get_db())
    
    try:
        game = db.query(GameSession).filter(
            GameSession.game_code == game_code.upper()
        ).first()
        
        if game and game.scenario_id:
            scenario_event_state[game_code.upper()] = {}
            logger.info(f"Scenario event tracking initialized for game {game_code}")
    
    except Exception as e:
        logger.error(f"Error initializing scenario events for game {game_code}: {str(e)}")
    
    finally:
        db.close()


async def on_game_ended(game_code: str):
    """Called when a game ends - cleanup tracking"""
    if game_code.upper() in scenario_event_state:
        del scenario_event_state[game_code.upper()]
    logger.info(f"Game {game_code} ended - removed from scenario event monitoring")
