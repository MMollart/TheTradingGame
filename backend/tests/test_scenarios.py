"""
Tests for historical scenarios feature
"""

import pytest
from scenarios import (
    ScenarioType, SCENARIOS, get_scenario, list_scenarios,
    get_nation_config_for_scenario
)


class TestScenarios:
    """Test historical scenarios data and functions"""
    
    def test_all_scenarios_exist(self):
        """Test that all 6 scenarios are defined"""
        expected_scenarios = [
            ScenarioType.MARSHALL_PLAN,
            ScenarioType.SILK_ROAD,
            ScenarioType.INDUSTRIAL_REVOLUTION,
            ScenarioType.SPACE_RACE,
            ScenarioType.AGE_OF_EXPLORATION,
            ScenarioType.GREAT_DEPRESSION
        ]
        
        for scenario_id in expected_scenarios:
            assert scenario_id in SCENARIOS, f"Scenario {scenario_id} not found"
    
    def test_scenario_structure(self):
        """Test that each scenario has required fields"""
        required_fields = [
            'id', 'name', 'period', 'difficulty', 'recommended_duration',
            'description', 'nation_profiles', 'special_rules', 'victory_conditions'
        ]
        
        for scenario_id, scenario in SCENARIOS.items():
            for field in required_fields:
                assert field in scenario, f"Scenario {scenario_id} missing field {field}"
    
    def test_scenario_nation_profiles(self):
        """Test that each scenario has 4 nation profiles"""
        for scenario_id, scenario in SCENARIOS.items():
            nation_profiles = scenario['nation_profiles']
            assert len(nation_profiles) == 4, f"Scenario {scenario_id} should have 4 nations"
            
            # Check that nations are numbered 1-4
            for i in range(1, 5):
                assert str(i) in nation_profiles, f"Scenario {scenario_id} missing nation {i}"
                
                # Check nation structure
                nation = nation_profiles[str(i)]
                assert 'name' in nation
                assert 'description' in nation
                assert 'starting_resources' in nation
                assert 'starting_buildings' in nation
    
    def test_get_scenario(self):
        """Test get_scenario function"""
        scenario = get_scenario(ScenarioType.MARSHALL_PLAN)
        assert scenario['id'] == ScenarioType.MARSHALL_PLAN
        assert scenario['name'] == 'Post-WWII Marshall Plan'
        
        # Test invalid scenario
        with pytest.raises(ValueError):
            get_scenario('invalid_scenario')
    
    def test_list_scenarios(self):
        """Test list_scenarios function"""
        scenarios = list_scenarios()
        assert len(scenarios) == 6
        
        # Check structure of listed scenarios
        for scenario in scenarios:
            assert 'id' in scenario
            assert 'name' in scenario
            assert 'period' in scenario
            assert 'difficulty' in scenario
            assert 'recommended_duration' in scenario
            assert 'description' in scenario
    
    def test_get_nation_config_for_scenario(self):
        """Test getting nation configuration for a scenario"""
        # Test Marshall Plan - Britain
        config = get_nation_config_for_scenario(ScenarioType.MARSHALL_PLAN, 1)
        assert config['name'] == 'Britain'
        assert 'resources' in config
        assert 'buildings' in config
        assert config['scenario_id'] == ScenarioType.MARSHALL_PLAN
        assert config['team_number'] == 1
        
        # Test invalid team number
        with pytest.raises(ValueError):
            get_nation_config_for_scenario(ScenarioType.MARSHALL_PLAN, 5)
        
        # Test invalid scenario
        with pytest.raises(ValueError):
            get_nation_config_for_scenario('invalid_scenario', 1)
    
    def test_scenario_difficulties(self):
        """Test that scenarios have appropriate difficulty levels"""
        valid_difficulties = ['easy', 'medium', 'hard']
        
        for scenario_id, scenario in SCENARIOS.items():
            assert scenario['difficulty'] in valid_difficulties, \
                f"Scenario {scenario_id} has invalid difficulty: {scenario['difficulty']}"
    
    def test_scenario_durations(self):
        """Test that scenario durations are reasonable"""
        for scenario_id, scenario in SCENARIOS.items():
            duration = scenario['recommended_duration']
            assert 60 <= duration <= 240, \
                f"Scenario {scenario_id} has invalid duration: {duration}"
            assert duration % 30 == 0, \
                f"Scenario {scenario_id} duration should be in 30-min intervals: {duration}"
    
    def test_scenario_special_rules(self):
        """Test that special rules have required structure"""
        for scenario_id, scenario in SCENARIOS.items():
            special_rules = scenario['special_rules']
            assert len(special_rules) >= 1, \
                f"Scenario {scenario_id} should have at least one special rule"
            
            for rule in special_rules:
                assert 'name' in rule
                assert 'description' in rule
                assert 'implementation' in rule
                assert 'parameters' in rule
    
    def test_scenario_victory_conditions(self):
        """Test that victory conditions have required structure"""
        for scenario_id, scenario in SCENARIOS.items():
            victory_conditions = scenario['victory_conditions']
            assert len(victory_conditions) >= 1, \
                f"Scenario {scenario_id} should have at least one victory condition"
            
            for condition in victory_conditions:
                assert 'type' in condition
                assert 'description' in condition
    
    def test_marshall_plan_specifics(self):
        """Test specific details of Marshall Plan scenario"""
        scenario = get_scenario(ScenarioType.MARSHALL_PLAN)
        assert scenario['difficulty'] == 'medium'
        assert scenario['recommended_duration'] == 120
        
        # Check Britain's starting configuration
        britain = scenario['nation_profiles']['1']
        assert britain['name'] == 'Britain'
        assert 'infrastructure' in britain['starting_buildings']


