"""
Test suite for challenge locking logic.

Tests the following scenarios:
1. Without school: Team-wide lock affects all buildings for entire team
2. With school: Individual lock affects all buildings for specific player only
"""

import pytest


class MockChallenge:
    """Mock challenge object for testing."""
    def __init__(self, player_id, player_name, team_number, building_type, has_school):
        self.player_id = player_id
        self.player_name = player_name
        self.team_number = team_number
        self.building_type = building_type
        self.has_school = has_school


class MockPlayer:
    """Mock player object for testing."""
    def __init__(self, player_id, player_name, team_number):
        self.id = player_id
        self.name = player_name
        self.groupNumber = team_number


def check_challenge_lock(building_type, current_player, active_challenges):
    """
    Python implementation of the JavaScript checkChallengeLock function.
    
    When a challenge is active, ALL buildings are locked (not just the requested building type).
    - If has_school=False: Team-wide lock (all buildings for entire team)
    - If has_school=True: Individual lock (all buildings for that player only)
    
    Args:
        building_type: The building type being checked (e.g., 'farm', 'mine')
        current_player: MockPlayer object representing the current player
        active_challenges: Dict of active challenges
    
    Returns:
        Dict with lock status:
        - isLocked: bool
        - teamWide: bool (if locked team-wide)
        - lockedByName: str (player name who has the lock)
        - lockedByCurrentPlayer: bool
        - buildingName: str
        - activeBuildingType: str (the building that has the active challenge)
    """
    current_team_number = current_player.groupNumber
    
    # Check all active challenges - any challenge locks ALL buildings
    for key, challenge in active_challenges.items():
        # If no school, check team-wide lock (locks all buildings for the team)
        if not challenge.has_school:
            # Only lock if same team
            if challenge.team_number == current_team_number:
                return {
                    'isLocked': True,
                    'teamWide': True,
                    'lockedByName': challenge.player_name,
                    'lockedByCurrentPlayer': challenge.player_id == current_player.id,
                    'buildingName': challenge.building_type,
                    'activeBuildingType': challenge.building_type
                }
        else:
            # With school, only lock for the specific player (locks all buildings for that player)
            if challenge.player_id == current_player.id and challenge.team_number == current_team_number:
                return {
                    'isLocked': True,
                    'teamWide': False,
                    'lockedByName': challenge.player_name,
                    'lockedByCurrentPlayer': True,
                    'buildingName': challenge.building_type,
                    'activeBuildingType': challenge.building_type
                }
            # Different player with school = no lock
    
    return {'isLocked': False}


class TestChallengeLockingWithoutSchool:
    """Test challenge locking when team does NOT have a school (team-wide locks)."""
    
    def test_same_team_same_player_different_building(self):
        """When player has active farm challenge, they cannot request mine challenge."""
        player = MockPlayer(1, "Alice", 1)
        active_challenges = {
            'team1-farm': MockChallenge(1, "Alice", 1, 'farm', has_school=False)
        }
        
        result = check_challenge_lock('mine', player, active_challenges)
        
        assert result['isLocked'] is True
        assert result['teamWide'] is True
        assert result['lockedByCurrentPlayer'] is True
        assert result['activeBuildingType'] == 'farm'
    
    def test_same_team_different_player_any_building(self):
        """When teammate has active farm challenge, other players cannot request any challenge."""
        current_player = MockPlayer(2, "Bob", 1)
        active_challenges = {
            'team1-farm': MockChallenge(1, "Alice", 1, 'farm', has_school=False)
        }
        
        # Try to request different building types
        for building in ['mine', 'electrical_factory', 'medical_factory', 'farm']:
            result = check_challenge_lock(building, current_player, active_challenges)
            
            assert result['isLocked'] is True, f"Building {building} should be locked"
            assert result['teamWide'] is True
            assert result['lockedByCurrentPlayer'] is False
            assert result['lockedByName'] == "Alice"
            assert result['activeBuildingType'] == 'farm'
    
    def test_different_team_not_locked(self):
        """When different team has active challenge, current team is not locked."""
        current_player = MockPlayer(3, "Charlie", 2)
        active_challenges = {
            'team1-farm': MockChallenge(1, "Alice", 1, 'farm', has_school=False)
        }
        
        result = check_challenge_lock('mine', current_player, active_challenges)
        
        assert result['isLocked'] is False
    
    def test_no_active_challenges(self):
        """When no active challenges, nothing is locked."""
        player = MockPlayer(1, "Alice", 1)
        active_challenges = {}
        
        result = check_challenge_lock('farm', player, active_challenges)
        
        assert result['isLocked'] is False


