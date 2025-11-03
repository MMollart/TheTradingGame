"""
Tests for Challenge Manager

Run with: pytest backend/tests/test_challenge_manager.py -v
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, GameSession, Player, Challenge, ChallengeStatus, GameStatus, PlayerRole
from challenge_manager import ChallengeManager


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db():
    """Create a fresh database for each test"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def game_session(db):
    """Create a test game session"""
    game = GameSession(
        game_code="TEST1",
        status=GameStatus.IN_PROGRESS
    )
    db.add(game)
    db.commit()
    db.refresh(game)
    return game


@pytest.fixture
def player(db, game_session):
    """Create a test player"""
    player = Player(
        game_session_id=game_session.id,
        player_name="Test Player",
        role=PlayerRole.PLAYER,
        group_number=1
    )
    db.add(player)
    db.commit()
    db.refresh(player)
    return player


@pytest.fixture
def challenge_manager(db):
    """Create a ChallengeManager instance"""
    return ChallengeManager(db)


class TestChallengeCreation:
    """Tests for challenge request creation"""
    
    def test_create_challenge_request(self, challenge_manager, game_session, player):
        """Test creating a new challenge request"""
        challenge = challenge_manager.create_challenge_request(
            game_code="TEST1",
            player_id=player.id,
            building_type="farm",
            building_name="🌾 Farm",
            team_number=1,
            has_school=True
        )
        
        assert challenge.id is not None
        assert challenge.status == ChallengeStatus.REQUESTED
        assert challenge.player_id == player.id
        assert challenge.building_type == "farm"
        assert challenge.requested_at is not None
        assert challenge.assigned_at is None
    
    def test_prevent_duplicate_request(self, challenge_manager, game_session, player):
        """Test that duplicate requests are prevented"""
        challenge_manager.create_challenge_request(
            game_code="TEST1",
            player_id=player.id,
            building_type="farm",
            building_name="🌾 Farm",
            team_number=1,
            has_school=True
        )
        
        with pytest.raises(ValueError, match="Challenge already exists"):
            challenge_manager.create_challenge_request(
                game_code="TEST1",
                player_id=player.id,
                building_type="farm",
                building_name="🌾 Farm",
                team_number=1,
                has_school=True
            )
    
    def test_create_for_nonexistent_game(self, challenge_manager, player):
        """Test that creating challenge for nonexistent game raises error"""
        with pytest.raises(ValueError, match="Game INVALID not found"):
            challenge_manager.create_challenge_request(
                game_code="INVALID",
                player_id=player.id,
                building_type="farm",
                building_name="🌾 Farm",
                team_number=1,
                has_school=True
            )


class TestChallengeAssignment:
    """Tests for challenge assignment"""
    
    def test_assign_challenge(self, challenge_manager, game_session, player):
        """Test assigning a challenge"""
        challenge = challenge_manager.create_challenge_request(
            game_code="TEST1",
            player_id=player.id,
            building_type="farm",
            building_name="🌾 Farm",
            team_number=1,
            has_school=True
        )
        
        assigned = challenge_manager.assign_challenge(
            challenge_id=challenge.id,
            challenge_type="push_ups",
            challenge_description="20 Push-ups",
            target_number=20
        )
        
        assert assigned.status == ChallengeStatus.ASSIGNED
        assert assigned.challenge_type == "push_ups"
        assert assigned.challenge_description == "20 Push-ups"
        assert assigned.target_number == 20
        assert assigned.assigned_at is not None
    
    def test_assign_nonexistent_challenge(self, challenge_manager):
        """Test assigning a nonexistent challenge"""
        with pytest.raises(ValueError, match="Challenge 999 not found"):
            challenge_manager.assign_challenge(
                challenge_id=999,
                challenge_type="push_ups",
                challenge_description="20 Push-ups",
                target_number=20
            )
    
    def test_assign_already_assigned_challenge(self, challenge_manager, game_session, player):
        """Test that assigning an already assigned challenge raises error"""
        challenge = challenge_manager.create_challenge_request(
            game_code="TEST1",
            player_id=player.id,
            building_type="farm",
            building_name="🌾 Farm",
            team_number=1,
            has_school=True
        )
        
        challenge_manager.assign_challenge(
            challenge_id=challenge.id,
            challenge_type="push_ups",
            challenge_description="20 Push-ups",
            target_number=20
        )
        
        with pytest.raises(ValueError, match="is not in REQUESTED state"):
            challenge_manager.assign_challenge(
                challenge_id=challenge.id,
                challenge_type="sit_ups",
                challenge_description="30 Sit-ups",
                target_number=30
            )


