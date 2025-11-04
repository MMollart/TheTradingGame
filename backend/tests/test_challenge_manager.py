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


@pytest.fixture
def banker(db, game_session):
    """Create a banker player with initial inventory"""
    banker = Player(
        game_session_id=game_session.id,
        player_name="Banker",
        role=PlayerRole.BANKER,
        player_state={'bank_inventory': {'food': 1000, 'raw_materials': 1000, 'electrical_goods': 1000, 'medical_goods': 1000}}
    )
    db.add(banker)
    db.commit()
    db.refresh(banker)
    return banker


@pytest.fixture
def game_with_buildings(game_session, db):
    """Setup game state with team buildings"""
    game_session.game_state = {
        'teams': {
            '1': {
                'buildings': {'farm': 1, 'mine': 1}
            },
            '2': {
                'buildings': {'farm': 1, 'mine': 1}
            }
        }
    }
    db.commit()
    return game_session


class TestChallengeCreation:
    """Tests for challenge request creation"""
    
    @pytest.mark.asyncio
    async def test_create_challenge_request(self, challenge_manager, game_session, player, db):
        """Test creating a new challenge request"""
        # Create banker with initial inventory
        banker = Player(
            game_session_id=game_session.id,
            player_name="Banker",
            role=PlayerRole.BANKER,
            player_state={'bank_inventory': {'food': 1000, 'raw_materials': 1000}}
        )
        db.add(banker)
        
        # Initialize game state with team buildings
        game_session.game_state = {
            'teams': {
                '1': {
                    'buildings': {'farm': 1}
                }
            }
        }
        db.commit()
        
        challenge = await challenge_manager.create_challenge_request(
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
    
    @pytest.mark.asyncio
    async def test_prevent_duplicate_request(self, challenge_manager, game_session, player, db):
        """Test that duplicate requests are prevented"""
        # Create banker with initial inventory
        banker = Player(
            game_session_id=game_session.id,
            player_name="Banker",
            role=PlayerRole.BANKER,
            player_state={'bank_inventory': {'food': 1000, 'raw_materials': 1000}}
        )
        db.add(banker)
        
        # Initialize game state with team buildings
        game_session.game_state = {
            'teams': {
                '1': {
                    'buildings': {'farm': 1}
                }
            }
        }
        db.commit()
        
        await challenge_manager.create_challenge_request(
            game_code="TEST1",
            player_id=player.id,
            building_type="farm",
            building_name="🌾 Farm",
            team_number=1,
            has_school=True
        )
        
        with pytest.raises(ValueError, match="Challenge already exists"):
            await challenge_manager.create_challenge_request(
                game_code="TEST1",
                player_id=player.id,
                building_type="farm",
                building_name="🌾 Farm",
                team_number=1,
                has_school=True
            )
    
    @pytest.mark.asyncio
    async def test_create_for_nonexistent_game(self, challenge_manager, player):
        """Test that creating challenge for nonexistent game raises error"""
        with pytest.raises(ValueError, match="Game INVALID not found"):
            await challenge_manager.create_challenge_request(
                game_code="INVALID",
                player_id=player.id,
                building_type="farm",
                building_name="🌾 Farm",
                team_number=1,
                has_school=True
            )


class TestChallengeAssignment:
    """Tests for challenge assignment"""
    
    @pytest.mark.asyncio
    async def test_assign_challenge(self, challenge_manager, game_session, player, banker, game_with_buildings):
        """Test assigning a challenge"""
        challenge = await challenge_manager.create_challenge_request(
            game_code="TEST1",
            player_id=player.id,
            building_type="farm",
            building_name="🌾 Farm",
            team_number=1,
            has_school=True
        )
        
        assigned = await challenge_manager.assign_challenge(
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
    
    @pytest.mark.asyncio
    async def test_assign_nonexistent_challenge(self, challenge_manager):
        """Test assigning a nonexistent challenge"""
        with pytest.raises(ValueError, match="Challenge 999 not found"):
            await challenge_manager.assign_challenge(
                challenge_id=999,
                challenge_type="push_ups",
                challenge_description="20 Push-ups",
                target_number=20
            )
    
    @pytest.mark.asyncio
    async def test_assign_already_assigned_challenge(self, challenge_manager, game_session, player, banker, game_with_buildings):
        """Test that assigning an already assigned challenge raises error"""
        challenge = await challenge_manager.create_challenge_request(
            game_code="TEST1",
            player_id=player.id,
            building_type="farm",
            building_name="🌾 Farm",
            team_number=1,
            has_school=True
        )
        
        await challenge_manager.assign_challenge(
            challenge_id=challenge.id,
            challenge_type="push_ups",
            challenge_description="20 Push-ups",
            target_number=20
        )
        
        with pytest.raises(ValueError, match="is not in REQUESTED state"):
            await challenge_manager.assign_challenge(
                challenge_id=challenge.id,
                challenge_type="sit_ups",
                challenge_description="30 Sit-ups",
                target_number=30
            )


class TestChallengeCompletion:
    """Tests for challenge completion and cancellation"""
    
    @pytest.mark.asyncio
    async def test_complete_challenge(self, challenge_manager, game_session, player, banker, game_with_buildings):
        """Test completing a challenge"""
        challenge = await challenge_manager.create_challenge_request(
            game_code="TEST1",
            player_id=player.id,
            building_type="farm",
            building_name="🌾 Farm",
            team_number=1,
            has_school=True
        )
        
        await challenge_manager.assign_challenge(
            challenge_id=challenge.id,
            challenge_type="push_ups",
            challenge_description="20 Push-ups",
            target_number=20
        )
        
        completed = await challenge_manager.complete_challenge(challenge.id)
        
        assert completed.status == ChallengeStatus.COMPLETED
        assert completed.completed_at is not None
    
    @pytest.mark.asyncio
    async def test_cancel_requested_challenge(self, challenge_manager, game_session, player, banker, game_with_buildings):
        """Test cancelling a requested challenge"""
        challenge = await challenge_manager.create_challenge_request(
            game_code="TEST1",
            player_id=player.id,
            building_type="farm",
            building_name="🌾 Farm",
            team_number=1,
            has_school=True
        )
        
        cancelled = await challenge_manager.cancel_challenge(challenge.id)
        
        assert cancelled.status == ChallengeStatus.CANCELLED
    
    @pytest.mark.asyncio
    async def test_cancel_assigned_challenge(self, challenge_manager, game_session, player, banker, game_with_buildings):
        """Test cancelling an assigned challenge"""
        challenge = await challenge_manager.create_challenge_request(
            game_code="TEST1",
            player_id=player.id,
            building_type="farm",
            building_name="🌾 Farm",
            team_number=1,
            has_school=True
        )
        
        await challenge_manager.assign_challenge(
            challenge_id=challenge.id,
            challenge_type="push_ups",
            challenge_description="20 Push-ups",
            target_number=20
        )
        
        cancelled = await challenge_manager.cancel_challenge(challenge.id)
        
        assert cancelled.status == ChallengeStatus.CANCELLED


class TestPauseAwareTiming:
    """Tests for pause-aware challenge timing"""
    
    @pytest.mark.asyncio
    async def test_adjust_for_pause(self, challenge_manager, game_session, player, db, banker, game_with_buildings):
        """Test adjusting challenge times for pause"""
        challenge = await challenge_manager.create_challenge_request(
            game_code="TEST1",
            player_id=player.id,
            building_type="farm",
            building_name="🌾 Farm",
            team_number=1,
            has_school=True
        )
        
        assigned = await challenge_manager.assign_challenge(
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
    
    @pytest.mark.asyncio
    async def test_adjust_multiple_challenges(self, challenge_manager, game_session, db, banker, game_with_buildings):
        """Test adjusting multiple challenges for pause"""
        # Create two players
        player1 = Player(game_session_id=game_session.id, player_name="Player 1", role=PlayerRole.PLAYER, group_number=1)
        player2 = Player(game_session_id=game_session.id, player_name="Player 2", role=PlayerRole.PLAYER, group_number=2)
        db.add(player1)
        db.add(player2)
        db.commit()
        
        # Create and assign two challenges
        for player in [player1, player2]:
            challenge = await challenge_manager.create_challenge_request(
                game_code="TEST1",
                player_id=player.id,
                building_type="farm",
                building_name="🌾 Farm",
                team_number=player.group_number,
                has_school=True
            )
            await challenge_manager.assign_challenge(
                challenge_id=challenge.id,
                challenge_type="push_ups",
                challenge_description="20 Push-ups",
                target_number=20
            )
        
        result = challenge_manager.adjust_for_pause("TEST1", 60000)
        
        assert result["adjusted_count"] == 2
    
    @pytest.mark.asyncio
    async def test_adjust_only_assigned_challenges(self, challenge_manager, game_session, player, banker, game_with_buildings):
        """Test that only assigned challenges are adjusted"""
        # Create requested challenge (not adjusted)
        await challenge_manager.create_challenge_request(
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
    
    @pytest.mark.asyncio
    async def test_check_and_expire_challenges(self, challenge_manager, game_session, player, db, banker, game_with_buildings):
        """Test expiring challenges past their deadline"""
        challenge = await challenge_manager.create_challenge_request(
            game_code="TEST1",
            player_id=player.id,
            building_type="farm",
            building_name="🌾 Farm",
            team_number=1,
            has_school=True
        )
        
        assigned = await challenge_manager.assign_challenge(
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
    
    @pytest.mark.asyncio
    async def test_dont_expire_valid_challenges(self, challenge_manager, game_session, player, banker, game_with_buildings):
        """Test that valid challenges are not expired"""
        challenge = await challenge_manager.create_challenge_request(
            game_code="TEST1",
            player_id=player.id,
            building_type="farm",
            building_name="🌾 Farm",
            team_number=1,
            has_school=True
        )
        
        await challenge_manager.assign_challenge(
            challenge_id=challenge.id,
            challenge_type="push_ups",
            challenge_description="20 Push-ups",
            target_number=20
        )
        
        expired = challenge_manager.check_and_expire_challenges("TEST1")
        
        assert len(expired) == 0


class TestChallengeQueries:
    """Tests for challenge query methods"""
    
    @pytest.mark.asyncio
    async def test_get_active_challenges(self, challenge_manager, game_session, player, db, banker, game_with_buildings):
        """Test getting all active challenges"""
        # Create requested challenge
        await challenge_manager.create_challenge_request(
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
        
        challenge2 = await challenge_manager.create_challenge_request(
            game_code="TEST1",
            player_id=player2.id,
            building_type="mine",
            building_name="⛏️ Mine",
            team_number=1,
            has_school=True
        )
        await challenge_manager.assign_challenge(
            challenge_id=challenge2.id,
            challenge_type="sit_ups",
            challenge_description="30 Sit-ups",
            target_number=30
        )
        
        active = challenge_manager.get_active_challenges("TEST1")
        
        assert len(active) == 2
        assert any(c.status == ChallengeStatus.REQUESTED for c in active)
        assert any(c.status == ChallengeStatus.ASSIGNED for c in active)
    
    @pytest.mark.asyncio
    async def test_get_time_remaining(self, challenge_manager, game_session, player, banker, game_with_buildings):
        """Test calculating time remaining for a challenge"""
        challenge = await challenge_manager.create_challenge_request(
            game_code="TEST1",
            player_id=player.id,
            building_type="farm",
            building_name="🌾 Farm",
            team_number=1,
            has_school=True
        )
        
        assigned = await challenge_manager.assign_challenge(
            challenge_id=challenge.id,
            challenge_type="push_ups",
            challenge_description="20 Push-ups",
            target_number=20
        )
        
        time_remaining = challenge_manager.get_challenge_time_remaining(assigned)
        
        assert time_remaining is not None
        assert time_remaining > 0
        assert time_remaining <= 600  # 10 minutes in seconds
    
    @pytest.mark.asyncio
    async def test_serialize_challenge(self, challenge_manager, game_session, player, banker, game_with_buildings):
        """Test serializing a challenge to dict"""
        challenge = await challenge_manager.create_challenge_request(
            game_code="TEST1",
            player_id=player.id,
            building_type="farm",
            building_name="🌾 Farm",
            team_number=1,
            has_school=True
        )
        
        assigned = await challenge_manager.assign_challenge(
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