class TestChallengeLockingWithSchool:
    """Test challenge locking when team HAS a school (individual locks)."""
    
    def test_same_player_different_building(self):
        """When player has active farm challenge, they cannot request mine challenge."""
        player = MockPlayer(1, "Alice", 1)
        active_challenges = {
            '1-farm': MockChallenge(1, "Alice", 1, 'farm', has_school=True)
        }
        
        result = check_challenge_lock('mine', player, active_challenges)
        
        assert result['isLocked'] is True
        assert result['teamWide'] is False
        assert result['lockedByCurrentPlayer'] is True
        assert result['activeBuildingType'] == 'farm'
    
    def test_different_player_same_team_not_locked(self):
        """When teammate has active challenge but team has school, other players can request challenges."""
        current_player = MockPlayer(2, "Bob", 1)
        active_challenges = {
            '1-farm': MockChallenge(1, "Alice", 1, 'farm', has_school=True)
        }
        
        # Try to request different building types - all should be unlocked
        for building in ['mine', 'electrical_factory', 'medical_factory', 'farm']:
            result = check_challenge_lock(building, current_player, active_challenges)
            
            assert result['isLocked'] is False, f"Building {building} should NOT be locked for different player when has_school=True"
    
    def test_multiple_players_with_school(self):
        """Multiple players on same team can have simultaneous challenges when team has school."""
        alice = MockPlayer(1, "Alice", 1)
        bob = MockPlayer(2, "Bob", 1)
        charlie = MockPlayer(3, "Charlie", 1)
        
        active_challenges = {
            '1-farm': MockChallenge(1, "Alice", 1, 'farm', has_school=True),
            '2-mine': MockChallenge(2, "Bob", 1, 'mine', has_school=True)
        }
        
        # Alice is locked (has active farm challenge)
        result_alice = check_challenge_lock('electrical_factory', alice, active_challenges)
        assert result_alice['isLocked'] is True
        assert result_alice['lockedByCurrentPlayer'] is True
        assert result_alice['activeBuildingType'] == 'farm'
        
        # Bob is locked (has active mine challenge)
        result_bob = check_challenge_lock('farm', bob, active_challenges)
        assert result_bob['isLocked'] is True
        assert result_bob['lockedByCurrentPlayer'] is True
        assert result_bob['activeBuildingType'] == 'mine'
        
        # Charlie is NOT locked (no active challenge)
        result_charlie = check_challenge_lock('medical_factory', charlie, active_challenges)
        assert result_charlie['isLocked'] is False
    
    def test_different_team_with_school_not_locked(self):
        """Different team's challenges don't affect current team even with school."""
        current_player = MockPlayer(3, "Charlie", 2)
        active_challenges = {
            '1-farm': MockChallenge(1, "Alice", 1, 'farm', has_school=True)
        }
        
        result = check_challenge_lock('mine', current_player, active_challenges)
        
        assert result['isLocked'] is False


class TestChallengeLockingMixedScenarios:
    """Test challenge locking with mixed has_school scenarios."""
    
    def test_team_without_school_team_with_school(self):
        """Team 1 (no school) is locked, Team 2 (has school) operates independently."""
        # Team 1 player
        alice = MockPlayer(1, "Alice", 1)
        bob = MockPlayer(2, "Bob", 1)
        
        # Team 2 players
        charlie = MockPlayer(3, "Charlie", 2)
        diana = MockPlayer(4, "Diana", 2)
        
        active_challenges = {
            'team1-farm': MockChallenge(1, "Alice", 1, 'farm', has_school=False),
            '3-mine': MockChallenge(3, "Charlie", 2, 'mine', has_school=True)
        }
        
        # Team 1: Alice and Bob both locked (no school, team-wide)
        result_alice = check_challenge_lock('mine', alice, active_challenges)
        assert result_alice['isLocked'] is True
        assert result_alice['teamWide'] is True
        
        result_bob = check_challenge_lock('electrical_factory', bob, active_challenges)
        assert result_bob['isLocked'] is True
        assert result_bob['teamWide'] is True
        
        # Team 2: Charlie locked (his own challenge), Diana not locked (has school)
        result_charlie = check_challenge_lock('farm', charlie, active_challenges)
        assert result_charlie['isLocked'] is True
        assert result_charlie['teamWide'] is False
        assert result_charlie['lockedByCurrentPlayer'] is True
        
        result_diana = check_challenge_lock('medical_factory', diana, active_challenges)
        assert result_diana['isLocked'] is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