class TestChallengeCompletion:
    """Tests for challenge completion and cancellation"""
    
    def test_complete_challenge(self, challenge_manager, game_session, player):
        """Test completing a challenge"""
        challenge = challenge_manager.create_challenge_request(
            game_code="TEST1",
            player_id=player.id,
            building_type="farm",
            building_name="🌾 Farm",
            team_number=1,
            has_school=True
        )
        
        challenge_manager.assign_challenge(
            challenge_id=challenge.id,
            challenge_type="push_ups",
            challenge_description="20 Push-ups",
            target_number=20
        )
        
        completed = challenge_manager.complete_challenge(challenge.id)
        
        assert completed.status == ChallengeStatus.COMPLETED
        assert completed.completed_at is not None
    
    def test_cancel_requested_challenge(self, challenge_manager, game_session, player):
        """Test cancelling a requested challenge"""
        challenge = challenge_manager.create_challenge_request(
            game_code="TEST1",
            player_id=player.id,
            building_type="farm",
            building_name="🌾 Farm",
            team_number=1,
            has_school=True
        )
        
        cancelled = challenge_manager.cancel_challenge(challenge.id)
        
        assert cancelled.status == ChallengeStatus.CANCELLED
    
    def test_cancel_assigned_challenge(self, challenge_manager, game_session, player):
        """Test cancelling an assigned challenge"""
        challenge = challenge_manager.create_challenge_request(
            game_code="TEST1",
            player_id=player.id,
            building_type="farm",
            building_name="🌾 Farm",
            team_number=1,
            has_school=True
        )
        
        challenge_manager.assign_challenge(
            challenge_id=challenge.id,
            challenge_type="push_ups",
            challenge_description="20 Push-ups",
            target_number=20
        )
        
        cancelled = challenge_manager.cancel_challenge(challenge.id)
        
        assert cancelled.status == ChallengeStatus.CANCELLED


class TestPauseAwareTiming:
    """Tests for pause-aware challenge timing"""
    
    def test_adjust_for_pause(self, challenge_manager, game_session, player, db):
        """Test adjusting challenge times for pause"""
        challenge = challenge_manager.create_challenge_request(
            game_code="TEST1",
            player_id=player.id,
            building_type="farm",
            building_name="🌾 Farm",
            team_number=1,
            has_school=True
        )
        
        assigned = challenge_manager.assign_challenge(
            challenge_id=challenge.id,
            challenge_type="push_ups",
            challenge_description="20 Push-ups",
            target_number=20
        )
        
        original_time = assigned.assigned_at
        pause_duration_ms = 120000  # 2 minutes
        
        result = challenge_manager.adjust_for_pause("TEST1", pause_duration_ms)
        
        assert result["success"] is True
        assert result["adjusted_count"] == 1
        
        # Refresh from database
        db.refresh(assigned)
        
        expected_time = original_time + timedelta(milliseconds=pause_duration_ms)
        assert assigned.assigned_at == expected_time
    
    def test_adjust_multiple_challenges(self, challenge_manager, game_session, db):
        """Test adjusting multiple challenges for pause"""
        # Create two players
        player1 = Player(game_session_id=game_session.id, player_name="Player 1", role=PlayerRole.PLAYER, group_number=1)
        player2 = Player(game_session_id=game_session.id, player_name="Player 2", role=PlayerRole.PLAYER, group_number=2)
        db.add(player1)
        db.add(player2)
        db.commit()
        
        # Create and assign two challenges
        for player in [player1, player2]:
            challenge = challenge_manager.create_challenge_request(
                game_code="TEST1",
                player_id=player.id,
                building_type="farm",
                building_name="🌾 Farm",
                team_number=player.group_number,
                has_school=True
            )
            challenge_manager.assign_challenge(
                challenge_id=challenge.id,
                challenge_type="push_ups",
                challenge_description="20 Push-ups",
                target_number=20
            )
        
        result = challenge_manager.adjust_for_pause("TEST1", 60000)
        
        assert result["adjusted_count"] == 2
    
    def test_adjust_only_assigned_challenges(self, challenge_manager, game_session, player):
        """Test that only assigned challenges are adjusted"""
        # Create requested challenge (not adjusted)
        challenge_manager.create_challenge_request(
            game_code="TEST1",
            player_id=player.id,
            building_type="farm",
            building_name="🌾 Farm",
            team_number=1,
            has_school=True
        )
        
        result = challenge_manager.adjust_for_pause("TEST1", 60000)
        
        assert result["adjusted_count"] == 0


