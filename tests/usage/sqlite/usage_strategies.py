"""
Usage examples for apps.sqlite.strategies.py

This module demonstrates:
- StrategyManager class for strategy management
- Creating and versioning strategies
- Strategy sharing between users
- CRUD operations for strategies
"""

from apps.sqlite import SQLiteDatabase


def example_create_strategy():
    """
    Example: Creating a new trading strategy

    Strategies can have:
    - Name and description
    - Category (Trend Following, Mean Reversion, etc.)
    - Status (active/inactive/testing)
    - Public/private visibility
    """
    db = SQLiteDatabase(db_path="test_strategies.db")
    db.initialize_database()

    # Create a user first
    user_id = db.create_user(
        email="strategist@example.com",
        username="strategist",
        password="password123"
    )

    # Create a trend following strategy
    strategy_id = db.create_strategy(
        user_id=user_id,
        name="Moving Average Crossover",
        description="Simple MA crossover strategy using 10/20 periods",
        category="Trend Following",
        status="testing"
    )
    print(f"Strategy created with ID: {strategy_id}")

    # Create a mean reversion strategy
    strategy_id2 = db.create_strategy(
        user_id=user_id,
        name="RSI Mean Reversion",
        description="Buy oversold, sell overbought using RSI",
        category="Mean Reversion",
        status="inactive",
        is_public=True
    )
    print(f"Public strategy created with ID: {strategy_id2}")


def example_create_strategy_version():
    """
    Example: Creating strategy versions

    Strategy versioning allows:
    - Tracking changes over time
    - Rolling back to previous versions
    - A/B testing different parameter sets
    - Maintaining changelog
    """
    db = SQLiteDatabase(db_path="test_versions.db")
    db.initialize_database()

    # Setup
    user_id = db.create_user(
        email="dev@example.com",
        username="developer",
        password="pass123"
    )
    strategy_id = db.create_strategy(
        user_id=user_id,
        name="Adaptive MA Strategy",
        description="Dynamic moving average strategy"
    )

    # Create version 1.0.0
    version_id_v1 = db.create_strategy_version(
        strategy_id=strategy_id,
        version="1.0.0",
        file_path="strategies/adaptive_ma_v1.py",
        parameters={"fast_period": 10, "slow_period": 20},
        changelog="Initial release",
        created_by=user_id
    )
    print(f"Version 1.0.0 created: ID {version_id_v1}")

    # Create version 1.1.0 with updated parameters
    version_id_v11 = db.create_strategy_version(
        strategy_id=strategy_id,
        version="1.1.0",
        file_path="strategies/adaptive_ma_v11.py",
        parameters={"fast_period": 8, "slow_period": 21, "filter_atr": True},
        changelog="Added ATR filter for better entries",
        created_by=user_id
    )
    print(f"Version 1.1.0 created: ID {version_id_v11}")

    # Create version 2.0.0 with major changes
    version_id_v2 = db.create_strategy_version(
        strategy_id=strategy_id,
        version="2.0.0",
        file_path="strategies/adaptive_ma_v2.py",
        parameters={
            "fast_period": 8,
            "slow_period": 21,
            "use_ema": True,
            "stop_loss_atr_mult": 2.0,
            "take_profit_atr_mult": 3.0
        },
        changelog="Major refactor: Added EMA support and risk management",
        created_by=user_id
    )
    print(f"Version 2.0.0 created: ID {version_id_v2}")


def example_get_strategy():
    """
    Example: Retrieving strategy information

    Get strategy details including active version.
    """
    db = SQLiteDatabase(db_path="test_get_strategy.db")
    db.initialize_database()

    # Setup
    user_id = db.create_user(
        email="user@example.com",
        username="user",
        password="pass"
    )
    strategy_id = db.create_strategy(
        user_id=user_id,
        name="Test Strategy",
        description="A test strategy",
        category="Scalping"
    )
    version_id = db.create_strategy_version(
        strategy_id=strategy_id,
        version="1.0.0",
        file_path="strategies/test.py",
        parameters={"param1": 10}
    )

    # Get strategy
    strategy = db.get_strategy(strategy_id)
    print("\nStrategy details:")
    print(f"  ID: {strategy['id']}")
    print(f"  Name: {strategy['name']}")
    print(f"  Description: {strategy['description']}")
    print(f"  Category: {strategy['category']}")
    print(f"  Status: {strategy['status']}")
    print(f"  Active Version: {strategy['active_version']}")
    print(f"  Active File: {strategy['active_file_path']}")


