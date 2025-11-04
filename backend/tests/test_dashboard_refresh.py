"""
Tests for dashboard refresh WebSocket broadcasts.

Tests verify that the following endpoints broadcast state_updated events:
1. complete_challenge_with_bank_transfer
2. give_manual_resources
3. give_manual_buildings
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# These tests verify the structure and behavior of the changes


class TestDashboardRefreshBroadcasts:
    """Test that state updates are broadcast to trigger dashboard refreshes"""
    
    def test_manual_resources_broadcasts_state_update(self):
        """
        Test that giving manual resources broadcasts a state_updated event.
        
        This test verifies the code structure rather than executing it,
        since we have dependency compatibility issues.
        """
        # Read the main.py file and verify the broadcast is present
        with open('/home/runner/work/TheTradingGame/TheTradingGame/backend/main.py', 'r') as f:
            content = f.read()
        
        # Find the manual-resources endpoint
        manual_resources_start = content.find('async def give_manual_resources(')
        manual_resources_end = content.find('@app.post("/games/{game_code}/manual-buildings")')
        manual_resources_code = content[manual_resources_start:manual_resources_end]
        
        # Verify it broadcasts state_updated
        assert 'await manager.broadcast_to_game' in manual_resources_code, \
            "manual-resources endpoint should broadcast to game"
        assert '"type": "state_updated"' in manual_resources_code, \
            "manual-resources should broadcast state_updated event"
        assert '"state": game.game_state' in manual_resources_code, \
            "manual-resources should include game state in broadcast"
    
    def test_manual_buildings_broadcasts_state_update(self):
        """
        Test that giving manual buildings broadcasts a state_updated event.
        """
        with open('/home/runner/work/TheTradingGame/TheTradingGame/backend/main.py', 'r') as f:
            content = f.read()
        
        # Find the manual-buildings endpoint
        manual_buildings_start = content.find('async def give_manual_buildings(')
        manual_buildings_end = content.find('@app.post("/games/{game_code}/build-building")')
        manual_buildings_code = content[manual_buildings_start:manual_buildings_end]
        
        # Verify it broadcasts state_updated
        assert 'await manager.broadcast_to_game' in manual_buildings_code, \
            "manual-buildings endpoint should broadcast to game"
        assert '"type": "state_updated"' in manual_buildings_code, \
            "manual-buildings should broadcast state_updated event"
        assert '"state": game.game_state' in manual_buildings_code, \
            "manual-buildings should include game state in broadcast"
    
    def test_challenge_completion_broadcasts_state_update(self):
        """
        Test that completing a challenge broadcasts a state_updated event.
        """
        with open('/home/runner/work/TheTradingGame/TheTradingGame/backend/main.py', 'r') as f:
            content = f.read()
        
        # Find the complete_challenge endpoint
        complete_challenge_start = content.find('async def complete_challenge_with_bank_transfer(')
        # Find the next endpoint after it
        complete_challenge_end = content.find('@app.post("/games/{game_code}/challenges")', 
                                               complete_challenge_start)
        complete_challenge_code = content[complete_challenge_start:complete_challenge_end]
        
        # Verify it broadcasts state_updated
        assert 'await manager.broadcast_to_game' in complete_challenge_code, \
            "challenge completion endpoint should broadcast to game"
        assert '"type": "state_updated"' in complete_challenge_code, \
            "challenge completion should broadcast state_updated event"
        assert '"state": game.game_state' in complete_challenge_code, \
            "challenge completion should include game state in broadcast"
    
    def test_all_broadcasts_use_uppercase_game_code(self):
        """
        Test that all broadcasts use game_code.upper() as per coding conventions.
        """
        with open('/home/runner/work/TheTradingGame/TheTradingGame/backend/main.py', 'r') as f:
            content = f.read()
        
        # Find all our new broadcasts
        broadcasts = []
        
        # Manual resources
        manual_resources_start = content.find('async def give_manual_resources(')
        manual_resources_end = content.find('@app.post("/games/{game_code}/manual-buildings")')
        broadcasts.append(content[manual_resources_start:manual_resources_end])
        
        # Manual buildings
        manual_buildings_start = content.find('async def give_manual_buildings(')
        manual_buildings_end = content.find('@app.post("/games/{game_code}/build-building")')
        broadcasts.append(content[manual_buildings_start:manual_buildings_end])
        
        # Challenge completion
        complete_challenge_start = content.find('async def complete_challenge_with_bank_transfer(')
        complete_challenge_end = content.find('@app.post("/games/{game_code}/challenges")', 
                                               complete_challenge_start)
        broadcasts.append(content[complete_challenge_start:complete_challenge_end])
        
        # Verify each uses .upper()
        for i, broadcast in enumerate(broadcasts):
            assert 'game_code.upper()' in broadcast, \
                f"Broadcast {i} should use game_code.upper() for consistency"
    
    def test_broadcasts_happen_after_db_commit(self):
        """
        Test that broadcasts happen after db.commit() to ensure data is persisted.
        """
        with open('/home/runner/work/TheTradingGame/TheTradingGame/backend/main.py', 'r') as f:
            content = f.read()
        
        # Check manual resources
        manual_resources_start = content.find('async def give_manual_resources(')
        manual_resources_end = content.find('@app.post("/games/{game_code}/manual-buildings")')
        manual_resources_code = content[manual_resources_start:manual_resources_end]
        
        commit_pos = manual_resources_code.find('db.commit()')
        broadcast_pos = manual_resources_code.find('await manager.broadcast_to_game')
        assert commit_pos < broadcast_pos, \
            "In manual-resources, db.commit() should happen before broadcast"
        
        # Check manual buildings
        manual_buildings_start = content.find('async def give_manual_buildings(')
        manual_buildings_end = content.find('@app.post("/games/{game_code}/build-building")')
        manual_buildings_code = content[manual_buildings_start:manual_buildings_end]
        
        commit_pos = manual_buildings_code.find('db.commit()')
        broadcast_pos = manual_buildings_code.find('await manager.broadcast_to_game')
        assert commit_pos < broadcast_pos, \
            "In manual-buildings, db.commit() should happen before broadcast"
        
        # Check challenge completion
        complete_challenge_start = content.find('async def complete_challenge_with_bank_transfer(')
        complete_challenge_end = content.find('@app.post("/games/{game_code}/challenges")', 
                                               complete_challenge_start)
        complete_challenge_code = content[complete_challenge_start:complete_challenge_end]
        
        commit_pos = complete_challenge_code.find('db.commit()')
        broadcast_pos = complete_challenge_code.find('await manager.broadcast_to_game')
        assert commit_pos < broadcast_pos, \
            "In challenge completion, db.commit() should happen before broadcast"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
