"""
Food Tax Scheduler - Background task for automated tax collection

This module runs a background task that periodically checks all active games
and processes food tax warnings and collections.
"""

import asyncio
import logging
from typing import Dict, Set
from datetime import datetime

from sqlalchemy.orm import Session
from database import get_db
from models import GameSession, GameStatus
from food_tax_manager import FoodTaxManager
from websocket_manager import manager as ws_manager

logger = logging.getLogger(__name__)

# Global state for active game monitoring
active_games: Set[str] = set()
scheduler_task = None
scheduler_running = False

# Track consecutive failures per game
game_failure_counts: Dict[str, int] = {}
MAX_CONSECUTIVE_FAILURES = 5


async def check_all_games_for_taxes():
    """
    Check all active games for food tax warnings and applications.
    
    This runs periodically (every 30 seconds) and processes all games
    that are currently in progress.
    """
    db = next(get_db())
    
    try:
        # Expire all objects to ensure we get fresh data from database
        # This prevents stale data issues when game status changes in other sessions
        db.expire_all()
        
        # Get all active games
        games = db.query(GameSession).filter(
            GameSession.status == GameStatus.IN_PROGRESS
        ).all()
        
        # Filter out games older than 12 hours (likely abandoned)
        current_time = datetime.utcnow()
        MAX_GAME_AGE_HOURS = 12
        
        for game in games:
            try:
                # Skip games older than MAX_GAME_AGE_HOURS
                if game.created_at:
                    game_age_hours = (current_time - game.created_at).total_seconds() / 3600
                    if game_age_hours > MAX_GAME_AGE_HOURS:
                        logger.warning(
                            f"Skipping old game {game.game_code} (age: {game_age_hours:.1f}h). "
                            f"Consider ending this game manually."
                        )
                        continue
                
                # Skip games with too many consecutive failures
                failure_count = game_failure_counts.get(game.game_code, 0)
                if failure_count >= MAX_CONSECUTIVE_FAILURES:
                    logger.warning(
                        f"Skipping game {game.game_code} after {failure_count} consecutive failures. "
                        f"Manual intervention required."
                    )
                    continue
                
                # Check and process taxes for this game
                tax_manager = FoodTaxManager(db)
                events = tax_manager.check_and_process_taxes(game.game_code)
                
                # Track if any failures occurred
                has_failure = any(event.get('event_type') == 'food_tax_failed' for event in events)
                
                if has_failure:
                    # Increment failure count
                    game_failure_counts[game.game_code] = failure_count + 1
                    logger.warning(
                        f"Game {game.game_code} food tax failed "
                        f"({game_failure_counts[game.game_code]}/{MAX_CONSECUTIVE_FAILURES})"
                    )
                else:
                    # Reset failure count on success
                    if game.game_code in game_failure_counts:
                        del game_failure_counts[game.game_code]
                
                # Broadcast any events via WebSocket
                for event in events:
                    await ws_manager.broadcast_to_game(
                        game.game_code.upper(),
                        event
                    )
                    
                    logger.info(
                        f"Food tax event for game {game.game_code}: {event.get('event_type')}"
                    )
            
            except Exception as e:
                # Increment failure count on exception
                game_failure_counts[game.game_code] = game_failure_counts.get(game.game_code, 0) + 1
                logger.error(
                    f"Error processing food tax for game {game.game_code} "
                    f"({game_failure_counts[game.game_code]}/{MAX_CONSECUTIVE_FAILURES}): {str(e)}",
                    exc_info=True
                )
    
    except Exception as e:
        logger.error(f"Error in check_all_games_for_taxes: {str(e)}", exc_info=True)
    
    finally:
        db.close()


async def food_tax_scheduler():
    """
    Background scheduler task that runs continuously.
    
    Checks all active games every 30 seconds for food tax processing.
    """
    global scheduler_running
    scheduler_running = True
    
    logger.info("Food tax scheduler started")
    
    try:
        while scheduler_running:
            await check_all_games_for_taxes()
            
            # Wait before next check (configurable interval)
            from food_tax_manager import SCHEDULER_CHECK_INTERVAL_SECONDS
            await asyncio.sleep(SCHEDULER_CHECK_INTERVAL_SECONDS)
    
    except asyncio.CancelledError:
        logger.info("Food tax scheduler cancelled")
        raise
    
    except Exception as e:
        logger.error(f"Error in food_tax_scheduler: {str(e)}", exc_info=True)
    
    finally:
        scheduler_running = False
        logger.info("Food tax scheduler stopped")


def start_food_tax_scheduler():
    """
    Start the food tax scheduler background task.
    
    This should be called when the application starts.
    """
    global scheduler_task, scheduler_running
    
    if scheduler_task is None or scheduler_task.done():
        scheduler_task = asyncio.create_task(food_tax_scheduler())
        logger.info("Food tax scheduler task created")
    else:
        logger.warning("Food tax scheduler already running")


def stop_food_tax_scheduler():
    """
    Stop the food tax scheduler background task.
    
    This should be called when the application shuts down.
    """
    global scheduler_task, scheduler_running
    
    scheduler_running = False
    
    if scheduler_task and not scheduler_task.done():
        scheduler_task.cancel()
        logger.info("Food tax scheduler stop requested")


async def on_game_started(game_code: str):
    """
    Called when a game starts.
    
    Initializes food tax tracking for the game.
    """
    db = next(get_db())
    
    try:
        game = db.query(GameSession).filter(
            GameSession.game_code == game_code.upper()
        ).first()
        
        if game:
            tax_manager = FoodTaxManager(db)
            tax_manager.initialize_food_tax_tracking(game)
            
            active_games.add(game_code.upper())
            logger.info(f"Food tax tracking initialized for game {game_code}")
    
    except Exception as e:
        logger.error(f"Error initializing food tax for game {game_code}: {str(e)}")
    
    finally:
        db.close()


async def on_game_paused(game_code: str):
    """
    Called when a game is paused.
    
    No action needed - the scheduler will skip paused games.
    """
    logger.info(f"Game {game_code} paused - food tax timer will be adjusted on resume")


async def on_game_resumed(game_code: str, pause_duration_ms: int):
    """
    Called when a game is resumed.
    
    Adjusts food tax timings to account for pause duration.
    """
    db = next(get_db())
    
    try:
        tax_manager = FoodTaxManager(db)
        result = tax_manager.adjust_for_pause(game_code, pause_duration_ms)
        
        if result.get('success'):
            logger.info(
                f"Food tax adjusted for game {game_code} after pause: "
                f"{result.get('pause_duration_seconds')}s"
            )
        else:
            logger.warning(
                f"Failed to adjust food tax for game {game_code}: "
                f"{result.get('error')}"
            )
    
    except Exception as e:
        logger.error(f"Error adjusting food tax for game {game_code}: {str(e)}")
    
    finally:
        db.close()


async def on_game_ended(game_code: str):
    """
    Called when a game ends.
    
    Removes game from active monitoring and clears failure count.
    """
    game_code_upper = game_code.upper()
    active_games.discard(game_code_upper)
    
    # Clear failure count
    if game_code_upper in game_failure_counts:
        del game_failure_counts[game_code_upper]
    
    logger.info(f"Game {game_code} ended - removed from food tax monitoring")