def example_get_user_strategies():
    """
    Example: Get all strategies for a user

    Can filter by:
    - Status (active/inactive/testing)
    - Category
    - Include shared strategies
    """
    db = SQLiteDatabase(db_path="test_user_strategies.db")
    db.initialize_database()

    # Create user and strategies
    user_id = db.create_user(
        email="trader@example.com",
        username="trader",
        password="pass"
    )

    strategies_data = [
        ("MA Crossover", "Trend Following", "active"),
        ("RSI Strategy", "Mean Reversion", "active"),
        ("Breakout Strategy", "Breakout", "inactive"),
        ("Scalping Bot", "Scalping", "testing"),
    ]

    for name, category, status in strategies_data:
        db.create_strategy(
            user_id=user_id,
            name=name,
            category=category,
            status=status
        )

    # Get all strategies
    all_strategies = db.get_user_strategies(user_id)
    print(f"Total strategies: {len(all_strategies)}")

    # Filter by status
    active_strategies = db.get_user_strategies(user_id, status="active")
    print(f"Active strategies: {len(active_strategies)}")
    for s in active_strategies:
        print(f"  - {s['name']} ({s['category']})")

    # Filter by category
    trend_strategies = db.get_user_strategies(user_id, category="Trend Following")
    print(f"\nTrend Following strategies: {len(trend_strategies)}")
    for s in trend_strategies:
        print(f"  - {s['name']}")


def example_strategy_versions():
    """
    Example: Managing multiple strategy versions

    Shows how to:
    - Create multiple versions
    - Retrieve version history
    - Get specific version details
    """
    db = SQLiteDatabase(db_path="test_version_mgmt.db")
    db.initialize_database()

    # Setup
    user_id = db.create_user(
        email="dev@example.com",
        username="dev",
        password="pass"
    )
    strategy_id = db.create_strategy(
        user_id=user_id,
        name="Evolving Strategy"
    )

    # Create version history
    versions = [
        ("0.1.0", "Alpha release", {"param": 5}),
        ("0.2.0", "Beta release", {"param": 7}),
        ("1.0.0", "First stable", {"param": 10}),
        ("1.0.1", "Bug fix", {"param": 10}),
        ("1.1.0", "Feature update", {"param": 12}),
    ]

    for version, changelog, params in versions:
        db.create_strategy_version(
            strategy_id=strategy_id,
            version=version,
            file_path=f"strategies/evolving_{version}.py",
            parameters=params,
            changelog=changelog,
            created_by=user_id
        )

    # Get all versions
    all_versions = db.get_strategy_versions(strategy_id)
    print(f"Total versions: {len(all_versions)}")
    print("\nVersion history:")
    for v in all_versions:
        print(f"  {v['version']}: {v['changelog']}")
        print(f"    Parameters: {v['parameters']}")


def example_update_strategy():
    """
    Example: Updating strategy details

    Can update:
    - Name, description, category
    - Status (active/inactive/testing)
    - Public visibility
    - Active version
    """
    db = SQLiteDatabase(db_path="test_update.db")
    db.initialize_database()

    # Setup
    user_id = db.create_user(
        email="user@example.com",
        username="user",
        password="pass"
    )
    strategy_id = db.create_strategy(
        user_id=user_id,
        name="Old Name",
        description="Old description",
        status="inactive"
    )

    print("Original strategy:")
    strategy = db.get_strategy(strategy_id)
    print(f"  Name: {strategy['name']}")
    print(f"  Description: {strategy['description']}")
    print(f"  Status: {strategy['status']}")

    # Update strategy
    db.update_strategy(
        strategy_id=strategy_id,
        name="New Name",
        description="Updated description with more details",
        status="active",
        is_public=True
    )

    print("\nUpdated strategy:")
    strategy = db.get_strategy(strategy_id)
    print(f"  Name: {strategy['name']}")
    print(f"  Description: {strategy['description']}")
    print(f"  Status: {strategy['status']}")
    print(f"  Public: {strategy['is_public']}")


def example_share_strategy():
    """
    Example: Sharing strategies between users

    Strategies can be shared with different permission levels:
    - view: Can view strategy details
    - clone: Can create a copy
    - edit: Can modify the strategy
    """
    db = SQLiteDatabase(db_path="test_share.db")
    db.initialize_database()

    # Create two users
    owner_id = db.create_user(
        email="owner@example.com",
        username="owner",
        password="pass"
    )
    collaborator_id = db.create_user(
        email="collab@example.com",
        username="collaborator",
        password="pass"
    )

    # Create a strategy
    strategy_id = db.create_strategy(
        user_id=owner_id,
        name="Shared Strategy",
        description="A strategy to share"
    )

    # Share with view permission
    share_id = db.share_strategy(
        strategy_id=strategy_id,
        shared_with_user_id=collaborator_id,
        permission="view"
    )
    print(f"Strategy shared with view permission: Share ID {share_id}")

    # Get collaborator's strategies (including shared)
    collab_strategies = db.get_user_strategies(
        user_id=collaborator_id,
        include_shared=True
    )
    print(f"\nCollaborator can access {len(collab_strategies)} strategies")
    for s in collab_strategies:
        print(f"  - {s['name']} (Permission: {s.get('permission', 'owner')})")

    # Unshare strategy
    db.unshare_strategy(strategy_id, collaborator_id)
    print("\nStrategy unshared")