class TestScenarioResources:
    """Test scenario-specific resource and building definitions"""
    
    def test_get_scenario_resources_space_race(self):
        """Test Space Race has custom resources"""
        from scenarios import get_scenario_resources, ScenarioType
        
        resources = get_scenario_resources(ScenarioType.SPACE_RACE)
        
        # Should have 4 resources
        assert len(resources) == 4
        
        # Check specific Space Race resources
        resource_names = [r['name'] for r in resources.values()]
        assert 'Knowledge' in resource_names
        assert 'Liquid Fuels' in resource_names
        assert 'Metals' in resource_names
        assert 'Electronics' in resource_names
        
        # Check each resource has required fields
        for res_key, res_data in resources.items():
            assert 'id' in res_data
            assert 'name' in res_data
            assert 'icon' in res_data
            assert 'description' in res_data
            assert 'base_price' in res_data
            assert 'rarity' in res_data
            assert 'maps_to' in res_data
    
    def test_get_scenario_resources_default(self):
        """Test default resources for non-scenario games"""
        from scenarios import get_scenario_resources
        
        resources = get_scenario_resources(None)
        
        # Should have 4 default resources
        assert len(resources) == 4
        
        resource_names = [r['name'] for r in resources.values()]
        assert 'Food' in resource_names
        assert 'Raw Materials' in resource_names
        assert 'Electrical Goods' in resource_names
        assert 'Medical Goods' in resource_names
    
    def test_get_scenario_buildings_space_race(self):
        """Test Space Race has custom buildings"""
        from scenarios import get_scenario_buildings, ScenarioType
        
        buildings = get_scenario_buildings(ScenarioType.SPACE_RACE)
        
        # Should have 4 buildings
        assert len(buildings) == 4
        
        # Check specific Space Race buildings
        building_names = [b['name'] for b in buildings.values()]
        assert 'Research Library' in building_names
        assert 'Fuel Refinery' in building_names
        assert 'Metalworks' in building_names
        assert 'Electronics Lab' in building_names
        
        # Check each building has required fields
        for bld_key, bld_data in buildings.items():
            assert 'id' in bld_data
            assert 'name' in bld_data
            assert 'icon' in bld_data
            assert 'description' in bld_data
            assert 'produces' in bld_data
            assert 'maps_to' in bld_data
    
    def test_get_scenario_buildings_default(self):
        """Test default buildings for non-scenario games"""
        from scenarios import get_scenario_buildings
        
        buildings = get_scenario_buildings(None)
        
        # Should have 4 default buildings
        assert len(buildings) == 4
        
        building_names = [b['name'] for b in buildings.values()]
        assert 'Farm' in building_names
        assert 'Mine' in building_names
        assert 'Electrical Factory' in building_names
        assert 'Medical Factory' in building_names
    
    def test_get_resource_price_difficulty(self):
        """Test resource prices adjust based on difficulty"""
        from scenarios import get_resource_price, ScenarioType
        
        # Test Space Race metals pricing
        easy_price = get_resource_price(ScenarioType.SPACE_RACE, 'metals', 'easy')
        medium_price = get_resource_price(ScenarioType.SPACE_RACE, 'metals', 'medium')
        hard_price = get_resource_price(ScenarioType.SPACE_RACE, 'metals', 'hard')
        
        # Easy should be cheaper than medium
        assert easy_price < medium_price
        # Hard should be more expensive than medium
        assert hard_price > medium_price
        
        # Check specific multipliers (base price is 20 for metals)
        assert easy_price == int(20 * 0.8)  # 16
        assert medium_price == 20
        assert hard_price == int(20 * 1.3)  # 26
    
    def test_scenario_includes_metadata(self):
        """Test that get_scenario includes resource and building metadata"""
        from scenarios import get_scenario, ScenarioType
        
        scenario = get_scenario(ScenarioType.SPACE_RACE)
        
        # Should include metadata
        assert 'resources' in scenario
        assert 'buildings' in scenario
        
        # Resources should be populated
        assert len(scenario['resources']) == 4
        assert 'resource_1' in scenario['resources']
        
        # Buildings should be populated
        assert len(scenario['buildings']) == 4
        assert 'building_1' in scenario['buildings']
    
    def test_all_scenarios_have_resource_definitions(self):
        """Test that all scenarios have resource definitions (custom or default)"""
        from scenarios import get_scenario_resources, SCENARIOS
        
        for scenario_id in SCENARIOS.keys():
            resources = get_scenario_resources(scenario_id)
            assert len(resources) >= 4, f"Scenario {scenario_id} should have at least 4 resources"
            
            # Each resource should have required metadata
            for res in resources.values():
                assert 'icon' in res
                assert 'name' in res
                assert 'base_price' in res
    
    def test_resource_mapping_consistency(self):
        """Test that resource mappings are consistent with game_constants"""
        from scenarios import get_scenario_resources, ScenarioType
        from game_constants import ResourceType
        
        resources = get_scenario_resources(ScenarioType.SPACE_RACE)
        
        # Check that maps_to values are valid ResourceType values
        valid_resource_types = [rt.value for rt in ResourceType if rt != ResourceType.CURRENCY]
        
        for res in resources.values():
            maps_to = res.get('maps_to')
            if maps_to and hasattr(maps_to, 'value'):
                # It's an enum, get the value
                assert maps_to.value in valid_resource_types or maps_to in valid_resource_types
    
    def test_silk_road_specifics(self):
        """Test specific details of Silk Road scenario"""
        scenario = get_scenario(ScenarioType.SILK_ROAD)
        assert scenario['difficulty'] == 'easy'
        assert scenario['recommended_duration'] == 90
        
        # Check China's starting configuration
        china = scenario['nation_profiles']['1']
        assert china['name'] == 'China'
    
    def test_great_depression_specifics(self):
        """Test specific details of Great Depression scenario"""
        scenario = get_scenario(ScenarioType.GREAT_DEPRESSION)
        assert scenario['difficulty'] == 'hard'
        assert scenario['recommended_duration'] == 90
        
        # Check that nations start with reduced resources (depression effect)
        for nation_key, nation in scenario['nation_profiles'].items():
            resources = nation['starting_resources']
            # All nations should have relatively low starting resources
            assert 'currency' in resources
            # USA starts with 75, which is low
            if nation['name'] == 'USA':
                assert resources['currency'] == 75
