"""
Price Fluctuation Scheduler - Background task for random price variations

This module runs a background task that periodically checks all active games
and applies random price fluctuations with momentum and mean reversion.
"""

import asyncio
import logging
from typing import Dict, Set
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from database import get_db
from models import GameSession, GameStatus
from pricing_manager import PricingManager
from websocket_manager import manager as ws_manager

logger = logging.getLogger(__name__)

# Global state
scheduler_task = None
scheduler_running = False

# Configuration
CHECK_INTERVAL_SECONDS = 1  # Check every second for fluctuations


async def check_all_games_for_price_fluctuations():
    """
    Check all active games for price fluctuations.
    
    This runs every second and applies random price changes based on
    probability, momentum, mean reversion, and active events.
    """
    db = next(get_db())
    
    try:
        # Expire all objects to ensure we get fresh data from database
        # This prevents stale data issues when game status changes in other sessions
        db.expire_all()
        
        # Get all active games (in progress, not paused)
        games = db.query(GameSession).filter(
            GameSession.status == GameStatus.IN_PROGRESS
        ).all()
        
        pricing_mgr = PricingManager(db)
        
        for game in games:
            try:
                # Skip if game doesn't have bank prices initialized
                if not game.game_state or 'bank_prices' not in game.game_state:
                    continue
                
                current_prices = game.game_state['bank_prices']
                
                # Apply random fluctuations
                updated_prices, changed_resources = pricing_mgr.apply_random_fluctuation(
                    game.game_code,
                    current_prices
                )
                
                # If any prices changed, update and broadcast
                if changed_resources:
                    game.game_state['bank_prices'] = updated_prices
                    flag_modified(game, 'game_state')
                    db.commit()
                    
                    # Broadcast price updates
                    await ws_manager.broadcast_to_game(
                        game.game_code.upper(),
                        {
                            "type": "event",
                            "event_type": "bank_prices_updated",
                            "data": {
                                "prices": updated_prices,
                                "changed_resources": changed_resources,
                                "timestamp": datetime.utcnow().isoformat()
                            }
                        }
                    )
                    
                    logger.debug(
                        f"Price fluctuation in game {game.game_code}: "
                        f"changed {', '.join(changed_resources)}"
                    )
            
            except Exception as e:
                logger.error(
                    f"Error processing price fluctuation for game {game.game_code}: {str(e)}",
                    exc_info=True
                )
    
    except Exception as e:
        logger.error(f"Error in check_all_games_for_price_fluctuations: {str(e)}", exc_info=True)
    
    finally:
        db.close()


async def price_fluctuation_scheduler():
    """
    Background scheduler task that runs continuously.
    
    Checks all active games every second for price fluctuations.
    """
    global scheduler_running
    scheduler_running = True
    
    logger.info("Price fluctuation scheduler started")
    
    try:
        while scheduler_running:
            await check_all_games_for_price_fluctuations()
            
            # Wait before next check
            await asyncio.sleep(CHECK_INTERVAL_SECONDS)
    
    except asyncio.CancelledError:
        logger.info("Price fluctuation scheduler cancelled")
        raise
    
    except Exception as e:
        logger.error(f"Error in price_fluctuation_scheduler: {str(e)}", exc_info=True)
    
    finally:
        scheduler_running = False
        logger.info("Price fluctuation scheduler stopped")


def start_price_fluctuation_scheduler():
    """
    Start the price fluctuation scheduler background task.
    
    This should be called when the application starts.
    """
    global scheduler_task, scheduler_running
    
    if scheduler_task is None or scheduler_task.done():
        scheduler_task = asyncio.create_task(price_fluctuation_scheduler())
        logger.info("Price fluctuation scheduler task created")
    else:
        logger.warning("Price fluctuation scheduler already running")


def stop_price_fluctuation_scheduler():
    """
    Stop the price fluctuation scheduler background task.
    
    This should be called when the application shuts down.
    """
    global scheduler_task, scheduler_running
    
    scheduler_running = False
    
    if scheduler_task and not scheduler_task.done():
        scheduler_task.cancel()
        logger.info("Price fluctuation scheduler stop requested")