class TestChallengeExpiry:
    """Tests for challenge expiry"""
    
    def test_check_and_expire_challenges(self, challenge_manager, game_session, player, db):
        """Test expiring challenges past their deadline"""
        challenge = challenge_manager.create_challenge_request(
            game_code="TEST1",
            player_id=player.id,
            building_type="farm",
            building_name="🌾 Farm",
            team_number=1,
            has_school=True
        )
        
        assigned = challenge_manager.assign_challenge(
            challenge_id=challenge.id,
            challenge_type="push_ups",
            challenge_description="20 Push-ups",
            target_number=20
        )
        
        # Manually set assigned_at to 11 minutes ago
        old_time = datetime.utcnow() - timedelta(minutes=11)
        assigned.assigned_at = old_time
        db.commit()
        
        expired = challenge_manager.check_and_expire_challenges("TEST1")
        
        assert len(expired) == 1
        assert expired[0].status == ChallengeStatus.EXPIRED
    
    def test_dont_expire_valid_challenges(self, challenge_manager, game_session, player):
        """Test that valid challenges are not expired"""
        challenge = challenge_manager.create_challenge_request(
            game_code="TEST1",
            player_id=player.id,
            building_type="farm",
            building_name="🌾 Farm",
            team_number=1,
            has_school=True
        )
        
        challenge_manager.assign_challenge(
            challenge_id=challenge.id,
            challenge_type="push_ups",
            challenge_description="20 Push-ups",
            target_number=20
        )
        
        expired = challenge_manager.check_and_expire_challenges("TEST1")
        
        assert len(expired) == 0


class TestChallengeQueries:
    """Tests for challenge query methods"""
    
    def test_get_active_challenges(self, challenge_manager, game_session, player, db):
        """Test getting all active challenges"""
        # Create requested challenge
        challenge_manager.create_challenge_request(
            game_code="TEST1",
            player_id=player.id,
            building_type="farm",
            building_name="🌾 Farm",
            team_number=1,
            has_school=True
        )
        
        # Create another player and assigned challenge
        player2 = Player(game_session_id=game_session.id, player_name="Player 2", role=PlayerRole.PLAYER, group_number=1)
        db.add(player2)
        db.commit()
        
        challenge2 = challenge_manager.create_challenge_request(
            game_code="TEST1",
            player_id=player2.id,
            building_type="mine",
            building_name="⛏️ Mine",
            team_number=1,
            has_school=True
        )
        challenge_manager.assign_challenge(
            challenge_id=challenge2.id,
            challenge_type="sit_ups",
            challenge_description="30 Sit-ups",
            target_number=30
        )
        
        active = challenge_manager.get_active_challenges("TEST1")
        
        assert len(active) == 2
        assert any(c.status == ChallengeStatus.REQUESTED for c in active)
        assert any(c.status == ChallengeStatus.ASSIGNED for c in active)
    
    def test_get_time_remaining(self, challenge_manager, game_session, player):
        """Test calculating time remaining for a challenge"""
        challenge = challenge_manager.create_challenge_request(
            game_code="TEST1",
            player_id=player.id,
            building_type="farm",
            building_name="🌾 Farm",
            team_number=1,
            has_school=True
        )
        
        assigned = challenge_manager.assign_challenge(
            challenge_id=challenge.id,
            challenge_type="push_ups",
            challenge_description="20 Push-ups",
            target_number=20
        )
        
        time_remaining = challenge_manager.get_challenge_time_remaining(assigned)
        
        assert time_remaining is not None
        assert time_remaining > 0
        assert time_remaining <= 600  # 10 minutes in seconds
    
    def test_serialize_challenge(self, challenge_manager, game_session, player):
        """Test serializing a challenge to dict"""
        challenge = challenge_manager.create_challenge_request(
            game_code="TEST1",
            player_id=player.id,
            building_type="farm",
            building_name="🌾 Farm",
            team_number=1,
            has_school=True
        )
        
        assigned = challenge_manager.assign_challenge(
            challenge_id=challenge.id,
            challenge_type="push_ups",
            challenge_description="20 Push-ups",
            target_number=20
        )
        
        data = challenge_manager.serialize_challenge(assigned, include_time_remaining=True)
        
        assert data["id"] == assigned.id
        assert data["status"] == "assigned"
        assert data["challenge_type"] == "push_ups"
        assert data["time_remaining_seconds"] is not None