def example_delete_operations():
    """
    Example: Deleting strategies and versions

    Cascade behavior:
    - Deleting a strategy deletes all versions
    - Deleting a strategy deletes all shares
    - Deleting a strategy cascades to related backtests
    """
    db = SQLiteDatabase(db_path="test_delete.db")
    db.initialize_database()

    # Setup
    user_id = db.create_user(
        email="user@example.com",
        username="user",
        password="pass"
    )
    strategy_id = db.create_strategy(
        user_id=user_id,
        name="Temporary Strategy"
    )

    # Create versions
    for i in range(3):
        db.create_strategy_version(
            strategy_id=strategy_id,
            version=f"1.{i}.0",
            file_path=f"strategies/temp_v{i}.py"
        )

    # Verify versions exist
    versions = db.get_strategy_versions(strategy_id)
    print(f"Created {len(versions)} versions")

    # Delete one version
    version_id = versions[0]['id']
    db.delete_strategy_version(version_id)
    print(f"Deleted version {versions[0]['version']}")

    # Verify deletion
    versions = db.get_strategy_versions(strategy_id)
    print(f"Remaining versions: {len(versions)}")

    # Delete entire strategy (cascades to all versions)
    db.delete_strategy(strategy_id)
    print("\nStrategy deleted (all versions removed)")


def example_complete_strategy_workflow():
    """
    Example: Complete strategy lifecycle

    1. Create strategy
    2. Create multiple versions
    3. Activate strategy
    4. Share with team
    5. Update over time
    6. Retire strategy
    """
    db = SQLiteDatabase(db_path="test_workflow.db")
    db.initialize_database()

    # Create team
    owner_id = db.create_user(
        email="owner@example.com",
        username="owner",
        password="pass"
    )
    team_member_id = db.create_user(
        email="team@example.com",
        username="team_member",
        password="pass"
    )

    print("Step 1: Create strategy")
    strategy_id = db.create_strategy(
        user_id=owner_id,
        name="Production Strategy",
        description="Main trading strategy",
        category="Trend Following",
        status="inactive"
    )
    print(f"  Strategy ID: {strategy_id}")

    print("\nStep 2: Develop versions")
    db.create_strategy_version(
        strategy_id=strategy_id,
        version="1.0.0",
        file_path="strategies/prod_v1.py",
        parameters={"period": 20},
        changelog="Initial version"
    )
    db.create_strategy_version(
        strategy_id=strategy_id,
        version="1.1.0",
        file_path="strategies/prod_v11.py",
        parameters={"period": 20, "use_filter": True},
        changelog="Added trend filter"
    )
    print("  Created versions 1.0.0 and 1.1.0")

    print("\nStep 3: Activate strategy")
    db.update_strategy(strategy_id=strategy_id, status="active")
    print("  Status: active")

    print("\nStep 4: Share with team")
    db.share_strategy(strategy_id, team_member_id, permission="view")
    print("  Shared with team member")

    print("\nStep 5: Continue development")
    db.create_strategy_version(
        strategy_id=strategy_id,
        version="2.0.0",
        file_path="strategies/prod_v2.py",
        parameters={"period": 25, "use_filter": True, "risk_mgmt": True},
        changelog="Major update with risk management"
    )
    print("  Released version 2.0.0")

    print("\nStep 6: Strategy summary")
    strategy = db.get_strategy(strategy_id)
    versions = db.get_strategy_versions(strategy_id)
    print(f"  Name: {strategy['name']}")
    print(f"  Status: {strategy['status']}")
    print(f"  Total versions: {len(versions)}")
    print(f"  Active version: {strategy['active_version']}")


if __name__ == "__main__":
    print("=" * 80)
    print("StrategyManager Usage Examples")
    print("=" * 80)

    print("\n1. Create Strategy")
    print("-" * 80)
    example_create_strategy()

    print("\n2. Create Strategy Version")
    print("-" * 80)
    example_create_strategy_version()

    print("\n3. Get Strategy")
    print("-" * 80)
    example_get_strategy()

    print("\n4. Get User Strategies")
    print("-" * 80)
    example_get_user_strategies()

    print("\n5. Strategy Versions")
    print("-" * 80)
    example_strategy_versions()

    print("\n6. Update Strategy")
    print("-" * 80)
    example_update_strategy()

    print("\n7. Share Strategy")
    print("-" * 80)
    example_share_strategy()

    print("\n8. Delete Operations")
    print("-" * 80)
    example_delete_operations()

    print("\n9. Complete Strategy Workflow")
    print("-" * 80)
    example_complete_strategy_workflow()
