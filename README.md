***Folder Structure***

**Project Root Directory: `HaruQuant/`**

- **`README.md`**: Provides an overview of the project, setup instructions, and usage guidelines.

- **`requirements.txt`**: Lists all the Python dependencies required for the project.

- **`config/`**: Contains configuration files.

  - **`config.yaml`**: Holds configuration settings such as API keys, database connections, and other environment-specific variables.

- **`data/`**: Directory designated for data storage.

  - **`raw/`**: Stores raw data fetched from external sources.

  - **`processed/`**: Contains data that has been cleaned and processed for analysis.

- **`logs/`**: Houses log files generated during the bot's operation.

- **`notebooks/`**: Jupyter notebooks for exploratory data analysis, strategy development, and prototyping.

- **`scripts/`**: Utility scripts for tasks like data downloading, backtesting, and deployment.

- **`src/`**: Main source code directory containing the core modules of the bot.

  - **`__init__.py`**: Initializes the package.

  - **`data_acquisition.py`**: Module responsible for fetching and handling market data.

  - **`strategy.py`**: Contains the logic for various trading strategies.

  - **`risk_management.py`**: Implements risk and position management rules.

  - **`order_execution.py`**: Manages order placement and execution through the MT5 API.

  - **`portfolio.py`**: Handles portfolio tracking and performance evaluation.

  - **`logger.py`**: Sets up logging configurations to monitor the bot's activities.

  - **`alerts.py`**: Manages alerts and notifications, such as integrating with Telegram for real-time updates.

  - **`backtester.py`**: Module dedicated to backtesting trading strategies on historical data.

  - **`visualization.py`**: Generates visual representations of data and performance metrics.

- **`tests/`**: Contains unit and integration tests to ensure code reliability.

  - **`__init__.py`**: Initializes the test package.

  - **`test_data_acquisition.py`**: Tests for the data acquisition module.

  - **`test_strategy.py`**: Tests for the strategy module.

  - **`test_risk_management.py`**: Tests for the risk management module.

  - **`test_order_execution.py`**: Tests for the order execution module.

  - **`test_portfolio.py`**: Tests for the portfolio module.

  - **`test_logger.py`**: Tests for the logger module.

  - **`test_alerts.py`**: Tests for the alerts module.

  - **`test_backtester.py`**: Tests for the backtester module.

  - **`test_visualization.py`**: Tests for the visualization module.

